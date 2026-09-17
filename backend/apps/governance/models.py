from django.db import models

from apps.core.models import TenantScopedModel


class ExceptionSourceModule(models.TextChoices):
    ALLOCATION = "allocation", "Allocation"
    BALANCE_IMPORT = "balance_import", "Balance Import"
    POOL_LIFECYCLE = "pool_lifecycle", "Pool Lifecycle"
    ASSET_ASSIGNMENT = "asset_assignment", "Asset Assignment"
    OTHER = "other", "Other"


class ExceptionSeverity(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class ExceptionStatus(models.TextChoices):
    OPEN = "open", "Open"
    INVESTIGATING = "investigating", "Investigating"
    RESOLVED = "resolved", "Resolved"
    DISMISSED = "dismissed", "Dismissed"


class ExceptionDetectedBy(models.TextChoices):
    SYSTEM = "system", "System"
    AI_AGENT = "ai_agent", "AI Agent"
    MANUAL = "manual", "Manual"


class ExceptionCase(TenantScopedModel):
    """
    A generic anomaly/exception record raised by any module (balance
    import mismatches, allocation variances, pool lifecycle issues,
    etc.) for the Risk & Compliance team to triage. Other modules
    should create these via apps.core.exceptions_helper.create_exception_case()
    rather than instantiating this model directly.
    """

    source_module = models.CharField(max_length=30, choices=ExceptionSourceModule.choices)
    source_object_id = models.CharField(max_length=64, null=True, blank=True)
    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="exception_cases", null=True, blank=True
    )
    severity = models.CharField(max_length=10, choices=ExceptionSeverity.choices)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=20, choices=ExceptionStatus.choices, default=ExceptionStatus.OPEN
    )
    detected_by = models.CharField(
        max_length=10, choices=ExceptionDetectedBy.choices, default=ExceptionDetectedBy.SYSTEM
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_exception_cases",
    )
    resolution_notes = models.TextField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_exception_cases",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.severity}] {self.title}"
