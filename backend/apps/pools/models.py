from django.db import models

from apps.core.models import TenantScopedModel


class PoolStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    OPEN = "open", "Open"
    ALLOCATION = "allocation", "Allocation"
    CLOSED = "closed", "Closed"
    ARCHIVED = "archived", "Archived"


class Pool(TenantScopedModel):
    """
    IMPORTANT: once a Pool reaches "open" or later, its configuration
    must never be edited directly - any config change is recorded as a
    new PoolVersion instead. This model only defines the structure;
    actual versioning/change-request logic is a future task.
    """

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    product = models.ForeignKey(
        "products.Product", on_delete=models.PROTECT, related_name="pools"
    )
    status = models.CharField(max_length=20, choices=PoolStatus.choices, default=PoolStatus.DRAFT)
    effective_date = models.DateField()
    closed_date = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="unique_pool_code_per_tenant"),
        ]

    def __str__(self):
        return self.name


class PoolVersion(TenantScopedModel):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="versions")
    version_number = models.IntegerField()
    snapshot = models.JSONField()
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ["-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["pool", "version_number"], name="unique_version_number_per_pool"
            ),
        ]

    def __str__(self):
        return f"{self.pool.name} v{self.version_number}"
