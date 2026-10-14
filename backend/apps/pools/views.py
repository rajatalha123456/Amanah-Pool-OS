from django.core.exceptions import ValidationError as DjangoValidationError
from datetime import date
from decimal import Decimal
import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.pagination import StandardPagination
from apps.accounts.permissions import (
    HasAnyRole,
    IsFinanceChecker,
    IsPoolManager,
    IsShariahBoard,
)
from apps.core.audit import log_action
from apps.core.viewset_guards import NO_DELETE, READ_AND_POST, STAFF_ROLES, EditableWhileDraftMixin
from apps.notifications import events
from apps.core.exceptions_helper import create_exception_case
from apps.participants.models import AccountStatus, KYCStatus, ParticipantAccount
from apps.products.models import ProductStatus

from .activation import activation_checks
from .config_snapshot import bound_rule_pack, build_pool_snapshot
from .liquidity import calculate_liquidity_forecast
from .daily_close import assert_day_open
from .period_lock import assert_period_open
from .version_diff import generate_version_diff

from .models import (
    Asset,
    AssetAssignment,
    AssetProvisionEntry,
    AssetStatus,
    BalanceImportBatch,
    BalanceImportBatchStatus,
    DailyBalance,
    DailyBalanceStatus,
    DailyClose,
    PeriodCloseChecklist,
    Pool,
    PoolStatus,
    PoolVersion,
)
from .serializers import (
    DailyCloseSerializer,
    AssetAssignmentSerializer,
    AssetProvisionEntrySerializer,
    AssetSerializer,
    BalanceImportBatchSerializer,
    BulkBalanceImportSerializer,
    DailyBalanceSerializer,
    PeriodCloseChecklistSerializer,
    PoolSerializer,
    PoolVersionSerializer,
)

CONTROL_TOTAL_TOLERANCE = Decimal("0.01")


