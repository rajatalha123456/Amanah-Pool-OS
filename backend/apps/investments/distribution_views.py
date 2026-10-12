from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounting.models import JournalBatch
from apps.accounting.services import create_journal_from_distribution, create_reversal_journal
from apps.accounts.permissions import HasAnyRole, IsFinanceChecker, IsFinanceMaker
from apps.accounts.approval_matrix import assert_may_approve
from apps.accounts.workflow import validate_maker_checker
from apps.core.audit import log_action
from apps.notifications import events
from apps.pools.period_lock import assert_period_open

from .distribution import calculate_distribution, compute_run_hash
from .models import DistributionRunStatus, InvestmentDistributionLine, InvestmentDistributionRun, NegligenceCase
from .negligence import liable_cases, open_cases
from .serializers import DistributionRunSerializer


class DistributionInputSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    gross_income = serializers.DecimalField(max_digits=18, decimal_places=2)
    direct_expenses = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.pools.models import Pool

        self.fields["pool"] = serializers.PrimaryKeyRelatedField(queryset=Pool.objects.all())

    def validate(self, attrs):
        if attrs["period_start"] > attrs["period_end"]:
            raise serializers.ValidationError({"period_start": "period_start cannot be after period_end."})
        return attrs


class RestatementInputSerializer(serializers.Serializer):
    restatement_reason = serializers.CharField()
    gross_income = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=None)
    direct_expenses = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=None)


def _verify_negligence_state(run):
    """
    A Musharakah loss may only be signed while its negligence picture is unchanged: no investigation
    opened for the period since it was calculated, and the same liability determinations apply.
    Returns the ids of the liability cases the run applies.
    """

    snapshot = run.config_snapshot or {}
    if snapshot.get("contract_type") != "musharakah" or not run.is_loss:
        return []
    blocking = open_cases(run.pool, run.period_start, run.period_end)
    if blocking:
        raise ValidationError(
            f"Loss allocation is frozen: negligence case '{blocking[0].title}' is under investigation for this period."
        )
    expected = sorted(c["id"] for c in (snapshot.get("musharakah") or {}).get("liability_cases", []))
    current = sorted(
        str(c.id) for c in liable_cases(run.pool, run.period_start, run.period_end, replaces_run=run.replaces_run)
    )
    if expected != current:
        raise ValidationError(
            "The negligence determinations for this period changed after the run was calculated. "
            "Reject it and re-run the distribution."
        )
    return expected


def _persist(*, user, pool, period_start, period_end, gross_income, direct_expenses, result, **extra):
    with transaction.atomic():
        run = InvestmentDistributionRun.objects.create(
            tenant=user.tenant,
            pool=pool,
            period_start=period_start,
            period_end=period_end,
            gross_income=gross_income,
            direct_expenses=direct_expenses,
            distributable_amount=result["distributable"],
            investor_share=result["investor_share"],
            manager_share=result["manager_share"],
            rounding_residual=result["rounding_residual"],
            total_average_units=result["total_average_units"],
            is_loss=result["is_loss"],
            config_snapshot=result["config_snapshot"],
            status=DistributionRunStatus.SIMULATED,
            created_by=user,
            **extra,
        )
        InvestmentDistributionLine.objects.bulk_create(
            [
                InvestmentDistributionLine(
                    tenant=user.tenant,
                    run=run,
                    capital_account_id=line["capital_account_id"],
                    average_units=line["average_units"],
                    share_ratio=line["share_ratio"],
                    allocated_amount=line["allocated_amount"],
                )
                for line in result["lines"]
            ]
        )
        run.refresh_from_db()
        run.calculation_hash = compute_run_hash(run)
        run.save(update_fields=["calculation_hash", "updated_at"])
    return run


class DistributionRunViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = DistributionRunSerializer

    def get_queryset(self):
        # Investors never see runs (they would expose every investor's allocation);
        # they read their own figures from the capital-account statement.
        if self.request.user.role == "investor_member":
            return InvestmentDistributionRun.objects.none()
        queryset = InvestmentDistributionRun.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "simulate", "restate"):
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker"])()]
        if self.action == "submit_for_checking":
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action in ("approve", "reject"):
            return [IsAuthenticated(), IsFinanceChecker()]
        return [IsAuthenticated()]

    def _calculate(self, request):
        serializer = DistributionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            result = calculate_distribution(
                data["pool"], data["period_start"], data["period_end"], data["gross_income"], data["direct_expenses"]
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return data, result

    @action(detail=False, methods=["post"])
    def simulate(self, request):
        _, result = self._calculate(request)
        return Response(result)

    def create(self, request, *args, **kwargs):
        data, result = self._calculate(request)
        assert_period_open(data["pool"], data["period_end"], what="a profit distribution", start=data["period_start"])
        run = _persist(
            user=request.user,
            pool=data["pool"],
            period_start=data["period_start"],
            period_end=data["period_end"],
            gross_income=data["gross_income"],
            direct_expenses=data["direct_expenses"],
            result=result,
        )
        log_action(
            tenant=run.tenant, actor=request.user, action="create", model_name="InvestmentDistributionRun",
            object_id=str(run.id),
            changes={
                "distributable_amount": str(run.distributable_amount),
                "investor_share": str(run.investor_share),
                "manager_share": str(run.manager_share),
                "calculation_hash": run.calculation_hash,
            },
            request=request,
        )
        return Response(self.get_serializer(run).data, status=201)

    @action(detail=True, methods=["post"], url_path="submit-for-checking")
    def submit_for_checking(self, request, pk=None):
        run = self.get_object()
        if run.status != DistributionRunStatus.SIMULATED:
            raise ValidationError(f"Only a simulated run can be submitted (current status: '{run.status}').")
        run.status = DistributionRunStatus.PENDING_APPROVAL
        run.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=run.tenant, actor=request.user, action="submit_for_checking",
            model_name="InvestmentDistributionRun", object_id=str(run.id), request=request,
        )
        events.distribution_submitted(run, request.user)
        return Response(self.get_serializer(run).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        run = self.get_object()
        if run.status != DistributionRunStatus.PENDING_APPROVAL:
            raise ValidationError(f"Only a pending run can be approved (current status: '{run.status}').")
        assert_may_approve(request.user, run.tenant_id, "distribution_approve", run.distributable_amount)
        try:
            validate_maker_checker(maker_user=run.created_by, checker_user=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message) from exc

        if not run.calculation_hash or compute_run_hash(run) != run.calculation_hash:
            raise ValidationError(
                "Calculation hash mismatch: the run no longer matches the figures it was sealed with. "
                "Reject it and re-run the distribution."
            )
        if not run.is_restatement:
            assert_period_open(run.pool, run.period_end, what="a profit distribution", start=run.period_start)
        case_ids = _verify_negligence_state(run)

        try:
            with transaction.atomic():
                reversal = None
                if run.is_restatement:
                    old = InvestmentDistributionRun.objects.select_for_update().get(pk=run.replaces_run_id)
                    if old.status != DistributionRunStatus.SIGNED:
                        raise ValidationError(f"The run being restated is no longer signed (status '{old.status}').")
                    old_batch = JournalBatch.objects.filter(investment_run=old).first()
                    if old_batch is not None:
                        reversal = create_reversal_journal(old_batch, posted_by=request.user)
                    old.status = DistributionRunStatus.REVERSED
                    old.restatement_reason = run.restatement_reason
                    old.save(update_fields=["status", "restatement_reason", "updated_at"])
                else:
                    overlap = (
                        InvestmentDistributionRun.objects.filter(
                            pool=run.pool, status=DistributionRunStatus.SIGNED,
                            period_end__gte=run.period_start, period_start__lte=run.period_end,
                        ).exclude(pk=run.pk)
                    )
                    if overlap.exists():
                        raise ValidationError(
                            f"A signed distribution already covers part of {run.period_start} to {run.period_end}; "
                            "use a restatement to correct it."
                        )

                run.status = DistributionRunStatus.SIGNED
                if case_ids:
                    NegligenceCase._base_manager.filter(tenant_id=run.tenant_id, id__in=case_ids).update(applied_run=run)
                run.checked_by = request.user
                run.checked_at = timezone.now()
                run.save(update_fields=["status", "checked_by", "checked_at", "updated_at"])
                batch = create_journal_from_distribution(run, posted_by=request.user)
        except (ValueError, DjangoValidationError) as exc:
            raise ValidationError(getattr(exc, "message", None) or str(exc)) from exc

        log_action(
            tenant=run.tenant, actor=request.user, action="approve", model_name="InvestmentDistributionRun",
            object_id=str(run.id),
            changes={
                "journal_batch_id": str(batch.id),
                "reversal_batch_id": str(reversal.id) if reversal else None,
                "total_debit": str(batch.total_debit),
            },
            request=request,
        )
        events.distribution_decided(run, request.user, True)
        return Response(self.get_serializer(run).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        run = self.get_object()
        if run.status != DistributionRunStatus.PENDING_APPROVAL:
            raise ValidationError(f"Only a pending run can be rejected (current status: '{run.status}').")
        reason = (request.data.get("rejection_reason") or "").strip()
        if not reason:
            raise ValidationError({"rejection_reason": ["This field is required."]})
        run.status = DistributionRunStatus.REJECTED
        run.checked_by = request.user
        run.checked_at = timezone.now()
        run.rejection_reason = reason
        run.save(update_fields=["status", "checked_by", "checked_at", "rejection_reason", "updated_at"])
        log_action(
            tenant=run.tenant, actor=request.user, action="reject", model_name="InvestmentDistributionRun",
            object_id=str(run.id), reason=reason, request=request,
        )
        events.distribution_decided(run, request.user, False, reason)
        return Response(self.get_serializer(run).data)

    @action(detail=True, methods=["post"])
    def restate(self, request, pk=None):
        """BR-004: propose a corrected linked rerun; the original stays signed until the rerun is approved."""
        old = self.get_object()
        if old.status != DistributionRunStatus.SIGNED:
            raise ValidationError("Only a signed run can be restated.")
        if InvestmentDistributionRun.objects.filter(
            replaces_run=old,
            status__in=[DistributionRunStatus.SIMULATED, DistributionRunStatus.PENDING_APPROVAL],
        ).exists():
            raise ValidationError("A restatement of this run is already awaiting approval.")

        serializer = RestatementInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["restatement_reason"].strip()
        if not reason:
            raise ValidationError({"restatement_reason": ["A reason is required."]})
        gross = serializer.validated_data["gross_income"]
        expenses = serializer.validated_data["direct_expenses"]
        gross = old.gross_income if gross is None else gross
        expenses = old.direct_expenses if expenses is None else expenses

        try:
            result = calculate_distribution(old.pool, old.period_start, old.period_end, gross, expenses, replaces_run=old)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        new_run = _persist(
            user=request.user, pool=old.pool, period_start=old.period_start, period_end=old.period_end,
            gross_income=gross, direct_expenses=expenses, result=result,
            replaces_run=old, is_restatement=True, restatement_reason=reason,
        )
        log_action(
            tenant=old.tenant, actor=request.user, action="restate", model_name="InvestmentDistributionRun",
            object_id=str(new_run.id), reason=reason, changes={"replaces_run": str(old.id)}, request=request,
        )
        return Response(self.get_serializer(new_run).data, status=201)
