from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsPlatformSuperAdmin
from apps.core.audit import log_action
from .models import Tenant, LegalEntity
from .serializers import TenantSerializer, LegalEntitySerializer


class TenantViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TenantSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "suspend", "reactivate"):
            return [IsAuthenticated(), IsPlatformSuperAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "platform_super_admin":
            return Tenant.objects.all().order_by("name")
        if user.tenant:
            return Tenant.objects.filter(pk=user.tenant_id, is_active=True, is_suspended=False)
        return Tenant.objects.none()

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(
            tenant=instance,
            actor=self.request.user,
            action="create",
            model_name="Tenant",
            object_id=str(instance.id),
            changes={"code": instance.code, "name": instance.name, "data_residency": instance.data_residency},
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        tenant = self.get_object()
        tenant.is_suspended = True
        tenant.save(update_fields=["is_suspended", "updated_at"])
        log_action(
            tenant=tenant,
            actor=request.user,
            action="suspend_tenant",
            model_name="Tenant",
            object_id=str(tenant.id),
            changes={"is_suspended": {"before": False, "after": True}},
            request=request,
        )
        return Response(TenantSerializer(tenant).data)

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        tenant = self.get_object()
        tenant.is_suspended = False
        tenant.save(update_fields=["is_suspended", "updated_at"])
        log_action(
            tenant=tenant,
            actor=request.user,
            action="reactivate_tenant",
            model_name="Tenant",
            object_id=str(tenant.id),
            changes={"is_suspended": {"before": True, "after": False}},
            request=request,
        )
        return Response(TenantSerializer(tenant).data)


class LegalEntityViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = LegalEntitySerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), IsPlatformSuperAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "platform_super_admin":
            return LegalEntity.objects.all().order_by("name")
        if user.tenant:
            return LegalEntity.objects.filter(tenant=user.tenant, is_active=True)
        return LegalEntity.objects.none()

    def perform_create(self, serializer):
        tenant = self.request.user.tenant
        tenant_id = self.request.data.get("tenant")
        if self.request.user.role == "platform_super_admin" and tenant_id:
            tenant = Tenant.objects.get(pk=tenant_id)
        serializer.save(tenant=tenant)
