from django.db import models

from apps.core.models import TenantScopedModel


class ExceptionSourceModule(models.TextChoices):
    ACCOUNTING = "accounting", "Accounting"
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
    investigation_notes = models.TextField(null=True, blank=True)
    treatment_plan = models.TextField(null=True, blank=True)
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


class PurificationStatus(models.TextChoices):
    IDENTIFIED = "identified", "Identified"
    APPROVED_FOR_PURIFICATION = "approved_for_purification", "Approved for Purification"
    DISTRIBUTED = "distributed", "Distributed"


class PurificationEntry(TenantScopedModel):
    """
    Tracks non-Shariah-compliant income (e.g. incidental conventional
    interest on idle cash) that must be purified - donated to charity
    rather than retained or distributed to depositors/mudarib. Lifecycle:
    identified -> approved_for_purification (Shariah Board ruling) ->
    distributed (Finance Checker confirms the charity payment was made).
    """

    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="purification_entries"
    )
    source_description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    identified_date = models.DateField()
    status = models.CharField(
        max_length=30, choices=PurificationStatus.choices, default=PurificationStatus.IDENTIFIED
    )
    shariah_decision = models.ForeignKey(
        "products.ShariahDecision",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purification_entries",
    )
    # The quarantined income event this purification was raised for (one entry per event).
    income_event = models.OneToOneField(
        "accounting.IncomeExpenseEvent",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purification_entry",
    )
    charity_recipient = models.CharField(max_length=255, null=True, blank=True)
    distributed_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_purification_entries",
    )
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Purification {self.amount} - {self.source_description}"


class RelatedPartyRelationshipType(models.TextChoices):
    DIRECTOR = "director", "Director"
    SHAREHOLDER = "shareholder", "Shareholder"
    FAMILY_MEMBER = "family_member", "Family Member"
    AFFILIATE_COMPANY = "affiliate_company", "Affiliate Company"
    OTHER = "other", "Other"


class RelatedPartyDisclosureStatus(models.TextChoices):
    DISCLOSED = "disclosed", "Disclosed"
    PENDING_REVIEW = "pending_review", "Pending Review"
    APPROVED = "approved", "Approved"
    FLAGGED = "flagged", "Flagged"


class RelatedPartyTransaction(TenantScopedModel):
    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="related_party_transactions"
    )
    related_party_name = models.CharField(max_length=255)
    relationship_type = models.CharField(max_length=30, choices=RelatedPartyRelationshipType.choices)
    transaction_type = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    transaction_date = models.DateField()
    disclosure_status = models.CharField(
        max_length=20,
        choices=RelatedPartyDisclosureStatus.choices,
        default=RelatedPartyDisclosureStatus.PENDING_REVIEW,
    )
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_related_party_transactions",
    )
    review_notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.related_party_name} - {self.amount}"


class SupportRequestType(models.TextChoices):
    STATEMENT_CORRECTION = "statement_correction", "Statement Correction"
    PAYOUT_INQUIRY = "payout_inquiry", "Payout Inquiry"
    KYC_ISSUE = "kyc_issue", "KYC Issue"
    GENERAL_COMPLAINT = "general_complaint", "General Complaint"
    OTHER = "other", "Other"


class SupportRequestStatus(models.TextChoices):
    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In Progress"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"


class SupportRequestPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class SupportRequest(TenantScopedModel):
    """
    A dispute or service request raised on behalf of an investor/member
    (statement corrections, payout inquiries, KYC issues, complaints).
    raised_by_name is a plain name for now, not linked to a User -
    linking to an investor_member User is future scope, same as
    CapitalAccount.investor_name.
    """

    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="support_requests", null=True, blank=True
    )
    request_type = models.CharField(max_length=30, choices=SupportRequestType.choices)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    raised_by_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=SupportRequestStatus.choices, default=SupportRequestStatus.OPEN
    )
    priority = models.CharField(
        max_length=10, choices=SupportRequestPriority.choices, default=SupportRequestPriority.MEDIUM
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_support_requests",
    )
    resolution_notes = models.TextField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_support_requests",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.request_type}] {self.subject}"


class AuditPlanStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"


class ShariahAuditPlan(TenantScopedModel):
    """
    Screen 33: Shariah Audit Plan - Risk-based universe, samples and findings.
    """

    plan_year = models.IntegerField()
    title = models.CharField(max_length=255)
    scope = models.CharField(max_length=255, default="All Islamic Pools & Products")
    frequency = models.CharField(max_length=50, default="Quarterly")
    status = models.CharField(
        max_length=20, choices=AuditPlanStatus.choices, default=AuditPlanStatus.DRAFT
    )
    target_samples_count = models.IntegerField(default=50)
    tested_samples_count = models.IntegerField(default=0)
    findings_count = models.IntegerField(default=0)
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_shariah_audit_plans",
    )
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-plan_year", "-created_at"]

    def __str__(self):
        return f"{self.plan_year} - {self.title} ({self.status})"


class ShariahAuditFinding(TenantScopedModel):
    audit_plan = models.ForeignKey(
        ShariahAuditPlan, on_delete=models.CASCADE, related_name="findings"
    )
    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.SET_NULL, null=True, blank=True
    )
    title = models.CharField(max_length=255)
    severity = models.CharField(
        max_length=10, choices=ExceptionSeverity.choices, default=ExceptionSeverity.MEDIUM
    )
    status = models.CharField(max_length=20, default="open")
    observation = models.TextField()
    management_response = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"[{self.severity}] {self.title}"



class ConfigChangeKind(models.TextChoices):
    APPROVAL_MATRIX = "approval_matrix", "Approval matrix rule"
    ACCOUNT_MAPPING = "account_mapping", "Account mapping"


class ConfigChangeOperation(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"


class ConfigChangeStatus(models.TextChoices):
    PENDING = "pending", "Pending approval"
    APPROVED = "approved", "Approved and applied"
    REJECTED = "rejected", "Rejected"


class ConfigChangeRequest(TenantScopedModel):
    """A proposed change to governance configuration; applied only when an independent approver accepts it."""

    kind = models.CharField(max_length=20, choices=ConfigChangeKind.choices)
    operation = models.CharField(max_length=10, choices=ConfigChangeOperation.choices)
    target_id = models.CharField(max_length=64, blank=True, default="")
    payload = models.JSONField(default=dict)
    before = models.JSONField(default=dict)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=ConfigChangeStatus.choices, default=ConfigChangeStatus.PENDING)
    requested_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")
    decided_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True, default="")
    applied_id = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]


class RetentionCategory(models.TextChoices):
    NOTIFICATIONS = "notifications", "In-app notifications (read)"
    SUPPORT_REQUESTS = "support_requests", "Resolved support requests"
    AI_RECOMMENDATIONS = "ai_recommendations", "AI recommendation records"


class RetentionPolicyStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    SUPERSEDED = "superseded", "Superseded"


class RetentionPolicy(TenantScopedModel):
    """
    How long a class of operational data is kept (BRD privacy: retention). Proposed by one person, approved by
    another. Ledgers, statements, contracts, the audit log and Shariah records are *not* covered: they follow the
    legal retention period and are never purged by the retention routine.
    """

    data_category = models.CharField(max_length=30, choices=RetentionCategory.choices)
    retention_days = models.IntegerField()
    basis = models.TextField()  # the legal / policy basis for the period
    status = models.CharField(max_length=12, choices=RetentionPolicyStatus.choices, default=RetentionPolicyStatus.DRAFT)
    proposed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")
    approved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["data_category", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "data_category"], condition=models.Q(status="approved"),
                name="one_approved_retention_policy_per_category",
            ),
        ]