class PoolViewSet(EditableWhileDraftMixin, viewsets.ModelViewSet):
    serializer_class = PoolSerializer
    http_method_names = NO_DELETE

    def get_queryset(self):
        # See apps/products/views.py for why this must be a method rather
        # than a class-level `queryset = Model.objects.all()` attribute
        # (TenantScopedManager + import-time evaluation bug).
        return Pool.objects.all()

    def get_permissions(self):
        if self.action == "open":
            # BRD 6.1: the Pool Manager prepares, an independent checker activates.
            return [IsAuthenticated(), HasAnyRole(["finance_checker", "authorized_signatory"])()]
        if self.action in ("create", "update", "partial_update", "submit_for_approval", "create_version"):
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
        if self.action in ("close", "archive"):
            return [IsAuthenticated(), IsFinanceChecker()]
        if self.action == "freeze":
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "risk_compliance"])()]
        if self.action == "unfreeze":
            return [IsAuthenticated(), HasAnyRole(["authorized_signatory", "finance_checker"])()]
        return [IsAuthenticated(), HasAnyRole(STAFF_ROLES)()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="Pool",
            object_id=str(instance.id),
            request=self.request,
        )

    @action(detail=False, methods=["get"], url_path="portfolio-summary")
    def portfolio_summary(self, request):
        """Real funds / signed profit / yield per pool for the dashboards (no placeholder figures)."""
        from .portfolio import portfolio_summary

        pools = Pool.objects.select_related("product__contract_template").order_by("code")
        return Response(portfolio_summary(list(pools)))

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        pool = self.get_object()
        versions = pool.versions.all().order_by("-version_number")
        return Response(PoolVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=["get"], url_path="compare-versions")
    def compare_versions(self, request, pk=None):
        """
        BRD Product & Pool Screen 5:
        Pool Version Comparison & Governance Diff Matrix.
        """
        pool = self.get_object()
        v1_id = request.query_params.get("v1")
        v2_id = request.query_params.get("v2")

        versions = list(pool.versions.all().order_by("version_number"))
        if not versions:
            return Response({"error": "No pool versions exist for comparison."}, status=400)

        def _find_v(ident):
            if not ident:
                return None
            try:
                n = int(ident)
                m = pool.versions.filter(version_number=n).first()
                if m:
                    return m
            except (ValueError, TypeError):
                pass
            try:
                u = uuid.UUID(str(ident))
                return pool.versions.filter(id=u).first()
            except (ValueError, TypeError):
                pass
            return None

        v1 = _find_v(v1_id) or versions[0]
        v2 = _find_v(v2_id) or (versions[-1] if len(versions) > 1 else versions[0])

        diff_data = generate_version_diff(pool, v1, v2)
        return Response(diff_data)

    @action(detail=True, methods=["get"], url_path="activation-readiness")
    def activation_readiness(self, request, pk=None):
        """BR-001 checklist: what stands between this pool and activation."""
        pool = self.get_object()
        checks = activation_checks(pool)
        return Response({"pool": str(pool.id), "ready": all(c["passed"] for c in checks), "checks": checks})

    @action(detail=True, methods=["post"], url_path="create-version")
    def create_version(self, request, pk=None):
        """
        Seals the pool's *current* governing configuration as a new version. Economics are not typed
        here: change the approved PSR / weightage bands / reserves through their own approvals, then
        seal. A version identical to the latest one is refused.
        """
        pool = self.get_object()
        if pool.status not in (PoolStatus.OPEN, PoolStatus.ALLOCATION, PoolStatus.FROZEN):
            raise ValidationError("Versions can only be sealed for an open pool.")

        data = request.data or {}
        rationale = (data.get("change_rationale") or "").strip()
        if not rationale:
            raise ValidationError({"change_rationale": ["A change rationale is required."]})

        effective = data.get("effective_value_date")
        if effective:
            try:
                effective = date.fromisoformat(str(effective))
            except ValueError:
                raise ValidationError({"effective_value_date": ["Enter a valid date (YYYY-MM-DD)."]})

        latest_version = pool.versions.order_by("-version_number").first()
        snapshot = build_pool_snapshot(pool, change_rationale=rationale, effective_value_date=effective)
        if latest_version and (latest_version.snapshot or {}).get("config_hash") == snapshot["config_hash"]:
            raise ValidationError(
                "The pool's governing configuration has not changed since the latest version; nothing to seal."
            )
        new_version_num = (latest_version.version_number + 1) if latest_version else 1

        with transaction.atomic():
            pool.versions.all().update(is_current=False)
            new_version = PoolVersion.objects.create(
                tenant=pool.tenant,
                pool=pool,
                version_number=new_version_num,
                snapshot=snapshot,
                created_by=request.user,
                is_current=True,
            )

        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="create_pool_version",
            model_name="PoolVersion",
            object_id=str(new_version.id),
            reason=rationale,
            changes={"version_number": new_version_num, "config_hash": snapshot["config_hash"]},
            request=request,
        )

        return Response(PoolVersionSerializer(new_version).data, status=201)

    @action(detail=True, methods=["get"], url_path="liquidity-forecast")
    def liquidity_forecast(self, request, pk=None):
        pool = self.get_object()

        as_of_date_param = request.query_params.get("as_of_date")
        as_of_date = date.fromisoformat(as_of_date_param) if as_of_date_param else timezone.localdate()

        horizon_days_param = request.query_params.get("horizon_days")
        try:
            horizon_days = int(horizon_days_param) if horizon_days_param else 30
        except ValueError:
            raise ValidationError({"horizon_days": ["Must be an integer."]})

        result = calculate_liquidity_forecast(pool, as_of_date, horizon_days=horizon_days)
        return Response(result)

    @action(detail=True, methods=["post"], url_path="submit-for-approval")
    def submit_for_approval(self, request, pk=None):
        pool = self.get_object()

        if pool.status != PoolStatus.DRAFT:
            raise ValidationError(
                f"Pool must be in '{PoolStatus.DRAFT}' status to submit for approval "
                f"(current status: '{pool.status}')."
            )

        if pool.product.status != ProductStatus.APPROVED:
            raise ValidationError("Product must be approved first.")

        pool.status = PoolStatus.PENDING_APPROVAL
        pool.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="submit_for_approval",
            model_name="Pool",
            object_id=str(pool.id),
            changes={"status": {"before": PoolStatus.DRAFT, "after": PoolStatus.PENDING_APPROVAL}},
            request=request,
        )
        events.pool_submitted(pool, request.user)
        return Response(self.get_serializer(pool).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        pool = self.get_object()

        if pool.status != PoolStatus.PENDING_APPROVAL:
            raise ValidationError(
                f"Pool must be in '{PoolStatus.PENDING_APPROVAL}' status to approve "
                f"(current status: '{pool.status}')."
            )

        pool.status = PoolStatus.APPROVED
        pool.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="approve",
            model_name="Pool",
            object_id=str(pool.id),
            reason="Shariah Board sign-off on pool",
            changes={"status": {"before": PoolStatus.PENDING_APPROVAL, "after": PoolStatus.APPROVED}},
            request=request,
        )
        events.pool_approved(pool, request.user)
        return Response(self.get_serializer(pool).data)

    @action(detail=True, methods=["post"])
    def open(self, request, pk=None):
        pool = self.get_object()

        if pool.status != PoolStatus.APPROVED:
            raise ValidationError(
                f"Pool must be in '{PoolStatus.APPROVED}' status to open "
                f"(current status: '{pool.status}')."
            )

        # BR-001: contract, Shariah decision, rule pack, approved economics, accounting mapping and
        # approval matrix must all be in place before the pool goes live.
        failed = [
            f"{check['label']}: {check['detail']}".rstrip(": ")
            for check in activation_checks(pool)
            if not check["passed"]
        ]
        if failed:
            raise ValidationError({"activation": failed})

        if pool.rule_pack_id is None:
            pool.rule_pack = bound_rule_pack(pool)
        pool.status = PoolStatus.OPEN
        pool.save(update_fields=["status", "rule_pack", "updated_at"])

        version = PoolVersion.objects.create(
            tenant=pool.tenant,
            pool=pool,
            version_number=1,
            snapshot=build_pool_snapshot(pool, change_rationale="Initial version sealed on activation"),
            created_by=request.user,
            is_current=True,
        )

        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="open",
            model_name="Pool",
            object_id=str(pool.id),
            changes={"status": {"before": PoolStatus.APPROVED, "after": PoolStatus.OPEN}},
            request=request,
        )
        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="create",
            model_name="PoolVersion",
            object_id=str(version.id),
            reason="Initial version created on pool open",
            request=request,
        )
        return Response(self.get_serializer(pool).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        pool = self.get_object()

        if pool.status not in (PoolStatus.OPEN, PoolStatus.ALLOCATION, PoolStatus.FROZEN):
            raise ValidationError(
                f"Pool must be open, in allocation or frozen to close "
                f"(current status: '{pool.status}')."
            )

        previous_status = pool.status
        pool.status = PoolStatus.CLOSED
        pool.closed_date = timezone.localdate()
        pool.save(update_fields=["status", "closed_date", "updated_at"])
        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="close",
            model_name="Pool",
            object_id=str(pool.id),
            changes={"status": {"before": previous_status, "after": PoolStatus.CLOSED}},
            request=request,
        )
        return Response(self.get_serializer(pool).data)


    @action(detail=True, methods=["post"])
    def freeze(self, request, pk=None):
        from . import lifecycle

        pool = self.get_object()
        previous = lifecycle.freeze(pool, request.user, request.data.get("reason"))
        log_action(
            tenant=pool.tenant, actor=request.user, action="freeze", model_name="Pool", object_id=str(pool.id),
            changes={"status": {"before": previous, "after": PoolStatus.FROZEN}}, reason=pool.freeze_reason, request=request,
        )
        return Response(self.get_serializer(pool).data)

    @action(detail=True, methods=["post"])
    def unfreeze(self, request, pk=None):
        from . import lifecycle

        pool = self.get_object()
        reason = request.data.get("reason")
        restored = lifecycle.unfreeze(pool, request.user, reason)
        log_action(
            tenant=pool.tenant, actor=request.user, action="unfreeze", model_name="Pool", object_id=str(pool.id),
            changes={"status": {"before": PoolStatus.FROZEN, "after": restored}}, reason=reason, request=request,
        )
        return Response(self.get_serializer(pool).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        from . import lifecycle

        pool = self.get_object()
        lifecycle.archive(pool, request.user)
        log_action(
            tenant=pool.tenant, actor=request.user, action="archive", model_name="Pool", object_id=str(pool.id),
            changes={"status": {"before": PoolStatus.CLOSED, "after": PoolStatus.ARCHIVED}}, request=request,
        )
        return Response(self.get_serializer(pool).data)


class AssetViewSet(EditableWhileDraftMixin, viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    http_method_names = NO_DELETE
    # An asset held by a pool is changed only through provisions, write-offs or transfers.
    editable_statuses = ("available",)

    def get_queryset(self):
        return Asset.objects.all()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker"])()]
        if self.action in ("remediation_plan", "stress_test"):
            return [IsAuthenticated(), HasAnyRole(["risk_compliance"])()]
        return [IsAuthenticated(), HasAnyRole(STAFF_ROLES)()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="Asset",
            object_id=str(instance.id),
            request=self.request,
        )

    @action(detail=False, methods=["get"], url_path="concentration-risk")
    def concentration_risk(self, request):
        pool_id = request.query_params.get("pool_id")
        pool = None
        if pool_id:
            pool = Pool.objects.filter(id=pool_id).first()
        from .concentration_engine import run_concentration_risk_analysis
        data = run_concentration_risk_analysis(pool=pool)
        return Response(data)

    @action(detail=False, methods=["post"], url_path="remediation-plan")
    def remediation_plan(self, request):
        target_name = request.data.get("target_name")
        target_type = request.data.get("target_type", "obligor")
        current_exposure = Decimal(str(request.data.get("current_exposure", 0)))
        excess_amount = Decimal(str(request.data.get("excess_amount", 0)))
        action_note = request.data.get("action_note", "Mitigation covenant registered.")
        pool_id = request.data.get("pool_id")
        pool = Pool.objects.filter(id=pool_id).first() if pool_id else None

        if not target_name:
            raise ValidationError("target_name is required.")

        from .concentration_engine import commit_breach_remediation_case
        result = commit_breach_remediation_case(
            tenant=request.user.tenant,
            user=request.user,
            target_name=target_name,
            target_type=target_type,
            current_exposure=current_exposure,
            excess_amount=excess_amount,
            action_note=action_note,
            pool=pool,
        )
        return Response(result)

    @action(detail=False, methods=["post"], url_path="stress-test")
    def stress_test(self, request):
        pool_id = request.data.get("pool_id")
        deposit_runoff_pct = float(request.data.get("deposit_runoff_pct", 15.0))
        pool = Pool.objects.filter(id=pool_id).first() if pool_id else None

        from .concentration_engine import run_concentration_stress_test
        result = run_concentration_stress_test(pool=pool, deposit_runoff_pct=deposit_runoff_pct)
        return Response(result)


class AssetAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssetAssignmentSerializer
    # Assignments are history: created, ended (unassign) or moved (transfer) - never edited or deleted.
    http_method_names = READ_AND_POST

    def get_queryset(self):
        queryset = AssetAssignment.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "unassign", "transfer"):
            return [IsAuthenticated(), IsPoolManager()]
        return [IsAuthenticated(), HasAnyRole(STAFF_ROLES)()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant, assigned_by=self.request.user)

        instance.asset.status = AssetStatus.ASSIGNED
        instance.asset.save(update_fields=["status", "updated_at"])

        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="AssetAssignment",
            object_id=str(instance.id),
            changes={"asset_status": {"before": AssetStatus.AVAILABLE, "after": AssetStatus.ASSIGNED}},
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def unassign(self, request, pk=None):
        assignment = self.get_object()

        if assignment.unassigned_date is not None:
            raise ValidationError("This assignment has already been unassigned.")

        assignment.unassigned_date = timezone.localdate()
        assignment.save(update_fields=["unassigned_date", "updated_at"])

        assignment.asset.status = AssetStatus.AVAILABLE
        assignment.asset.save(update_fields=["status", "updated_at"])

        log_action(
            tenant=assignment.tenant,
            actor=request.user,
            action="unassign",
            model_name="AssetAssignment",
            object_id=str(assignment.id),
            changes={"asset_status": {"before": AssetStatus.ASSIGNED, "after": AssetStatus.AVAILABLE}},
            request=request,
        )
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        """Effective-dated move of the asset to another pool (old assignment ends the day before)."""
        from .asset_rules import transfer_asset

        assignment = self.get_object()
        to_pool = Pool.objects.filter(id=request.data.get("to_pool")).first()
        if to_pool is None:
            raise ValidationError({"to_pool": ["A valid destination pool is required."]})
        try:
            effective_date = date.fromisoformat(str(request.data.get("effective_date")))
        except ValueError:
            raise ValidationError({"effective_date": ["A valid date (YYYY-MM-DD) is required."]})

        with transaction.atomic():
            new_assignment = transfer_asset(
                assignment, to_pool, effective_date, str(request.data.get("reason") or ""), request.user
            )
            log_action(
                tenant=assignment.tenant,
                actor=request.user,
                action="transfer",
                model_name="AssetAssignment",
                object_id=str(assignment.id),
                changes={
                    "from_pool": str(assignment.pool_id),
                    "to_pool": str(to_pool.id),
                    "effective_date": str(effective_date),
                },
                reason=new_assignment.transfer_reason,
                request=request,
            )
        return Response(self.get_serializer(new_assignment).data)


class DailyBalanceViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = DailyBalanceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = DailyBalance.objects.all().order_by("-value_date", "participant_class", "account_id")
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        value_date = self.request.query_params.get("value_date")
        if value_date:
            queryset = queryset.filter(value_date=value_date)
        return queryset


class BalanceImportViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    POST creates a bulk balance import batch (BulkBalanceImportSerializer
    payload); GET lists BalanceImportBatch history, filterable by
    ?pool={pool_id}.
    """

    def get_queryset(self):
        queryset = BalanceImportBatch.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return BulkBalanceImportSerializer
        return BalanceImportBatchSerializer

    def get_permissions(self):
        if self.action in ("create", "cbs_sftp_daemon"):
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker"])()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = BulkBalanceImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        pool = data["pool"]
        value_date = data["value_date"]
        control_total_expected = data.get("control_total_expected")
        records = data["records"]

        assert_period_open(pool, value_date, what="a balance import")
        assert_day_open(pool, value_date, what="a balance import")

        errors = []
        created_balances = []
        control_total_actual = Decimal("0.00")

        accounts_by_number = {
            account.account_number: account
            for account in ParticipantAccount.objects.select_related("participant").filter(pool=pool)
        }

        with transaction.atomic():
            for record in records:
                balance_amount = record["balance_amount"]
                account_number = record.get("account_number")
                account = None

                if account_number:
                    account = accounts_by_number.get(account_number)
                    if account is None:
                        errors.append(f"Unknown account '{account_number}' for this pool: skipped.")
                        continue
                    if (
                        account.opened_date > value_date
                        or (account.closed_date and account.closed_date < value_date)
                        or (account.status == AccountStatus.CLOSED and not account.closed_date)
                    ):
                        errors.append(
                            f"Account '{account_number}' is not open on {value_date}: skipped."
                        )
                        continue
                    if account.participant.kyc_status != KYCStatus.VERIFIED:
                        errors.append(
                            f"Account '{account_number}': participant KYC is "
                            f"'{account.participant.kyc_status}', not verified: skipped."
                        )
                        continue
                    participant_class = account.participant.participant_class
                    duplicate = DailyBalance.objects.filter(
                        pool=pool, value_date=value_date, account=account
                    ).exists()
                    duplicate_label = f"account '{account_number}'"
                else:
                    if accounts_by_number:
                        errors.append(
                            "This pool has participant accounts; account_number is required "
                            "(class-level balances are not accepted): skipped."
                        )
                        continue
                    participant_class = record["participant_class"]
                    duplicate = DailyBalance.objects.filter(
                        pool=pool, value_date=value_date, participant_class=participant_class, account__isnull=True
                    ).exists()
                    duplicate_label = f"participant_class='{participant_class}'"

                if duplicate:
                    errors.append(f"Duplicate balance for {duplicate_label} on {value_date}: skipped.")
                    continue

                balance = DailyBalance.objects.create(
                    tenant=request.user.tenant,
                    pool=pool,
                    account=account,
                    participant_class=participant_class,
                    value_date=value_date,
                    balance_amount=balance_amount,
                    status=DailyBalanceStatus.VALIDATED,
                )
                created_balances.append(balance)
                control_total_actual += balance_amount

            matched_records = len(created_balances)
            exception_count = len(errors)

            # A batch is only "balanced" when nothing was skipped (no
            # duplicate exceptions) AND, if a control total was supplied,
            # it matches the actual sum within tolerance. Any exception
            # (duplicate skip or control-total mismatch) marks the whole
            # batch "exception", even if the other check would have passed.
            control_total_matches = (
                control_total_expected is None
                or abs(control_total_actual - control_total_expected) <= CONTROL_TOTAL_TOLERANCE
            )

            batch_status = (
                BalanceImportBatchStatus.BALANCED
                if exception_count == 0 and control_total_matches
                else BalanceImportBatchStatus.EXCEPTION
            )

            batch = BalanceImportBatch.objects.create(
                tenant=request.user.tenant,
                pool=pool,
                value_date=value_date,
                total_records=len(records),
                matched_records=matched_records,
                exception_count=exception_count,
                control_total_expected=control_total_expected,
                control_total_actual=control_total_actual,
                status=batch_status,
                imported_by=request.user,
            )

        log_action(
            tenant=batch.tenant,
            actor=request.user,
            action="import",
            model_name="BalanceImportBatch",
            object_id=str(batch.id),
            changes={
                "total_records": batch.total_records,
                "matched_records": batch.matched_records,
                "exception_count": batch.exception_count,
                "control_total_expected": str(control_total_expected) if control_total_expected is not None else None,
                "control_total_actual": str(control_total_actual),
                "status": batch.status,
            },
            request=request,
        )

        if batch.status == BalanceImportBatchStatus.EXCEPTION:
            create_exception_case(
                tenant=batch.tenant,
                source_module="balance_import",
                source_object_id=str(batch.id),
                pool=pool,
                severity="medium",
                title=f"Control total mismatch on {value_date} for pool {pool.code}",
                description=(
                    f"Balance import batch {batch.id} for pool {pool.code} on {value_date} "
                    f"flagged as exception: {exception_count} skipped/duplicate record(s), "
                    f"control total expected={control_total_expected}, actual={control_total_actual}."
                ),
            )

        return Response(
            {
                "id": str(batch.id),
                "total_records": batch.total_records,
                "matched_records": batch.matched_records,
                "exception_count": batch.exception_count,
                "control_total_expected": batch.control_total_expected,
                "control_total_actual": batch.control_total_actual,
                "status": batch.status,
                "errors": errors,
            },
            status=201,
        )

    @action(detail=False, methods=["post"], url_path="cbs-sftp-daemon")
    def cbs_sftp_daemon(self, request):
        """
        Screen 09 / Module 06: Automated Core Banking System SFTP EOD Batch Ingestion.
        """
        from datetime import datetime
        from apps.core.simulation import assert_simulation_allowed
        from .cbs_daemon import simulate_cbs_sftp_ingestion

        assert_simulation_allowed("The CBS SFTP feed")

        pool_id = request.data.get("pool_id")
        if not pool_id:
            raise ValidationError({"pool_id": ["This field is required."]})

        try:
            pool = Pool.objects.get(id=pool_id, tenant=request.user.tenant)
        except Pool.DoesNotExist:
            raise ValidationError({"pool_id": ["Pool not found."]})

        value_date_str = request.data.get("value_date")
        if value_date_str:
            value_date = datetime.strptime(value_date_str, "%Y-%m-%d").date()
        else:
            value_date = timezone.now().date()

        assert_period_open(pool, value_date, what="a balance import")
        assert_day_open(pool, value_date, what="a balance import")

        if ParticipantAccount.objects.filter(pool=pool).exists():
            raise ValidationError(
                "The CBS feed simulator only produces class-level balances and cannot be used "
                "for a pool with participant accounts; import account-level balances instead."
            )

        cbs_vendor = request.data.get("cbs_vendor", "Temenos T24")
        scenario = request.data.get("scenario", "clean")

        result = simulate_cbs_sftp_ingestion(
            tenant=request.user.tenant,
            pool=pool,
            value_date=value_date,
            cbs_vendor=cbs_vendor,
            scenario=scenario,
            user=request.user,
        )

        status_code = 200 if result.get("success") else 422
        return Response(result, status=status_code)



class PeriodCloseChecklistViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    """
    Screen 16: Period Close Manager. Status only moves through gate verification, three role sign-offs
    and the lock ceremony (see period_close_engine); it is never edited directly and a record is never deleted.
    """

    serializer_class = PeriodCloseChecklistSerializer

    def get_queryset(self):
        queryset = PeriodCloseChecklist.objects.select_related("pool__product")
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "auto_verify_gates"):
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker", "finance_checker"])()]
        if self.action == "sign_off_role":
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "shariah_secretariat", "shariah_board", "finance_checker"])()]
        if self.action in ("lock", "lock_ceremony", "certify"):
            return [IsAuthenticated(), HasAnyRole(["finance_checker", "authorized_signatory"])()]
        return [IsAuthenticated(), HasAnyRole(STAFF_ROLES)()]

    def perform_create(self, serializer):
        data = serializer.validated_data
        if data["period_start"] > data["period_end"]:
            raise ValidationError({"period_start": ["The period cannot start after it ends."]})
        overlapping = PeriodCloseChecklist.objects.filter(
            pool=data["pool"], period_start__lte=data["period_end"], period_end__gte=data["period_start"]
        )
        if overlapping.exists():
            raise ValidationError("A close record already covers part of this period.")
        instance = serializer.save(tenant=self.request.user.tenant, checklist_data={})
        log_action(
            tenant=instance.tenant, actor=self.request.user, action="create", model_name="PeriodCloseChecklist",
            object_id=str(instance.id), request=self.request,
        )

    @action(detail=True, methods=["post"], url_path="certify")
    def certify(self, request, pk=None):
        raise ValidationError(
            "A period is certified by the three role sign-offs (pool manager, Shariah reviewer, finance checker)."
        )

    @action(detail=True, methods=["post"], url_path="lock")
    def lock(self, request, pk=None):
        return self.lock_ceremony(request, pk)

    @action(detail=True, methods=["post"], url_path="auto-verify-gates")
    def auto_verify_gates(self, request, pk=None):
        from .period_close_engine import auto_verify_period_gates

        return Response(auto_verify_period_gates(self.get_object(), request.user))

    @action(detail=True, methods=["post"], url_path="sign-off-role")
    def sign_off_role(self, request, pk=None):
        from .period_close_engine import sign_off_period_role

        return Response(
            sign_off_period_role(
                period_close=self.get_object(), user=request.user, role=str(request.data.get("role") or ""),
                notes=str(request.data.get("notes") or ""), fatwa_ref=str(request.data.get("fatwa_ref") or ""),
            )
        )

    @action(detail=True, methods=["post"], url_path="lock-ceremony")
    def lock_ceremony(self, request, pk=None):
        from .period_close_engine import execute_cryptographic_lock_ceremony

        return Response(
            execute_cryptographic_lock_ceremony(
                period_close=self.get_object(), user=request.user, lock_note=str(request.data.get("lock_note") or "")
            )
        )

    @action(detail=True, methods=["get"], url_path="filing-package")
    def filing_package(self, request, pk=None):
        from .period_close_engine import get_sbp_filing_certificate

        return Response(get_sbp_filing_certificate(self.get_object()))


class AssetProvisionEntryViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    """Maker-checker provisions, write-offs and recoveries on assets (BRD 6.4)."""

    serializer_class = AssetProvisionEntrySerializer

    def get_queryset(self):
        queryset = AssetProvisionEntry.objects.select_related("asset", "pool", "created_by", "approved_by")
        for param in ("asset", "pool", "status"):
            value = self.request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{param: value})
        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), HasAnyRole(["finance_maker", "pool_manager"])()]
        if self.action in ("approve", "reject"):
            return [IsAuthenticated(), HasAnyRole(["finance_checker"])()]
        return [IsAuthenticated(), HasAnyRole(["finance_maker", "finance_checker", "pool_manager", "auditor",
                                               "risk_compliance", "shariah_board", "shariah_secretariat",
                                               "platform_super_admin"])()]

    def create(self, request, *args, **kwargs):
        from .provisions import create_entry

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        entry = create_entry(
            asset=data["asset"], entry_type=data["entry_type"], amount=data["amount"],
            effective_date=data["effective_date"], reason=data["reason"], user=request.user,
        )
        log_action(
            tenant=entry.tenant, actor=request.user, action=f"asset_{entry.entry_type}_requested",
            model_name="AssetProvisionEntry", object_id=str(entry.id),
            changes={"asset": str(entry.asset_id), "amount": str(entry.amount)}, reason=entry.reason,
            request=request,
        )
        return Response(self.get_serializer(entry).data, status=201)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from .provisions import approve_entry

        entry = approve_entry(self.get_object(), request.user)
        log_action(
            tenant=entry.tenant, actor=request.user, action=f"asset_{entry.entry_type}_approved",
            model_name="AssetProvisionEntry", object_id=str(entry.id),
            changes={"amount": str(entry.amount), "journal_batch": str(entry.journal_batch_id)}, request=request,
        )
        return Response(self.get_serializer(entry).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        from .provisions import reject_entry

        entry = reject_entry(self.get_object(), request.user, str(request.data.get("reason") or ""))
        log_action(
            tenant=entry.tenant, actor=request.user, action=f"asset_{entry.entry_type}_rejected",
            model_name="AssetProvisionEntry", object_id=str(entry.id), reason=entry.rejection_reason,
            request=request,
        )
        return Response(self.get_serializer(entry).data)

    @action(detail=False, methods=["get"])
    def position(self, request):
        """Provision balance / write-off / recovery position of one asset (?asset=<id>)."""
        from .provisions import asset_position

        asset = Asset.objects.filter(id=request.query_params.get("asset")).first()
        if asset is None:
            raise ValidationError({"asset": ["A valid asset is required."]})
        return Response({k: str(v) for k, v in asset_position(asset).items()})


class DailyCloseViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """BRD 6.2 daily close: the maker prepares (gates are computed by the server), an independent checker signs."""

    serializer_class = DailyCloseSerializer

    def get_queryset(self):
        queryset = DailyClose.objects.select_related("pool", "prepared_by", "signed_by")
        pool_id = self.request.query_params.get("pool")
        return queryset.filter(pool_id=pool_id) if pool_id else queryset

    def get_permissions(self):
        if self.action == "prepare":
            return [IsAuthenticated(), HasAnyRole(["finance_maker"])()]
        if self.action == "sign":
            return [IsAuthenticated(), HasAnyRole(["finance_checker"])()]
        return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker", "finance_checker", "risk_compliance", "auditor"])()]

    @action(detail=False, methods=["post"])
    def prepare(self, request):
        from . import daily_close

        try:
            pool = Pool.objects.select_related("product").get(pk=request.data.get("pool"))
            day = date.fromisoformat(str(request.data.get("value_date")))
        except (Pool.DoesNotExist, ValueError, TypeError, DjangoValidationError):
            raise ValidationError("A valid pool and value date (YYYY-MM-DD) are required.")
        close = daily_close.prepare(pool, day, request.user, notes=str(request.data.get("notes") or ""))
        log_action(
            tenant=pool.tenant, actor=request.user, action="daily_close_prepared", model_name="DailyClose",
            object_id=str(close.id), changes={"date": str(day), "status": close.status}, request=request,
        )
        return Response(self.get_serializer(close).data, status=201)

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        from . import daily_close

        close = daily_close.sign(self.get_object(), request.user)
        log_action(
            tenant=close.tenant, actor=request.user, action="daily_close_signed", model_name="DailyClose",
            object_id=str(close.id), changes={"date": str(close.value_date)}, request=request,
        )
        return Response(self.get_serializer(close).data)
