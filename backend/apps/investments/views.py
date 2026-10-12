from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import (
    HasAnyRole,
    IsFinanceChecker,
    IsFinanceMaker,
    IsRiskCompliance,
    IsShariahBoard,
)
from apps.accounts.workflow import validate_maker_checker
from apps.accounting.services import post_capital_movement_journal
from apps.core.audit import log_action
from apps.pools.period_lock import assert_period_open

from .models import (
    CapitalAccount,
    CapitalAccountStatus,
    ImpairmentEvent,
    ImpairmentEventStatus,
    InvestorProfile,
    KYCStatus,
    NAVSnapshot,
    NAVSnapshotStatus,
    Redemption,
    Subscription,
    UnitMovement,
    UnitMovementType,
)
from .nav_engine import calculate_nav
from .serializers import (
    CapitalAccountSerializer,
    ImpairmentEventSerializer,
    InvestorProfileSerializer,
    NAVSnapshotSerializer,
    RedemptionSerializer,
    SubscriptionSerializer,
)


STAFF_ROLES = ["pool_manager", "finance_maker", "finance_checker", "risk_compliance", "auditor", "shariah_board"]


def _scope_to_owner(queryset, user, owner_path):
    """Investors/members only ever see records that belong to their own participant record."""

    if user.role == "investor_member":
        return queryset.filter(**{owner_path: user})
    return queryset


def _parse_date(value, field="transaction_date"):
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValidationError({field: ["Enter a valid date (YYYY-MM-DD)."]})


def _latest_published_nav(pool):
    """
    Returns the most recent published NAVSnapshot for `pool` (by
    valuation_date), or None if there isn't one.
    """

    return (
        NAVSnapshot.objects.filter(pool=pool, status=NAVSnapshotStatus.PUBLISHED)
        .order_by("-valuation_date")
        .first()
    )


class CapitalAccountViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CapitalAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # See apps/products/views.py etc. for why this must be a method
        # rather than a class-level `queryset = Model.objects.all()`
        # attribute (TenantScopedManager + import-time evaluation bug).
        queryset = _scope_to_owner(CapitalAccount.objects.all(), self.request.user, "participant__user")
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker"])()]
        if self.action == "subscribe":
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action == "redeem":
            return [IsAuthenticated(), HasAnyRole(["finance_maker", "pool_manager", "investor_member"])()]
        if self.action in ("update", "partial_update"):
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker"])()]
        return [IsAuthenticated()]  # list/retrieve/statement: investors are limited to their own accounts

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="CapitalAccount",
            object_id=str(instance.id),
            changes={"investor_reference": instance.investor_reference, "investor_name": instance.investor_name},
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def subscribe(self, request, pk=None):
        account = self.get_object()

        if not hasattr(account, "investor_profile") or account.investor_profile.kyc_status != KYCStatus.VERIFIED:
            raise ValidationError("KYC verification required before subscription")
        from .disclosures import assert_subscription_allowed

        assert_subscription_allowed(account)
        from apps.pools.lifecycle import assert_not_frozen

        assert_not_frozen(account.pool, "subscriptions")

        amount = request.data.get("amount")
        transaction_date = request.data.get("transaction_date")

        errors = {}
        if not amount:
            errors["amount"] = ["This field is required."]
        if not transaction_date:
            errors["transaction_date"] = ["This field is required."]
        if errors:
            raise ValidationError(errors)

        nav_snapshot = _latest_published_nav(account.pool)
        if nav_snapshot is None:
            raise ValidationError(
                "No published NAV available for this pool. Cannot process subscription/redemption."
            )
        nav_per_unit = nav_snapshot.nav_per_unit

        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValidationError({"amount": ["Amount must be positive."]})
        units_allotted = amount / nav_per_unit
        effective_date = _parse_date(transaction_date)
        assert_period_open(account.pool, effective_date, what="a subscription")

        with transaction.atomic():
            subscription = Subscription.objects.create(
                tenant=account.tenant,
                capital_account=account,
                amount=amount,
                nav_per_unit=nav_per_unit,
                units_allotted=units_allotted,
                transaction_date=effective_date,
                status="processed",
            )

            account.units_held += units_allotted
            account.save(update_fields=["units_held", "updated_at"])
            UnitMovement.objects.create(
                tenant=account.tenant, capital_account=account, effective_date=effective_date,
                units_delta=units_allotted, movement_type=UnitMovementType.SUBSCRIPTION,
                reference_id=str(subscription.id),
            )
            post_capital_movement_journal(
                kind="subscription", tenant=account.tenant, pool=account.pool, amount=amount,
                on_date=effective_date, posted_by=request.user,
            )

        log_action(
            tenant=account.tenant,
            actor=request.user,
            action="subscribe",
            model_name="CapitalAccount",
            object_id=str(account.id),
            changes={
                "subscription_id": str(subscription.id),
                "amount": str(amount),
                "nav_per_unit": str(nav_per_unit),
                "nav_snapshot_id": str(nav_snapshot.id),
                "units_allotted": str(units_allotted),
                "units_held_after": str(account.units_held),
            },
            request=request,
        )

        return Response(SubscriptionSerializer(subscription).data, status=201)

    @action(detail=True, methods=["post"])
    def redeem(self, request, pk=None):
        """Request a redemption; an independent finance checker approves it (see redemptions.py)."""
        from .redemptions import request_redemption

        account = self.get_object()
        from apps.pools.lifecycle import assert_not_frozen

        assert_not_frozen(account.pool, "redemptions")
        errors = {}
        for field in ("units_redeemed", "transaction_date"):
            if not request.data.get(field):
                errors[field] = ["This field is required."]
        if errors:
            raise ValidationError(errors)
        try:
            units = Decimal(str(request.data["units_redeemed"]))
        except ArithmeticError:
            raise ValidationError({"units_redeemed": ["Enter a valid number of units."]})
        redemption = request_redemption(
            account=account, units=units, dealing_date=_parse_date(request.data["transaction_date"]),
            user=request.user,
        )
        log_action(
            tenant=account.tenant, actor=request.user, action="redemption_requested", model_name="CapitalAccount",
            object_id=str(account.id),
            changes={"redemption_id": str(redemption.id), "units_redeemed": str(units),
                     "dealing_date": str(redemption.transaction_date)},
            request=request,
        )
        return Response(RedemptionSerializer(redemption).data, status=201)

    @action(detail=True, methods=["get"])
    def statement(self, request, pk=None):
        """Capital account statement; an investor can only open their own (queryset-scoped)."""
        account = self.get_object()
        period_end = _parse_date(request.query_params.get("to") or timezone.localdate().isoformat(), "to")
        period_start = _parse_date(request.query_params.get("from") or period_end.replace(day=1).isoformat(), "from")
        if period_start > period_end:
            raise ValidationError("'from' cannot be after 'to'.")
        return Response(_capital_statement(account, period_start, period_end))


