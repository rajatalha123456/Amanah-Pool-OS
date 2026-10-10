from decimal import Decimal
import logging

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
    IsPoolManager,
    IsShariahBoard,
    IsShariahSecretariat,
)
from apps.accounts.workflow import validate_maker_checker
from apps.core.audit import log_action
from apps.pools.period_lock import assert_period_open

from .engine import calculate_allocation, compute_run_hash
from .reserves import apply_reserve_movements, reverse_reserve_movements
from .models import (
    AllocationLine,
    AllocationRun,
    AllocationRunStatus,
    DepositorStatement,
    PSRStatus,
    ProfitSharingRatio,
    ReservePolicy,
    WeightageBand,
    WeightageBandStatus,
)
from .serializers import (
    AllocationRunInputSerializer,
    AllocationRunSerializer,
    DepositorStatementSerializer,
    PSRSerializer,
    ReservePolicySerializer,
    RestatementInputSerializer,
    WeightageBandSerializer,
)
from .statements import generate_statement_narrative

logger = logging.getLogger("apps")


def _persist_run(*, user, pool, value_date, gross_income, direct_expenses, result, **extra):
    """
    Stores a calculated result as an AllocationRun (status "simulated") with
    its lines and seals it with the calculation hash. Used by both the normal
    create flow and the restatement rerun so they are hashed identically.
    """

    with transaction.atomic():
        run = AllocationRun.objects.create(
            tenant=user.tenant,
            pool=pool,
            value_date=value_date,
            gross_income=gross_income,
            direct_expenses=direct_expenses,
            distributable_amount=result["distributable"],
            total_weighted_funds=result["total_weighted_funds"],
            depositor_pool_share=result["depositor_pool_share"],
            mudarib_share=result["mudarib_share"],
            per_amount=result["per_amount"],
            irr_amount=result["irr_amount"],
            rounding_residual=result["rounding_residual"],
            is_loss=result["is_loss"],
            config_snapshot=result["config_snapshot"],
            status=AllocationRunStatus.SIMULATED,
            created_by=user,
            **extra,
        )

        AllocationLine.objects.bulk_create(
            [
                AllocationLine(
                    tenant=user.tenant,
                    allocation_run=run,
                    participant_class=line["participant_class"],
                    daily_funds=line["daily_funds"],
                    weightage=line["weightage"],
                    weighted_funds=line["weighted_funds"],
                    allocated_amount=line["allocated_amount"],
                )
                for line in result["lines"]
            ]
        )

        # Re-read so the hash is taken over exactly what the database holds.
        run.refresh_from_db()
        run.calculation_hash = compute_run_hash(run)
        run.save(update_fields=["calculation_hash", "updated_at"])
    return run


def _reverse_replaced_run(new_run, user):
    """
    Called when a restatement rerun is approved: reverses the run it
    replaces (contra journal, reserve movements, status REVERSED) so the
    rerun can be signed in its place. Returns the reversal JournalBatch
    (None if the original run never posted one).
    """

    from apps.accounting.models import JournalBatch
    from apps.accounting.services import create_reversal_journal

    old_run = AllocationRun.objects.select_for_update().get(pk=new_run.replaces_run_id)
    if old_run.status != AllocationRunStatus.SIGNED:
        raise ValidationError(
            f"The run being restated is no longer signed (current status: '{old_run.status}')."
        )

    reversal_batch = None
    old_batch = JournalBatch.objects.filter(allocation_run=old_run).first()
    if old_batch is not None:
        reversal_batch = create_reversal_journal(old_batch, posted_by=user)

    reverse_reserve_movements(old_run)

    old_run.status = AllocationRunStatus.REVERSED
    old_run.restatement_reason = new_run.restatement_reason
    old_run.save(update_fields=["status", "restatement_reason", "updated_at"])
    return reversal_batch


class WeightageBandViewSet(viewsets.ModelViewSet):
    serializer_class = WeightageBandSerializer

    def get_queryset(self):
        # See apps/products/views.py and apps/pools/views.py for why this
        # must be a method rather than a class-level
        # `queryset = Model.objects.all()` attribute (TenantScopedManager +
        # import-time evaluation bug).
        queryset = WeightageBand.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="WeightageBand",
            object_id=str(instance.id),
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        band = self.get_object()

        if band.status != WeightageBandStatus.DRAFT:
            raise ValidationError(
                f"WeightageBand must be in '{WeightageBandStatus.DRAFT}' status to approve "
                f"(current status: '{band.status}')."
            )

        band.status = WeightageBandStatus.APPROVED
        band.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=band.tenant,
            actor=request.user,
            action="approve",
            model_name="WeightageBand",
            object_id=str(band.id),
            changes={"status": {"before": WeightageBandStatus.DRAFT, "after": WeightageBandStatus.APPROVED}},
            request=request,
        )
        return Response(self.get_serializer(band).data)


