import uuid

from django.db import models

from .context import get_current_tenant


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class TenantScopedManager(models.Manager):
    """
    Automatically filters querysets to the current tenant (from the
    request-scoped contextvar). If no tenant context is set, returns an
    empty queryset rather than leaking cross-tenant data.
    """

    def get_queryset(self):
        tenant = get_current_tenant()
        queryset = super().get_queryset()

        if tenant is None:
            return queryset.none()

        return queryset.filter(tenant=tenant)


class TenantScopedModel(BaseModel):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)

    objects = TenantScopedManager()

    class Meta:
        abstract = True


class TenantIsolationTestRecord(TenantScopedModel):
    """
    Minimal concrete TenantScopedModel used only to verify that
    TenantScopedManager correctly scopes queries to the current tenant.
    See: apps/tenants/management/commands/test_tenant_isolation.py
    """

    label = models.CharField(max_length=100)

    def __str__(self):
        return self.label