def _capital_statement(account, period_start, period_end):
    """Units, movements, NAV value and distributions of one capital account for a period."""

    from .distribution import average_units
    from .models import DistributionRunStatus, InvestmentDistributionLine

    movements = list(UnitMovement.objects.filter(capital_account=account).order_by("effective_date", "created_at"))
    base = Decimal(account.units_held) - sum((m.units_delta for m in movements), Decimal("0"))

    def units_on(day):
        return max(base + sum((m.units_delta for m in movements if m.effective_date <= day), Decimal("0")), Decimal("0"))

    from datetime import timedelta

    in_period = [m for m in movements if period_start <= m.effective_date <= period_end]
    days = [period_start + timedelta(days=i) for i in range((period_end - period_start).days + 1)]
    nav = (
        NAVSnapshot.objects.filter(
            pool=account.pool, status=NAVSnapshotStatus.PUBLISHED, valuation_date__lte=period_end
        )
        .order_by("-valuation_date")
        .first()
    )
    distributions = InvestmentDistributionLine.objects.filter(
        capital_account=account,
        run__status=DistributionRunStatus.SIGNED,
        run__period_end__gte=period_start,
        run__period_end__lte=period_end,
    ).select_related("run")
    closing_units = units_on(period_end)
    return {
        "capital_account": str(account.id),
        "investor_reference": account.investor_reference,
        "investor_name": account.investor_name,
        "pool": account.pool.name,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "opening_units": str(units_on(period_start - timedelta(days=1))),
        "subscribed_units": str(sum((m.units_delta for m in in_period if m.units_delta > 0), Decimal("0"))),
        "redeemed_units": str(-sum((m.units_delta for m in in_period if m.units_delta < 0), Decimal("0"))),
        "closing_units": str(closing_units),
        "average_units": str(average_units(account, movements, days).quantize(Decimal("0.000001"))),
        "nav_per_unit": str(nav.nav_per_unit) if nav else None,
        "nav_date": nav.valuation_date.isoformat() if nav else None,
        "market_value": str((closing_units * nav.nav_per_unit).quantize(Decimal("0.01"))) if nav else None,
        "profit_distributions": [
            {
                "run_id": str(line.run_id),
                "period_start": line.run.period_start.isoformat(),
                "period_end": line.run.period_end.isoformat(),
                "average_units": str(line.average_units),
                "amount": str(line.allocated_amount),
            }
            for line in distributions
        ],
        "total_profit_distributed": str(sum((l.allocated_amount for l in distributions), Decimal("0.00"))),
        "movements": [
            {
                "date": m.effective_date.isoformat(),
                "type": m.movement_type,
                "units": str(m.units_delta),
            }
            for m in in_period
        ],
    }


class SubscriptionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = _scope_to_owner(
            Subscription.objects.all().order_by("-transaction_date"), self.request.user,
            "capital_account__participant__user",
        )
        capital_account_id = self.request.query_params.get("capital_account")
        if capital_account_id:
            queryset = queryset.filter(capital_account_id=capital_account_id)
        return queryset


class RedemptionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = RedemptionSerializer

    def get_permissions(self):
        if self.action in ("approve", "reject"):
            return [IsAuthenticated(), IsFinanceChecker()]
        return [IsAuthenticated()]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from .redemptions import approve_redemption

        redemption = approve_redemption(self.get_object(), request.user)
        log_action(
            tenant=redemption.tenant, actor=request.user, action="redemption_approved", model_name="Redemption",
            object_id=str(redemption.id),
            changes={"amount": str(redemption.amount), "nav_per_unit": str(redemption.nav_per_unit)},
            request=request,
        )
        return Response(self.get_serializer(redemption).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        from .redemptions import reject_redemption

        redemption = reject_redemption(self.get_object(), request.user, str(request.data.get("reason") or ""))
        log_action(
            tenant=redemption.tenant, actor=request.user, action="redemption_rejected", model_name="Redemption",
            object_id=str(redemption.id), reason=redemption.rejection_reason, request=request,
        )
        return Response(self.get_serializer(redemption).data)

    def get_queryset(self):
        queryset = _scope_to_owner(
            Redemption.objects.all().order_by("-transaction_date"), self.request.user,
            "capital_account__participant__user",
        )
        capital_account_id = self.request.query_params.get("capital_account")
        if capital_account_id:
            queryset = queryset.filter(capital_account_id=capital_account_id)
        return queryset


class InvestorProfileViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = InvestorProfileSerializer

    def get_queryset(self):
        queryset = _scope_to_owner(
            InvestorProfile.objects.all(), self.request.user, "capital_account__participant__user"
        )
        capital_account_id = self.request.query_params.get("capital_account")
        if capital_account_id:
            queryset = queryset.filter(capital_account_id=capital_account_id)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action == "verify_kyc":
            return [IsAuthenticated(), IsRiskCompliance()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="InvestorProfile",
            object_id=str(instance.id),
            changes={"capital_account": str(instance.capital_account_id), "kyc_status": instance.kyc_status},
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = serializer.save(
            kyc_status=KYCStatus.PENDING,
            verified_by=None,
            verified_at=None,
        )
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="update",
            model_name="InvestorProfile",
            object_id=str(instance.id),
            changes={"capital_account": str(instance.capital_account_id)},
            request=self.request,
        )

    @action(detail=True, methods=["post"], url_path="verify-kyc")
    def verify_kyc(self, request, pk=None):
        profile = self.get_object()
        kyc_status = request.data.get("kyc_status")
        if kyc_status not in {KYCStatus.VERIFIED, KYCStatus.REJECTED}:
            raise ValidationError({"kyc_status": ["Must be 'verified' or 'rejected'."]})

        previous_status = profile.kyc_status
        profile.kyc_status = kyc_status
        profile.suitability_assessment_notes = request.data.get("notes")
        profile.verified_by = request.user
        profile.verified_at = timezone.now()
        profile.save(
            update_fields=[
                "kyc_status",
                "suitability_assessment_notes",
                "verified_by",
                "verified_at",
                "updated_at",
            ]
        )
        log_action(
            tenant=profile.tenant,
            actor=request.user,
            action="verify_kyc",
            model_name="InvestorProfile",
            object_id=str(profile.id),
            changes={"kyc_status": {"before": previous_status, "after": kyc_status}},
            reason=profile.suitability_assessment_notes,
            request=request,
        )
        return Response(self.get_serializer(profile).data)


class ImpairmentEventViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ImpairmentEventSerializer

    def get_queryset(self):
        queryset = ImpairmentEvent.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        pool = serializer.validated_data["pool"]
        valuation_date = serializer.validated_data["valuation_date"]
        loss_amount = serializer.validated_data["loss_amount"]
        nav_snapshot = (
            NAVSnapshot.objects.filter(
                pool=pool,
                valuation_date__lte=valuation_date,
                status=NAVSnapshotStatus.PUBLISHED,
            )
            .order_by("-valuation_date")
            .first()
        )
        if nav_snapshot is None or nav_snapshot.total_pool_value <= 0:
            raise ValidationError(
                "A published NAV with a positive total pool value is required for impairment."
            )

        loss_percentage = loss_amount / nav_snapshot.total_pool_value * Decimal("100")
        if loss_percentage > Decimal("100"):
            raise ValidationError("Loss amount cannot exceed the total pool value.")

        instance = serializer.save(
            tenant=self.request.user.tenant,
            loss_percentage=loss_percentage,
            status=ImpairmentEventStatus.DRAFT,
        )
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="ImpairmentEvent",
            object_id=str(instance.id),
            changes={
                "pool": str(instance.pool_id),
                "loss_amount": str(instance.loss_amount),
                "loss_percentage": str(instance.loss_percentage),
            },
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        event = self.get_object()
        unit_quantum = Decimal("0.000001")

        with transaction.atomic():
            event = (
                self.get_queryset()
                .select_for_update()
                .get(pk=event.pk)
            )
            if event.status != ImpairmentEventStatus.DRAFT:
                raise ValidationError(
                    f"ImpairmentEvent must be in '{ImpairmentEventStatus.DRAFT}' status to approve."
                )

            accounts = list(
                CapitalAccount.objects.select_for_update()
                .filter(pool=event.pool, status=CapitalAccountStatus.ACTIVE)
                .order_by("id")
            )
            if not accounts:
                raise ValidationError("No active capital accounts found for this pool.")

            loss_ratio = event.loss_percentage / Decimal("100")
            total_units_before = sum((account.units_held for account in accounts), Decimal("0"))
            total_units_after = (total_units_before * (Decimal("1") - loss_ratio)).quantize(
                unit_quantum, rounding=ROUND_HALF_UP
            )
            remaining_units = total_units_after

            for index, account in enumerate(accounts):
                units_before = account.units_held
                if index == len(accounts) - 1:
                    units_after = remaining_units
                else:
                    units_after = (units_before * (Decimal("1") - loss_ratio)).quantize(
                        unit_quantum, rounding=ROUND_HALF_UP
                    )
                    remaining_units -= units_after

                units_reduced = units_before - units_after
                account.units_held = units_after
                account.save(update_fields=["units_held", "updated_at"])
                if units_reduced != 0:
                    UnitMovement.objects.create(
                        tenant=account.tenant, capital_account=account, effective_date=event.valuation_date,
                        units_delta=-units_reduced, movement_type=UnitMovementType.IMPAIRMENT,
                        reference_id=str(event.id),
                    )
                log_action(
                    tenant=account.tenant,
                    actor=request.user,
                    action="impairment_reduce_units",
                    model_name="CapitalAccount",
                    object_id=str(account.id),
                    changes={
                        "impairment_event_id": str(event.id),
                        "units_before": str(units_before),
                        "units_reduced": str(units_reduced),
                        "units_after": str(units_after),
                    },
                    request=request,
                )

            event.status = ImpairmentEventStatus.APPROVED
            event.approved_by = request.user
            event.save(update_fields=["status", "approved_by", "updated_at"])
            log_action(
                tenant=event.tenant,
                actor=request.user,
                action="approve",
                model_name="ImpairmentEvent",
                object_id=str(event.id),
                changes={"status": {"before": ImpairmentEventStatus.DRAFT, "after": event.status}},
                request=request,
            )

        return Response(self.get_serializer(event).data)


class NAVSnapshotViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NAVSnapshotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # See apps/products/views.py etc. for why this must be a method
        # rather than a class-level `queryset = Model.objects.all()`
        # attribute (TenantScopedManager + import-time evaluation bug).
        queryset = NAVSnapshot.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action == "publish":
            return [IsAuthenticated(), IsFinanceChecker()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        pool = serializer.validated_data["pool"]
        total_pool_value = serializer.validated_data["total_pool_value"]

        try:
            result = calculate_nav(pool, total_pool_value)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        instance = serializer.save(
            tenant=self.request.user.tenant,
            total_units_outstanding=result["total_units_outstanding"],
            nav_per_unit=result["nav_per_unit"],
            status=NAVSnapshotStatus.DRAFT,
            created_by=self.request.user,
        )

        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="NAVSnapshot",
            object_id=str(instance.id),
            changes={
                "pool": str(instance.pool_id),
                "valuation_date": str(instance.valuation_date),
                "total_pool_value": str(instance.total_pool_value),
                "total_units_outstanding": str(instance.total_units_outstanding),
                "nav_per_unit": str(instance.nav_per_unit),
            },
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        snapshot = self.get_object()

        if snapshot.status != NAVSnapshotStatus.DRAFT:
            raise ValidationError(
                f"NAVSnapshot must be in '{NAVSnapshotStatus.DRAFT}' status to publish "
                f"(current status: '{snapshot.status}')."
            )

        try:
            validate_maker_checker(maker_user=snapshot.created_by, checker_user=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message) from exc

        already_published = (
            NAVSnapshot.objects.filter(
                pool=snapshot.pool,
                valuation_date=snapshot.valuation_date,
                status=NAVSnapshotStatus.PUBLISHED,
            )
            .exclude(id=snapshot.id)
            .exists()
        )
        if already_published:
            raise ValidationError(
                f"A NAVSnapshot for {snapshot.pool.code} on {snapshot.valuation_date} has "
                "already been published."
            )

        previous_status = snapshot.status
        snapshot.status = NAVSnapshotStatus.PUBLISHED
        snapshot.published_by = request.user
        snapshot.published_at = timezone.now()
        snapshot.save(update_fields=["status", "published_by", "published_at", "updated_at"])

        log_action(
            tenant=snapshot.tenant,
            actor=request.user,
            action="publish",
            model_name="NAVSnapshot",
            object_id=str(snapshot.id),
            changes={
                "status": {"before": previous_status, "after": snapshot.status},
                "nav_per_unit": str(snapshot.nav_per_unit),
            },
            request=request,
        )

        return Response(self.get_serializer(snapshot).data)

    @action(detail=False, methods=["get"], url_path="latest")
    def latest(self, request):
        pool_id = request.query_params.get("pool")
        if not pool_id:
            raise ValidationError({"pool": ["This query parameter is required."]})

        snapshot = (
            NAVSnapshot.objects.filter(pool_id=pool_id, status=NAVSnapshotStatus.PUBLISHED)
            .order_by("-valuation_date")
            .first()
        )
        if snapshot is None:
            raise ValidationError("No published NAV available for this pool.")

        return Response(self.get_serializer(snapshot).data)