class PSRViewSet(viewsets.ModelViewSet):
    serializer_class = PSRSerializer

    def get_queryset(self):
        queryset = ProfitSharingRatio.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), IsPoolManager()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="ProfitSharingRatio",
            object_id=str(instance.id),
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        psr = self.get_object()

        if psr.status != PSRStatus.DRAFT:
            raise ValidationError(
                f"ProfitSharingRatio must be in '{PSRStatus.DRAFT}' status to approve "
                f"(current status: '{psr.status}')."
            )

        psr.status = PSRStatus.APPROVED
        psr.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=psr.tenant,
            actor=request.user,
            action="approve",
            model_name="ProfitSharingRatio",
            object_id=str(psr.id),
            changes={"status": {"before": PSRStatus.DRAFT, "after": PSRStatus.APPROVED}},
            request=request,
        )
        return Response(self.get_serializer(psr).data)


class AllocationRunViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AllocationRunSerializer

    def get_queryset(self):
        # See apps/products/views.py, apps/pools/views.py for why this
        # must be a method rather than a class-level
        # `queryset = Model.objects.all()` attribute (TenantScopedManager +
        # import-time evaluation bug).
        queryset = AllocationRun.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action in ("create", "simulate", "generate_statements"):
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker"])()]
        if self.action == "submit_for_checking":
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action == "shariah_sign_off":
            # BRD 6.3: the Shariah authority (Board) approves; the Secretariat
            # only prepares the review pack and holds no final authority.
            return [IsAuthenticated(), IsShariahBoard()]
        if self.action in ("approve", "reject"):
            return [IsAuthenticated(), IsFinanceChecker()]
        if self.action == "restate":
            # Initiated by a maker; the checker approves the linked rerun.
            return [IsAuthenticated(), HasAnyRole(["finance_maker", "pool_manager"])()]
        if self.action in ("simulate_hiba", "apply_hiba"):
            return [IsAuthenticated(), HasAnyRole(["finance_maker", "finance_checker", "pool_manager"])()]
        return [IsAuthenticated()]

    def _run_calculation(self, request):
        input_serializer = AllocationRunInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        try:
            result = calculate_allocation(
                pool=data["pool"],
                value_date=data["value_date"],
                gross_income=data["gross_income"],
                direct_expenses=data["direct_expenses"],
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        return data, result

    @action(detail=False, methods=["post"])
    def simulate(self, request):
        """
        Runs the allocation calculation and returns the result directly.
        Nothing is written to the database.
        """
        _, result = self._run_calculation(request)
        return Response(
            {
                "distributable": result["distributable"],
                "total_weighted_funds": result["total_weighted_funds"],
                "depositor_pool_share": result["depositor_pool_share"],
                "mudarib_share": result["mudarib_share"],
                "per_amount": result["per_amount"],
                "irr_amount": result["irr_amount"],
                "rounding_residual": result["rounding_residual"],
                "is_loss": result["is_loss"],
                "lines": result["lines"],
            }
        )

    def create(self, request, *args, **kwargs):
        """
        Runs the allocation calculation and persists it as an
        AllocationRun + AllocationLine rows, status="simulated".
        """
        data, result = self._run_calculation(request)

        # A closed period accepts no new runs; corrections go through restatement.
        assert_period_open(data["pool"], data["value_date"], what="an allocation run")

        run = _persist_run(
            user=request.user,
            pool=data["pool"],
            value_date=data["value_date"],
            gross_income=data["gross_income"],
            direct_expenses=data["direct_expenses"],
            result=result,
        )

        log_action(
            tenant=run.tenant,
            actor=request.user,
            action="create",
            model_name="AllocationRun",
            object_id=str(run.id),
            changes={
                "distributable_amount": str(run.distributable_amount),
                "total_weighted_funds": str(run.total_weighted_funds),
                "depositor_pool_share": str(run.depositor_pool_share),
                "mudarib_share": str(run.mudarib_share),
                "per_amount": str(run.per_amount),
                "irr_amount": str(run.irr_amount),
                "rounding_residual": str(run.rounding_residual),
                "line_count": len(result["lines"]),
                "calculation_hash": run.calculation_hash,
            },
            request=request,
        )

        return Response(self.get_serializer(run).data, status=201)

    @action(detail=True, methods=["post"], url_path="submit-for-checking")
    def submit_for_checking(self, request, pk=None):
        run = self.get_object()

        if run.status != AllocationRunStatus.SIMULATED:
            raise ValidationError(
                f"AllocationRun must be in '{AllocationRunStatus.SIMULATED}' status to submit "
                f"for checking (current status: '{run.status}')."
            )

        run.status = AllocationRunStatus.PENDING_APPROVAL
        run.save(update_fields=["status", "updated_at"])
        log_action(
            tenant=run.tenant,
            actor=request.user,
            action="submit_for_checking",
            model_name="AllocationRun",
            object_id=str(run.id),
            changes={
                "status": {
                    "before": AllocationRunStatus.SIMULATED,
                    "after": AllocationRunStatus.PENDING_APPROVAL,
                }
            },
            request=request,
        )
        return Response(self.get_serializer(run).data)

    @action(detail=True, methods=["post"], url_path="shariah-sign-off")
    def shariah_sign_off(self, request, pk=None):
        run = self.get_object()

        if not run.shariah_review_required:
            raise ValidationError(
                "This AllocationRun's pool does not require Shariah review."
            )

        if run.status != AllocationRunStatus.PENDING_APPROVAL:
            raise ValidationError(
                f"AllocationRun must be in '{AllocationRunStatus.PENDING_APPROVAL}' status for "
                f"Shariah sign-off (current status: '{run.status}')."
            )

        run.status = AllocationRunStatus.SHARIAH_REVIEW
        run.shariah_signed_off_by = request.user
        run.shariah_signed_off_at = timezone.now()
        run.shariah_review_note = request.data.get("note")
        run.save(
            update_fields=[
                "status",
                "shariah_signed_off_by",
                "shariah_signed_off_at",
                "shariah_review_note",
                "updated_at",
            ]
        )
        log_action(
            tenant=run.tenant,
            actor=request.user,
            action="shariah_sign_off",
            model_name="AllocationRun",
            object_id=str(run.id),
            changes={
                "status": {
                    "before": AllocationRunStatus.PENDING_APPROVAL,
                    "after": AllocationRunStatus.SHARIAH_REVIEW,
                }
            },
            reason=run.shariah_review_note,
            request=request,
        )
        return Response(self.get_serializer(run).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        # Local import: apps.accounting depends on apps.allocation's
        # models, so importing at module level here would create a
        # circular import between the two apps.
        from apps.accounting.services import create_journal_from_allocation

        from .anomaly_detector import check_for_anomalies

        run = self.get_object()

        required_status = (
            AllocationRunStatus.SHARIAH_REVIEW
            if run.shariah_review_required
            else AllocationRunStatus.PENDING_APPROVAL
        )
        if run.status != required_status:
            raise ValidationError(
                f"AllocationRun must be in '{required_status}' status to "
                f"approve (current status: '{run.status}')."
            )

        try:
            validate_maker_checker(maker_user=run.created_by, checker_user=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message) from exc

        previous_status = run.status

        # The checker signs exactly what the maker calculated: re-derive the
        # hash from the stored inputs, rule versions, amounts and lines.
        if not run.calculation_hash or compute_run_hash(run) != run.calculation_hash:
            raise ValidationError(
                "Calculation hash mismatch: the run no longer matches the figures it was sealed with. "
                "Reject it and re-run the allocation."
            )

        if not run.is_restatement:
            assert_period_open(run.pool, run.value_date, what="an allocation run")

        try:
            with transaction.atomic():
                reversal_batch = None
                if run.is_restatement:
                    reversal_batch = _reverse_replaced_run(run, request.user)
                else:
                    duplicate = AllocationRun.objects.filter(
                        pool=run.pool, value_date=run.value_date, status=AllocationRunStatus.SIGNED
                    ).exclude(pk=run.pk)
                    if duplicate.exists():
                        raise ValidationError(
                            f"A signed allocation run already exists for {run.pool.code} on "
                            f"{run.value_date}; use a restatement to correct it."
                        )

                apply_reserve_movements(run)

                run.status = AllocationRunStatus.SIGNED
                run.checked_by = request.user
                run.checked_at = timezone.now()
                run.save(update_fields=["status", "checked_by", "checked_at", "updated_at"])

                journal_batch = create_journal_from_allocation(run, posted_by=request.user)
        except (ValueError, DjangoValidationError) as exc:
            # JournalIntegrityError / reserve-cap errors block the approval and
            # roll the whole transaction back - nothing is signed or posted.
            message = getattr(exc, "message", None) or str(exc)
            raise ValidationError(message) from exc

        if reversal_batch is not None:
            log_action(
                tenant=run.tenant,
                actor=request.user,
                action="reverse",
                model_name="AllocationRun",
                object_id=str(run.replaces_run_id),
                changes={
                    "status": {"before": AllocationRunStatus.SIGNED, "after": AllocationRunStatus.REVERSED},
                    "reversal_batch_id": str(reversal_batch.id),
                    "replaced_by": str(run.id),
                },
                reason=run.restatement_reason,
                request=request,
            )

        log_action(
            tenant=run.tenant,
            actor=request.user,
            action="approve",
            model_name="AllocationRun",
            object_id=str(run.id),
            changes={
                "status": {
                    "before": previous_status,
                    "after": AllocationRunStatus.SIGNED,
                },
                "journal_batch_id": str(journal_batch.id),
                "total_debit": str(journal_batch.total_debit),
                "total_credit": str(journal_batch.total_credit),
            },
            request=request,
        )
        log_action(
            tenant=journal_batch.tenant,
            actor=request.user,
            action="create",
            model_name="JournalBatch",
            object_id=str(journal_batch.id),
            changes={
                "total_debit": str(journal_batch.total_debit),
                "total_credit": str(journal_batch.total_credit),
                "allocation_run_id": str(run.id),
            },
            request=request,
        )

        # Best-effort: a failure here must never block a successful approve
        # (the run is already signed and the journal is already posted).
        try:
            check_for_anomalies(run)
        except Exception:
            logger.exception("Anomaly check failed for AllocationRun %s", run.id)

        return Response(self.get_serializer(run).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        run = self.get_object()

        rejectable_statuses = (
            AllocationRunStatus.PENDING_APPROVAL,
            AllocationRunStatus.SHARIAH_REVIEW,
        )
        if run.status not in rejectable_statuses:
            raise ValidationError(
                f"AllocationRun must be in '{AllocationRunStatus.PENDING_APPROVAL}' or "
                f"'{AllocationRunStatus.SHARIAH_REVIEW}' status to reject "
                f"(current status: '{run.status}')."
            )

        rejection_reason = request.data.get("rejection_reason")
        if not rejection_reason:
            raise ValidationError({"rejection_reason": ["This field is required."]})

        previous_status = run.status
        run.status = AllocationRunStatus.REJECTED
        run.checked_by = request.user
        run.checked_at = timezone.now()
        run.rejection_reason = rejection_reason
        run.save(update_fields=["status", "checked_by", "checked_at", "rejection_reason", "updated_at"])

        log_action(
            tenant=run.tenant,
            actor=request.user,
            action="reject",
            model_name="AllocationRun",
            object_id=str(run.id),
            changes={
                "status": {
                    "before": previous_status,
                    "after": AllocationRunStatus.REJECTED,
                }
            },
            reason=rejection_reason,
            request=request,
        )
        return Response(self.get_serializer(run).data)

    @action(detail=True, methods=["post"], url_path="generate-statements")
    def generate_statements(self, request, pk=None):
        run = self.get_object()

        if run.status != AllocationRunStatus.SIGNED:
            raise ValidationError(
                "Statements can only be generated for signed allocation runs."
            )

        existing = list(DepositorStatement.objects.filter(allocation_run=run))
        if existing:
            return Response(DepositorStatementSerializer(existing, many=True).data)

        statements = []
        for line in run.lines.all():
            opening_balance = line.daily_funds
            net_deposits = 0
            profit_allocated = line.allocated_amount
            closing_balance = opening_balance + net_deposits + profit_allocated

            narrative = generate_statement_narrative(
                participant_class=line.participant_class,
                opening_balance=opening_balance,
                profit_allocated=profit_allocated,
                weightage=line.weightage,
                allocation_run=run,
            )

            statements.append(
                DepositorStatement(
                    tenant=run.tenant,
                    allocation_run=run,
                    participant_class=line.participant_class,
                    period_start=run.value_date,
                    period_end=run.value_date,
                    opening_balance=opening_balance,
                    net_deposits=net_deposits,
                    profit_allocated=profit_allocated,
                    closing_balance=closing_balance,
                    narrative=narrative,
                )
            )

        created = DepositorStatement.objects.bulk_create(statements)

        log_action(
            tenant=run.tenant,
            actor=request.user,
            action="generate_statements",
            model_name="AllocationRun",
            object_id=str(run.id),
            changes={"statement_count": len(created)},
            request=request,
        )

        return Response(DepositorStatementSerializer(created, many=True).data)

    @action(detail=True, methods=["get"])
    def statements(self, request, pk=None):
        run = self.get_object()
        statements = run.statements.all()
        return Response(DepositorStatementSerializer(statements, many=True).data)

    @action(detail=True, methods=["post"])
    def restate(self, request, pk=None):
        """
        Screen 17: Restatement Wizard - Controlled reversal and linked rerun.
        BR-004: A signed allocation run is immutable; corrections require reversal
        and a linked rerun.

        This only *proposes* the correction: it recalculates and stores a
        linked rerun (status "simulated") that goes through the normal
        maker-checker / Shariah approval. The original run stays signed
        until the rerun is approved; approval then reverses the original
        (contra journal + reserve movements) and signs the rerun together.
        """
        old_run = self.get_object()
        if old_run.status != AllocationRunStatus.SIGNED:
            raise ValidationError("Only a signed AllocationRun can be restated.")

        open_rerun = AllocationRun.objects.filter(
            replaces_run=old_run,
            status__in=[
                AllocationRunStatus.SIMULATED,
                AllocationRunStatus.PENDING_APPROVAL,
                AllocationRunStatus.SHARIAH_REVIEW,
            ],
        )
        if open_rerun.exists():
            raise ValidationError("A restatement of this run is already awaiting approval.")

        serializer = RestatementInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        restatement_reason = serializer.validated_data["restatement_reason"].strip()
        if not restatement_reason:
            raise ValidationError({"restatement_reason": ["A reason is required."]})

        new_gross_income = serializer.validated_data.get("gross_income")
        if new_gross_income is None:
            new_gross_income = old_run.gross_income
        new_direct_expenses = serializer.validated_data.get("direct_expenses")
        if new_direct_expenses is None:
            new_direct_expenses = old_run.direct_expenses

        try:
            calc_result = calculate_allocation(
                old_run.pool, old_run.value_date, new_gross_income, new_direct_expenses
            )
        except ValueError as exc:
            # No silent fallback: a restatement must be recalculated from the
            # real balances and the approved rules.
            raise ValidationError(str(exc)) from exc

        new_run = _persist_run(
            user=request.user,
            pool=old_run.pool,
            value_date=old_run.value_date,
            gross_income=new_gross_income,
            direct_expenses=new_direct_expenses,
            result=calc_result,
            replaces_run=old_run,
            is_restatement=True,
            restatement_reason=restatement_reason,
        )

        log_action(
            tenant=old_run.tenant,
            actor=request.user,
            action="restate",
            model_name="AllocationRun",
            object_id=str(new_run.id),
            reason=restatement_reason,
            changes={
                "replaces_run": str(old_run.id),
                "impact": {
                    "distributable_before": str(old_run.distributable_amount),
                    "distributable_after": str(new_run.distributable_amount),
                    "mudarib_before": str(old_run.mudarib_share),
                    "mudarib_after": str(new_run.mudarib_share),
                },
            },
            request=request,
        )
        return Response(self.get_serializer(new_run).data, status=201)

    @action(detail=True, methods=["post", "get"], url_path="simulate-hiba")
    def simulate_hiba(self, request, pk=None):
        """
        Screen 19 / Module 07: Mudarib Fee Optimization & Hiba Yield Simulator.
        Simulates AAOIFI Standard No. 13 voluntary reduction to match KIBOR benchmark.
        """
        from .services.hiba_simulator import simulate_mudarib_hiba

        run = self.get_object()
        target_kibor = request.data.get("target_kibor") or request.query_params.get("target_kibor") or 17.50
        hiba_amount = request.data.get("hiba_amount")
        mudarib_rate = request.data.get("mudarib_rate")

        result = simulate_mudarib_hiba(
            allocation_run=run,
            target_kibor_rate=Decimal(str(target_kibor)),
            simulated_hiba_amount=Decimal(str(hiba_amount)) if hiba_amount is not None else None,
            simulated_mudarib_rate=Decimal(str(mudarib_rate)) if mudarib_rate is not None else None,
        )
        return Response(result)

    @action(detail=True, methods=["post"], url_path="apply-hiba")
    def apply_hiba(self, request, pk=None):
        """
        Screen 19: Apply approved Hiba concession to AllocationRun.
        """
        from .services.hiba_simulator import apply_mudarib_hiba

        run = self.get_object()
        hiba_amount = request.data.get("hiba_amount")
        if hiba_amount is None:
            raise ValidationError({"hiba_amount": ["This field is required."]})

        justification = request.data.get("justification", "ALCO Yield Optimization concession against KIBOR benchmark")

        try:
            result = apply_mudarib_hiba(
                allocation_run=run,
                hiba_amount=Decimal(str(hiba_amount)),
                user=request.user,
                justification=justification,
            )
            return Response(result)
        except ValueError as e:
            raise ValidationError(str(e))



class ReservePolicyViewSet(viewsets.ModelViewSet):
    serializer_class = ReservePolicySerializer
    # Reserve policies change distributable economics: no hard delete.
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), IsPoolManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = ReservePolicy.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class PayoutClearingViewSet(viewsets.ViewSet):
    """
    BRD Module 14 / Screen 35: Core-Banking Clearing & Raast / 1LINK Payout Batch Simulator.
    Handles automated batch generation from certified allocation runs,
    5-gate pre-disbursement verification, ISO 20022 pacs.008 XML creation,
    live settlement simulation, and contra-GL posting.
    """
    _READ_ROLES = ["pool_manager", "finance_maker", "finance_checker", "auditor", "risk_compliance"]

    def get_permissions(self):
        # Payout batches move money: reads are for finance/oversight roles,
        # preparation for the maker, authorisation/dispatch/posting for the
        # checker only (maker-checker).
        if self.action in ("list", "batch_detail", "download_iso_pacs008"):
            return [IsAuthenticated(), HasAnyRole(self._READ_ROLES)()]
        if self.action == "verify_gates":
            return [IsAuthenticated(), HasAnyRole(["finance_maker", "finance_checker"])()]
        if self.action in ("authorize", "dispatch_simulate", "post_contra_gl"):
            return [IsAuthenticated(), IsFinanceChecker()]
        return [IsAuthenticated(), IsFinanceChecker()]

    def list(self, request):
        """List all allocation runs eligible for or possessing a payout clearing batch."""
        from .models import AllocationRun, AllocationRunStatus
        from .payout_clearing_engine import PayoutClearingEngine

        runs = AllocationRun.objects.filter(
            status__in=[AllocationRunStatus.SIGNED, AllocationRunStatus.PENDING_APPROVAL, AllocationRunStatus.SHARIAH_REVIEW]
        ).order_by("-value_date")

        batches = []
        for r in runs:
            b = PayoutClearingEngine.get_or_create_batch_for_run(r, request.user.tenant)
            batches.append({
                "allocation_run_id": str(r.id),
                "pool_code": r.pool.code,
                "pool_name": r.pool.name,
                "value_date": r.value_date.isoformat(),
                "period_month": b["period_month"],
                "batch_code": b["batch_code"],
                "status": b["status"],
                "total_records": b["total_records"],
                "total_gross_profit": b["total_gross_profit"],
                "total_net_disbursed": b["total_net_disbursed"],
                "gates_verified": b["gates_verified"],
                "settled_at": b["settled_at"],
                "contra_voucher_code": b.get("contra_voucher_code"),
            })

        return Response({"batches": batches})

    @action(detail=False, methods=["get"], url_path="batch-detail")
    def batch_detail(self, request):
        """Fetches complete granular batch details with depositor transactions."""
        from .models import AllocationRun
        from .payout_clearing_engine import PayoutClearingEngine

        run_id = request.query_params.get("allocation_run")
        if not run_id:
            raise ValidationError({"allocation_run": ["Query param is required."]})

        try:
            run = AllocationRun.objects.get(id=run_id)
        except AllocationRun.DoesNotExist:
            raise ValidationError({"allocation_run": ["Allocation run not found."]})

        force_regen = request.query_params.get("force_regenerate") == "true"
        batch_obj = PayoutClearingEngine.get_or_create_batch_for_run(run, request.user.tenant, force_regenerate=force_regen)
        return Response(batch_obj)

    @action(detail=False, methods=["post"], url_path="verify-gates")
    def verify_gates(self, request):
        """Runs the 5 Pre-Disbursement Statutory Gates."""
        from .models import AllocationRun
        from .payout_clearing_engine import PayoutClearingEngine

        run_id = request.data.get("allocation_run")
        if not run_id:
            raise ValidationError({"allocation_run": ["Field is required."]})

        run = AllocationRun.objects.get(id=run_id)
        batch_obj = PayoutClearingEngine.get_or_create_batch_for_run(run, request.user.tenant)
        updated_batch = PayoutClearingEngine.verify_pre_disbursement_gates(batch_obj, request.user.tenant)
        return Response(updated_batch)

    @action(detail=False, methods=["post"], url_path="authorize")
    def authorize(self, request):
        """Checker authorization prior to clearing network transmission."""
        from .models import AllocationRun
        from .payout_clearing_engine import PayoutClearingEngine

        run_id = request.data.get("allocation_run")
        if not run_id:
            raise ValidationError({"allocation_run": ["Field is required."]})

        run = AllocationRun.objects.get(id=run_id)
        batch_obj = PayoutClearingEngine.get_or_create_batch_for_run(run, request.user.tenant)
        try:
            updated_batch = PayoutClearingEngine.authorize_batch(batch_obj, request.user)
            return Response(updated_batch)
        except ValueError as e:
            raise ValidationError(str(e))

    @action(detail=False, methods=["post"], url_path="dispatch-simulate")
    def dispatch_simulate(self, request):
        """Triggers real-time simulated network clearing on SBP Raast / 1LINK."""
        from .models import AllocationRun
        from .payout_clearing_engine import PayoutClearingEngine

        run_id = request.data.get("allocation_run")
        if not run_id:
            raise ValidationError({"allocation_run": ["Field is required."]})

        inject_edge_case = request.data.get("inject_edge_case", False)
        run = AllocationRun.objects.get(id=run_id)
        batch_obj = PayoutClearingEngine.get_or_create_batch_for_run(run, request.user.tenant)

        # Dispatch must follow explicit gate verification and checker authorisation.
        if not batch_obj.get("gates_verified"):
            raise ValidationError("All pre-disbursement gates must be verified before dispatch.")
        if batch_obj.get("status") != "authorized":
            raise ValidationError("Batch must be authorized by a checker before dispatch.")

        updated_batch = PayoutClearingEngine.simulate_dispatch(batch_obj, inject_edge_case=inject_edge_case)
        return Response(updated_batch)

    @action(detail=False, methods=["get"], url_path="download-iso-pacs008")
    def download_iso_pacs008(self, request):
        """Downloads standard ISO 20022 pacs.008 XML message."""
        from django.http import HttpResponse
        from .models import AllocationRun
        from .payout_clearing_engine import PayoutClearingEngine

        run_id = request.query_params.get("allocation_run")
        if not run_id:
            raise ValidationError({"allocation_run": ["Query param is required."]})

        run = AllocationRun.objects.get(id=run_id)
        batch_obj = PayoutClearingEngine.get_or_create_batch_for_run(run, request.user.tenant)
        xml_content = PayoutClearingEngine.generate_iso20022_pacs008_xml(batch_obj)

        response = HttpResponse(xml_content, content_type="application/xml")
        response["Content-Disposition"] = f'attachment; filename="{batch_obj["batch_code"]}_pacs008.xml"'
        return response

    @action(detail=False, methods=["post"], url_path="post-contra-gl")
    def post_contra_gl(self, request):
        """Posts automated Contra-Accounting GL voucher in Finance Ledger."""
        from .models import AllocationRun
        from .payout_clearing_engine import PayoutClearingEngine

        run_id = request.data.get("allocation_run")
        if not run_id:
            raise ValidationError({"allocation_run": ["Field is required."]})

        run = AllocationRun.objects.get(id=run_id)
        batch_obj = PayoutClearingEngine.get_or_create_batch_for_run(run, request.user.tenant)

        if batch_obj.get("status") not in ["settled", "partially_settled"]:
            raise ValidationError("Batch must be settled before posting contra-accounting vouchers.")

        updated_batch = PayoutClearingEngine.post_contra_accounting_voucher(
            batch_obj, request.user.tenant, request.user
        )
        return Response(updated_batch)

