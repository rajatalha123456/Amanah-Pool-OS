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


class AuditLog(models.Model):
    """
    Append-only audit trail. Deliberately does not inherit BaseModel:
    it has no is_active/soft-delete concept and, unlike ordinary
    records, must never be updated after creation. See apps.core.audit
    for the log_action() helper used to write entries.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.SET_NULL, null=True, blank=True
    )
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=50)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64)
    changes = models.JSONField(null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("AuditLog entries are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditLog entries are immutable and cannot be deleted.")

    def __str__(self):
        return f"{self.action} {self.model_name}:{self.object_id}"
