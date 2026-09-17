from django.utils import timezone
from rest_framework import mixins, viewsets
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
from apps.core.audit import log_action

from .models import ExceptionCase, ExceptionStatus, PurificationEntry, PurificationStatus
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
