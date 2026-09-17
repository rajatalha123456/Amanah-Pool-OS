from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import (
    HasAnyRole,
    IsFinanceChecker,
    IsRiskCompliance,
    IsShariahBoard,
)
from apps.allocation.models import ProfitSharingRatio, WeightageBand
from apps.core.audit import log_action
from apps.pools.models import Pool, PoolStatus
from apps.products.models import ContractTemplate, ContractTemplateStatus, ShariahDecision, ShariahDecisionStatus

from .models import ExceptionCase, ExceptionSeverity, ExceptionStatus, PurificationEntry, PurificationStatus
from .serializers import ExceptionCaseSerializer, PurificationEntrySerializer


class ExceptionCaseViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ExceptionCaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # See apps/products/views.py etc. for why this must be a method
        # rather than a class-level `queryset = Model.objects.all()`
        # attribute (TenantScopedManager + import-time evaluation bug).
        queryset = ExceptionCase.objects.all()
        pool_id = self.request.query_params.get("pool")
        status_param = self.request.query_params.get("status")
        severity = self.request.query_params.get("severity")

        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        if status_param:
            queryset = queryset.filter(status=status_param)
        if severity:
            queryset = queryset.filter(severity=severity)

        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), HasAnyRole(["risk_compliance", "pool_manager"])()]
        if self.action in ("update", "partial_update", "resolve", "dismiss"):
            return [IsAuthenticated(), IsRiskCompliance()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="ExceptionCase",
            object_id=str(instance.id),
            changes={"status": instance.status, "severity": instance.severity, "title": instance.title},
            request=self.request,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="update",
            model_name="ExceptionCase",
            object_id=str(instance.id),
            changes={"assigned_to": instance.assigned_to_id},
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        case = self.get_object()

        resolution_notes = request.data.get("resolution_notes")
        if not resolution_notes:
            raise ValidationError({"resolution_notes": ["This field is required."]})

        previous_status = case.status
        case.status = ExceptionStatus.RESOLVED
        case.resolution_notes = resolution_notes
        case.resolved_by = request.user
        case.resolved_at = timezone.now()
        case.save(update_fields=["status", "resolution_notes", "resolved_by", "resolved_at", "updated_at"])

        log_action(
            tenant=case.tenant,
            actor=request.user,
            action="resolve",
            model_name="ExceptionCase",
            object_id=str(case.id),
            changes={"status": {"before": previous_status, "after": case.status}},
            reason=resolution_notes,
            request=request,
        )
        return Response(self.get_serializer(case).data)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        case = self.get_object()

        resolution_notes = request.data.get("resolution_notes")
        if not resolution_notes:
            raise ValidationError({"resolution_notes": ["This field is required."]})

        previous_status = case.status
        case.status = ExceptionStatus.DISMISSED
        case.resolution_notes = resolution_notes
        case.resolved_by = request.user
        case.resolved_at = timezone.now()
        case.save(update_fields=["status", "resolution_notes", "resolved_by", "resolved_at", "updated_at"])

        log_action(
            tenant=case.tenant,
            actor=request.user,
            action="dismiss",
            model_name="ExceptionCase",
            object_id=str(case.id),
            changes={"status": {"before": previous_status, "after": case.status}},
            reason=resolution_notes,
            request=request,
        )
        return Response(self.get_serializer(case).data)


class PurificationEntryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PurificationEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # See apps/products/views.py etc. for why this must be a method
        # rather than a class-level `queryset = Model.objects.all()`
        # attribute (TenantScopedManager + import-time evaluation bug).
        queryset = PurificationEntry.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), HasAnyRole(["finance_maker", "risk_compliance"])()]
        if self.action == "approve":
            return [IsAuthenticated(), IsShariahBoard()]
        if self.action == "mark_distributed":
            return [IsAuthenticated(), IsFinanceChecker()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant, status=PurificationStatus.IDENTIFIED)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="PurificationEntry",
            object_id=str(instance.id),
            changes={"status": instance.status, "amount": str(instance.amount)},
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        entry = self.get_object()

        if entry.status != PurificationStatus.IDENTIFIED:
            raise ValidationError(
                f"PurificationEntry must be in '{PurificationStatus.IDENTIFIED}' status to "
                f"approve (current status: '{entry.status}')."
            )

        previous_status = entry.status
        entry.status = PurificationStatus.APPROVED_FOR_PURIFICATION
        entry.approved_by = request.user
        entry.save(update_fields=["status", "approved_by", "updated_at"])

        log_action(
            tenant=entry.tenant,
            actor=request.user,
            action="approve",
            model_name="PurificationEntry",
            object_id=str(entry.id),
            changes={"status": {"before": previous_status, "after": entry.status}},
            request=request,
        )
        return Response(self.get_serializer(entry).data)

    @action(detail=True, methods=["post"], url_path="mark-distributed")
    def mark_distributed(self, request, pk=None):
        entry = self.get_object()

        if entry.status != PurificationStatus.APPROVED_FOR_PURIFICATION:
            raise ValidationError(
                f"PurificationEntry must be in '{PurificationStatus.APPROVED_FOR_PURIFICATION}' "
                f"status to mark distributed (current status: '{entry.status}')."
            )

        charity_recipient = request.data.get("charity_recipient")
        distributed_date = request.data.get("distributed_date")
        errors = {}
        if not charity_recipient:
            errors["charity_recipient"] = ["This field is required."]
        if not distributed_date:
            errors["distributed_date"] = ["This field is required."]
        if errors:
            raise ValidationError(errors)

        previous_status = entry.status
        entry.status = PurificationStatus.DISTRIBUTED
        entry.charity_recipient = charity_recipient
        entry.distributed_date = distributed_date
        entry.save(update_fields=["status", "charity_recipient", "distributed_date", "updated_at"])

        log_action(
            tenant=entry.tenant,
            actor=request.user,
            action="mark_distributed",
            model_name="PurificationEntry",
            object_id=str(entry.id),
            changes={
                "status": {"before": previous_status, "after": entry.status},
                "charity_recipient": charity_recipient,
                "distributed_date": str(distributed_date),
            },
            request=request,
        )
        return Response(self.get_serializer(entry).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasAnyRole(["shariah_board", "shariah_secretariat"])])
