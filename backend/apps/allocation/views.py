import logging

from django.core.exceptions import ValidationError as DjangoValidationError
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

from .engine import calculate_allocation, calculate_hash
from .models import (
    AllocationLine,
    AllocationRun,
    AllocationRunStatus,
    DepositorStatement,
    PSRStatus,
    ProfitSharingRatio,
    WeightageBand,
    WeightageBandStatus,
)
from .serializers import (
    AllocationRunInputSerializer,
    AllocationRunSerializer,
    DepositorStatementSerializer,
    PSRSerializer,
    WeightageBandSerializer,
)
from .statements import generate_statement_narrative

logger = logging.getLogger("apps")


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
            return [IsAuthenticated(), IsShariahSecretariat()]
        if self.action in ("approve", "reject"):
            return [IsAuthenticated(), IsFinanceChecker()]
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
                "lines": result["lines"],
            }
        )

    def create(self, request, *args, **kwargs):
        """
        Runs the allocation calculation and persists it as an
        AllocationRun + AllocationLine rows, status="simulated".
        """
        data, result = self._run_calculation(request)

        hashable_data = {
            "pool_id": str(data["pool"].id),
            "value_date": data["value_date"].isoformat(),
            "gross_income": str(data["gross_income"]),
            "direct_expenses": str(data["direct_expenses"]),
            "distributable": str(result["distributable"]),
            "total_weighted_funds": str(result["total_weighted_funds"]),
            "depositor_pool_share": str(result["depositor_pool_share"]),
            "mudarib_share": str(result["mudarib_share"]),
            "lines": [
                {k: str(v) for k, v in line.items()} for line in result["lines"]
            ],
        }
        calculation_hash = calculate_hash(hashable_data)

        run = AllocationRun.objects.create(
            tenant=request.user.tenant,
            pool=data["pool"],
            value_date=data["value_date"],
            gross_income=data["gross_income"],
            direct_expenses=data["direct_expenses"],
            distributable_amount=result["distributable"],
            total_weighted_funds=result["total_weighted_funds"],
            depositor_pool_share=result["depositor_pool_share"],
            mudarib_share=result["mudarib_share"],
            status=AllocationRunStatus.SIMULATED,
            calculation_hash=calculation_hash,
            created_by=request.user,
        )

        AllocationLine.objects.bulk_create(
            [
                AllocationLine(
                    tenant=request.user.tenant,
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
                "line_count": len(result["lines"]),
                "calculation_hash": calculation_hash,
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
        run.status = AllocationRunStatus.SIGNED
        run.checked_by = request.user
        run.checked_at = timezone.now()
        run.save(update_fields=["status", "checked_by", "checked_at", "updated_at"])

        journal_batch = create_journal_from_allocation(run, posted_by=request.user)

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
