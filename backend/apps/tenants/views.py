from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
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



from datetime import date  # noqa: E402

from .models import EncryptionKeyRecord, FeatureFlag  # noqa: E402
from .serializers import EncryptionKeyRecordSerializer, FeatureFlagSerializer  # noqa: E402


class FeatureFlagViewSet(viewsets.ModelViewSet):
    """The administrator switches features per tenant; tenant staff only ask which are on for them (`effective`)."""

    serializer_class = FeatureFlagSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ("create", "partial_update"):
            return [IsAuthenticated(), IsPlatformSuperAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = FeatureFlag.objects.select_related("tenant")
        user = self.request.user
        return qs if user.role == "platform_super_admin" else qs.filter(tenant_id=user.tenant_id)

    @action(detail=False, methods=["get"])
    def effective(self, request):
        flags = FeatureFlag.objects.filter(tenant_id=request.user.tenant_id, enabled=True, is_active=True)
        return Response({"enabled": sorted(f.key for f in flags)})

    def _audit(self, request, flag, verb):
        log_action(tenant=flag.tenant, actor=request.user, action=verb, model_name="FeatureFlag", object_id=str(flag.id),
                   changes={"key": flag.key, "enabled": flag.enabled}, reason=flag.note or None, request=request)

    def perform_create(self, serializer):
        flag = serializer.save(changed_by=self.request.user)
        self._audit(self.request, flag, "feature_flag_set")

    def perform_update(self, serializer):
        flag = serializer.save(changed_by=self.request.user)
        self._audit(self.request, flag, "feature_flag_set")


class EncryptionKeyRecordViewSet(viewsets.ModelViewSet):
    serializer_class = EncryptionKeyRecordSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        return [IsAuthenticated(), IsPlatformSuperAdmin()]

    def get_queryset(self):
        return EncryptionKeyRecord.objects.select_related("tenant")

    def perform_create(self, serializer):
        key = serializer.save()
        log_action(tenant=key.tenant, actor=self.request.user, action="encryption_key_registered", model_name="EncryptionKeyRecord",
                   object_id=str(key.id), changes={"purpose": key.purpose, "provider": key.provider}, request=self.request)

    @action(detail=True, methods=["post"])
    def rotated(self, request, pk=None):
        """Record that the key was rotated in the KMS/HSM on the given date (default today). The key itself is never handled here."""
        key = self.get_object()
        try:
            on = date.fromisoformat(str(request.data.get("rotated_on") or date.today()))
        except ValueError:
            raise ValidationError({"rotated_on": ["Use the format YYYY-MM-DD."]})
        if on > date.today():
            raise ValidationError({"rotated_on": ["A rotation cannot be dated in the future."]})
        key.last_rotated_on = on
        key.save(update_fields=["last_rotated_on", "updated_at"])
        log_action(tenant=key.tenant, actor=request.user, action="encryption_key_rotation_recorded", model_name="EncryptionKeyRecord",
                   object_id=str(key.id), changes={"purpose": key.purpose, "rotated_on": str(on)}, request=request)
        return Response(self.get_serializer(key).data)
