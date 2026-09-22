from django.db import models

from apps.core.models import TenantScopedModel


class PoolStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_APPROVAL = "pending_approval", "Pending Approval"
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


class AssetType(models.TextChoices):
    MURABAHAH = "murabahah", "Murabahah"
    IJARAH = "ijarah", "Ijarah"
    DIMINISHING_MUSHARAKAH = "diminishing_musharakah", "Diminishing Musharakah"
    OTHER = "other", "Other"


class AssetStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    ASSIGNED = "assigned", "Assigned"
    MATURED = "matured", "Matured"
    WRITTEN_OFF = "written_off", "Written Off"


class Asset(TenantScopedModel):
    reference_code = models.CharField(max_length=50)
    asset_type = models.CharField(max_length=30, choices=AssetType.choices)
    description = models.CharField(max_length=255)
    face_value = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, choices=AssetStatus.choices, default=AssetStatus.AVAILABLE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "reference_code"], name="unique_asset_reference_code_per_tenant"
            ),
        ]

    def __str__(self):
        return self.reference_code


class AssetAssignment(TenantScopedModel):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="assignments")
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="asset_assignments")
    assigned_date = models.DateField()
    unassigned_date = models.DateField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.asset.reference_code} -> {self.pool.name}"


class BalanceSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    FILE_IMPORT = "file_import", "File Import"
    API = "api", "API"


class DailyBalanceStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    VALIDATED = "validated", "Validated"
    REJECTED = "rejected", "Rejected"


class BalanceImportBatchStatus(models.TextChoices):
    PROCESSING = "processing", "Processing"
    BALANCED = "balanced", "Balanced"
    EXCEPTION = "exception", "Exception"


class DailyBalance(TenantScopedModel):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="daily_balances")
    participant_class = models.CharField(max_length=100)
    value_date = models.DateField()
    balance_amount = models.DecimalField(max_digits=18, decimal_places=2)
    source = models.CharField(max_length=20, choices=BalanceSource.choices, default=BalanceSource.MANUAL)
    status = models.CharField(
        max_length=20, choices=DailyBalanceStatus.choices, default=DailyBalanceStatus.PENDING
    )

    def __str__(self):
        return f"{self.pool.name} - {self.participant_class} @ {self.value_date}"


class BalanceImportBatch(TenantScopedModel):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="import_batches")
    value_date = models.DateField()
    total_records = models.IntegerField()
    matched_records = models.IntegerField(default=0)
    exception_count = models.IntegerField(default=0)
    control_total_expected = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    control_total_actual = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=BalanceImportBatchStatus.choices, default=BalanceImportBatchStatus.PROCESSING
    )
    imported_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.pool.name} import @ {self.value_date} ({self.status})"
