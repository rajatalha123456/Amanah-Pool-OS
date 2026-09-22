from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsFinanceChecker, IsFinanceMaker, IsPoolManager, IsRiskCompliance
from apps.core.audit import log_action
from apps.pools.models import Pool

from .models import (
    ArrearsRecord,
    ArrearsStatus,
    CircleMember,
    CircleMemberStatus,
    Contribution,
    ContributionStatus,
    Payout,
    PayoutStatus,
)
from .rotation import run_draw as run_draw_for_pool
from .serializers import ArrearsRecordSerializer, CircleMemberSerializer, ContributionSerializer, PayoutSerializer


class ContributionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Read-only: Contributions are only ever created via
    CircleMemberViewSet.record_contribution().
    """

    serializer_class = ContributionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Contribution.objects.all()
        member_id = self.request.query_params.get("member")
        pool_id = self.request.query_params.get("pool")
        if member_id:
            queryset = queryset.filter(member_id=member_id)
        if pool_id:
            queryset = queryset.filter(member__pool_id=pool_id)
        return queryset


class PayoutViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Read-only: Payouts are only ever created via
    CircleMemberViewSet.disburse_payout().
    """

    serializer_class = PayoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Payout.objects.all()
        pool_id = self.request.query_params.get("pool")
        member_id = self.request.query_params.get("member")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        if member_id:
            queryset = queryset.filter(member_id=member_id)
        return queryset


class CircleMemberViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CircleMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # See apps/products/views.py etc. for why this must be a method
        # rather than a class-level `queryset = Model.objects.all()`
        # attribute (TenantScopedManager + import-time evaluation bug).
        queryset = CircleMember.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "run_draw":
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "record_contribution":
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action == "disburse_payout":
            return [IsAuthenticated(), IsFinanceChecker()]
        if self.action == "flag_arrears":
            return [IsAuthenticated(), IsRiskCompliance()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="CircleMember",
            object_id=str(instance.id),
            changes={"member_reference": instance.member_reference, "member_name": instance.member_name},
            request=self.request,
        )

    @action(detail=False, methods=["post"], url_path="run-draw/(?P<pool_id>[^/.]+)")
    def run_draw(self, request, pool_id=None):
        try:
            pool = Pool.objects.get(pk=pool_id)
        except Pool.DoesNotExist:
            raise ValidationError("Pool not found.")

        result = run_draw_for_pool(pool)

        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="run_draw",
            model_name="Pool",
            object_id=str(pool.id),
            changes={"seed": result["seed"], "assignments": result["assignments"]},
            request=request,
        )
        return Response(result)

    @action(detail=True, methods=["post"], url_path="record-contribution")
    def record_contribution(self, request, pk=None):
        member = self.get_object()

        amount = request.data.get("amount")
        contribution_date = request.data.get("contribution_date")
        cycle_number = request.data.get("cycle_number")

        errors = {}
        if not amount:
            errors["amount"] = ["This field is required."]
        if not contribution_date:
            errors["contribution_date"] = ["This field is required."]
        if not cycle_number:
            errors["cycle_number"] = ["This field is required."]
        if errors:
            raise ValidationError(errors)

        contribution = Contribution.objects.create(
            tenant=member.tenant,
            member=member,
            amount=amount,
            contribution_date=contribution_date,
            cycle_number=cycle_number,
            status=ContributionStatus.RECEIVED,
        )

        log_action(
            tenant=member.tenant,
            actor=request.user,
            action="record_contribution",
            model_name="Contribution",
            object_id=str(contribution.id),
            changes={
                "member_id": str(member.id),
                "cycle_number": contribution.cycle_number,
                "amount": str(contribution.amount),
                "status": contribution.status,
            },
            request=request,
        )
        return Response(ContributionSerializer(contribution).data, status=201)

    @action(detail=True, methods=["post"], url_path="disburse-payout")
    def disburse_payout(self, request, pk=None):
        member = self.get_object()

        cycle_number = request.data.get("cycle_number")
        amount = request.data.get("amount")
        payout_date = request.data.get("payout_date")

        errors = {}
        if not cycle_number:
            errors["cycle_number"] = ["This field is required."]
        if not amount:
            errors["amount"] = ["This field is required."]
        if not payout_date:
            errors["payout_date"] = ["This field is required."]
        if errors:
            raise ValidationError(errors)

        if member.payout_position is None:
            raise ValidationError("This member has no payout_position assigned yet - run a draw first.")

        active_members = CircleMember.objects.filter(
            pool=member.pool, status=CircleMemberStatus.ACTIVE, payout_position__isnull=False
        )

        # The "turn" is whichever un-paid active member has the smallest
        # payout_position. A member can only be disbursed to once every
        # earlier position has already been paid out - this enforces the
        # rotation sequence rather than letting positions be paid out of
        # order.
        next_turn = active_members.order_by("payout_position").first()
        if next_turn is None or next_turn.id != member.id:
            expected = next_turn.payout_position if next_turn else None
            raise ValidationError(
                f"It is not this member's turn. Current turn is payout_position "
                f"{expected}, but this member is at position {member.payout_position}."
            )

        # Every active member must have a received Contribution for this
        # cycle before anyone can be paid out of it.
        active_member_ids = set(active_members.values_list("id", flat=True))
        received_member_ids = set(
            Contribution.objects.filter(
                member_id__in=active_member_ids,
                cycle_number=cycle_number,
                status=ContributionStatus.RECEIVED,
            ).values_list("member_id", flat=True)
        )
        missing = active_member_ids - received_member_ids
        if missing:
            raise ValidationError(
                f"Not all active members have contributed for cycle {cycle_number} yet "
                f"({len(missing)} member(s) still pending)."
            )

        payout = Payout.objects.create(
            tenant=member.tenant,
            member=member,
            pool=member.pool,
            cycle_number=cycle_number,
            amount=amount,
            payout_date=payout_date,
            status=PayoutStatus.DISBURSED,
            disbursed_by=request.user,
        )

        member.status = CircleMemberStatus.PAID_OUT
        member.save(update_fields=["status", "updated_at"])

        log_action(
            tenant=member.tenant,
            actor=request.user,
            action="disburse_payout",
            model_name="Payout",
            object_id=str(payout.id),
            changes={
                "member_id": str(member.id),
                "cycle_number": payout.cycle_number,
                "amount": str(payout.amount),
                "status": payout.status,
            },
            request=request,
        )
        return Response(PayoutSerializer(payout).data, status=201)

    @action(detail=True, methods=["post"], url_path="flag-arrears")
    def flag_arrears(self, request, pk=None):
        member = self.get_object()

        cycle_number = request.data.get("cycle_number")
        expected_amount = request.data.get("expected_amount")

        errors = {}
        if not cycle_number:
            errors["cycle_number"] = ["This field is required."]
        if not expected_amount:
            errors["expected_amount"] = ["This field is required."]
        if errors:
            raise ValidationError(errors)

        arrears = ArrearsRecord.objects.create(
            tenant=member.tenant,
            member=member,
            cycle_number=cycle_number,
            expected_amount=expected_amount,
            status=ArrearsStatus.OVERDUE,
        )

        log_action(
            tenant=member.tenant,
            actor=request.user,
            action="flag_arrears",
            model_name="ArrearsRecord",
            object_id=str(arrears.id),
            changes={
                "member_id": str(member.id),
                "cycle_number": arrears.cycle_number,
                "expected_amount": str(arrears.expected_amount),
                "status": arrears.status,
            },
            request=request,
        )
        return Response(ArrearsRecordSerializer(arrears).data, status=201)


class ArrearsRecordViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Read-only aside from grant_hardship: ArrearsRecords are created only
    via CircleMemberViewSet.flag_arrears().
    """

    serializer_class = ArrearsRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ArrearsRecord.objects.all()
        pool_id = self.request.query_params.get("pool")
        member_id = self.request.query_params.get("member")
        if pool_id:
            queryset = queryset.filter(member__pool_id=pool_id)
        if member_id:
            queryset = queryset.filter(member_id=member_id)
        return queryset

    def get_permissions(self):
        if self.action == "grant_hardship":
            return [IsAuthenticated(), HasAnyRole(["shariah_secretariat", "shariah_board"])()]
        return [IsAuthenticated()]

    @action(detail=True, methods=["post"], url_path="grant-hardship")
    def grant_hardship(self, request, pk=None):
        arrears = self.get_object()

        hardship_reason = request.data.get("hardship_reason")
        if not hardship_reason:
            raise ValidationError({"hardship_reason": ["This field is required."]})

        arrears.status = ArrearsStatus.HARDSHIP_GRANTED
        arrears.hardship_reason = hardship_reason
        arrears.reviewed_by = request.user
        arrears.reviewed_at = timezone.now()
        arrears.save(update_fields=["status", "hardship_reason", "reviewed_by", "reviewed_at", "updated_at"])

        log_action(
            tenant=arrears.tenant,
            actor=request.user,
            action="grant_hardship",
            model_name="ArrearsRecord",
            object_id=str(arrears.id),
            changes={"status": arrears.status, "hardship_reason": arrears.hardship_reason},
            request=request,
        )
        return Response(ArrearsRecordSerializer(arrears).data)