def shariah_dashboard(request):
    """
    Aggregates everything currently awaiting Shariah Board / Secretariat
    attention across the whole system into one dashboard payload. Deliberately
    a plain function-based view rather than a ModelViewSet - this endpoint
    doesn't map to a single model, it's a read-only rollup across several.

    Each list is built with a single .values(...) query (no serializers,
    no per-row related-object access) to avoid N+1s - see the per-list
    comments below for what would otherwise trigger one.
    """

    pool_id = request.query_params.get("pool")

    # ShariahDecision is tenant-wide, not pool-scoped, so it's
    # deliberately NOT filtered by ?pool= even when supplied.
    pending_shariah_decisions = list(
        ShariahDecision.objects.filter(status=ShariahDecisionStatus.DRAFT).values(
            "id", "decision_code", "title", "status", "effective_date"
        )
    )

    # ContractTemplate has no direct pool FK either (it's a level above
    # Pool, via Product) - also tenant-wide.
    pending_contract_templates = list(
        ContractTemplate.objects.filter(status=ContractTemplateStatus.DRAFT).values(
            "id", "name", "contract_type", "status"
        )
    )

    weightage_qs = WeightageBand.objects.filter(status="draft")
    if pool_id:
        weightage_qs = weightage_qs.filter(pool_id=pool_id)
    pending_weightage_bands = list(
        weightage_qs.values(
            "id", "pool__code", "participant_class", "weightage", "status"
        ).order_by("pool__code")
    )
    for row in pending_weightage_bands:
        row["pool_code"] = row.pop("pool__code")

    psr_qs = ProfitSharingRatio.objects.filter(status="draft")
    if pool_id:
        psr_qs = psr_qs.filter(pool_id=pool_id)
    pending_psr_schedules = list(
        psr_qs.values(
            "id", "pool__code", "depositor_share", "mudarib_share", "status"
        ).order_by("pool__code")
    )
    for row in pending_psr_schedules:
        row["pool_code"] = row.pop("pool__code")

    exception_qs = ExceptionCase.objects.filter(
        status__in=[ExceptionStatus.OPEN, ExceptionStatus.INVESTIGATING]
    )
    if pool_id:
        exception_qs = exception_qs.filter(pool_id=pool_id)
    open_exception_cases = list(
        exception_qs.values(
            "id", "title", "severity", "status", "pool__code"
        ).order_by("-created_at")
    )
    for row in open_exception_cases:
        row["pool_code"] = row.pop("pool__code")

    critical_exceptions = sum(
        1
        for row in open_exception_cases
        if row["severity"] in (ExceptionSeverity.HIGH, ExceptionSeverity.CRITICAL)
    )

    purification_qs = PurificationEntry.objects.filter(status=PurificationStatus.IDENTIFIED)
    if pool_id:
        purification_qs = purification_qs.filter(pool_id=pool_id)
    pending_purification_entries = list(
        purification_qs.values(
            "id", "source_description", "amount", "status", "pool__code"
        ).order_by("-identified_date")
    )
    for row in pending_purification_entries:
        row["pool_code"] = row.pop("pool__code")

    pool_approvals_qs = Pool.objects.filter(status=PoolStatus.APPROVED)
    if pool_id:
        pool_approvals_qs = pool_approvals_qs.filter(id=pool_id)
    pending_pool_approvals = list(
        pool_approvals_qs.values("id", "name", "code", "status")
    )

    total_pending_items = (
        len(pending_shariah_decisions)
        + len(pending_contract_templates)
        + len(pending_weightage_bands)
        + len(pending_psr_schedules)
        + len(open_exception_cases)
        + len(pending_purification_entries)
        + len(pending_pool_approvals)
    )

    return Response(
        {
            "pending_shariah_decisions": pending_shariah_decisions,
            "pending_contract_templates": pending_contract_templates,
            "pending_weightage_bands": pending_weightage_bands,
            "pending_psr_schedules": pending_psr_schedules,
            "open_exception_cases": open_exception_cases,
            "pending_purification_entries": pending_purification_entries,
            "pending_pool_approvals": pending_pool_approvals,
            "summary_counts": {
                "total_pending_items": total_pending_items,
                "critical_exceptions": critical_exceptions,
            },
        }
    )
