from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsPoolManager, IsShariahBoard
from apps.core.audit import log_action

from .models import PSRStatus, ProfitSharingRatio, WeightageBand, WeightageBandStatus
from .serializers import PSRSerializer, WeightageBandSerializer


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
