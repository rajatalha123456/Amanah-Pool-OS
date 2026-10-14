import re

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TenantScopedModel


class JournalBatchStatus(models.TextChoices):
    POSTED = "posted", "Posted"


class JournalEntryType(models.TextChoices):
    DEBIT = "debit", "Debit"
    CREDIT = "credit", "Credit"


class JournalBatch(TenantScopedModel):
    """
    A balanced double-entry posting derived from one AllocationRun.
    Only ever created via apps.accounting.services.create_journal_from_allocation() -
    total_debit and total_credit must be equal before this can be saved
    (see clean()/save()).
    """

    # PROTECT: a posted journal is never physically deleted (BRD Section 11);
    # corrections are made by posting a reversing batch.
    allocation_run = models.OneToOneField(
        "allocation.AllocationRun", on_delete=models.PROTECT, related_name="journal_batch", null=True, blank=True
    )
    investment_run = models.OneToOneField(
        "investments.InvestmentDistributionRun",
        on_delete=models.PROTECT,
        related_name="journal_batch",
        null=True,
        blank=True,
    )
    # Set on a reversal batch: the posted batch it contra-posts.
    reverses_batch = models.OneToOneField(
        "self", on_delete=models.PROTECT, related_name="reversed_by", null=True, blank=True
    )
    pool = models.ForeignKey("pools.Pool", on_delete=models.CASCADE, related_name="journal_batches")
    batch_date = models.DateField()
    total_debit = models.DecimalField(max_digits=18, decimal_places=2)
    total_credit = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=JournalBatchStatus.choices, default=JournalBatchStatus.POSTED
    )
    posted_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )

    def clean(self):
        if self.total_debit is not None and self.total_credit is not None:
            if self.total_debit != self.total_credit:
                raise ValidationError("Journal batch is not balanced.")

    def save(self, *args, **kwargs):
        self.clean()
        if not self._state.adding:
            raise ValidationError("Posted journal batches are immutable; post a reversal instead.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Posted journal batches cannot be deleted; post a reversal instead.")

    def __str__(self):
        return f"JournalBatch for {self.pool.name} @ {self.batch_date}"


class JournalEntry(TenantScopedModel):
    batch = models.ForeignKey(JournalBatch, on_delete=models.PROTECT, related_name="entries")
    account_name = models.CharField(max_length=255)
    # Logical account (apps.accounting.chart) and the GL code it was mapped to when posted.
    account_key = models.CharField(max_length=40, blank=True, default="")
    gl_code = models.CharField(max_length=40, blank=True, default="")
    entry_type = models.CharField(max_length=10, choices=JournalEntryType.choices)
    amount = models.DecimalField(max_digits=18, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Posted journal entries are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Posted journal entries cannot be deleted.")

    def __str__(self):
        return f"{self.entry_type} {self.account_name} = {self.amount}"


class IncomeExpenseEventType(models.TextChoices):
    INCOME = "income", "Income"
    EXPENSE = "expense", "Expense"


class IncomeExpenseEventStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    POSTED = "posted", "Posted"


class CostClassification(models.TextChoices):
    DIRECT_PERMISSIBLE = "direct_permissible", "Direct Operating Expense (Permissible)"
    INDIRECT_OVERHEAD = "indirect_overhead", "Indirect Overhead (Bank Absorbed)"
    PERMISSIBLE_INCOME = "permissible_income", "Permissible Pool Income"
    NON_PERMISSIBLE_INCOME = "non_permissible_income", "Non-Permissible Income (Charity Quarantine)"


class IncomeExpenseEvent(TenantScopedModel):
    """
    BRD Screen 03: Income & Expense Workbench with Direct Cost Segregation.
    Enforces SBP IBD Circular 03/2012: Direct expenses can be charged to the pool;
    indirect/overhead expenses must be absorbed 100% by the Mudarib bank.
    """

    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="income_expense_events"
    )
    event_type = models.CharField(max_length=10, choices=IncomeExpenseEventType.choices)
    cost_classification = models.CharField(
        max_length=50,
        choices=CostClassification.choices,
        default=CostClassification.DIRECT_PERMISSIBLE,
    )
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    pool_chargeable_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    bank_absorbed_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    is_direct_expense = models.BooleanField(default=True)
    is_overhead_leakage = models.BooleanField(default=False)
    quarantined_to_charity = models.BooleanField(default=False)
    event_date = models.DateField()
    description = models.TextField()
    shariah_note = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=IncomeExpenseEventStatus.choices, default=IncomeExpenseEventStatus.PENDING
    )
    # The signed allocation run that consumed this event (BR-005). A consumed event
    # can never feed another run; it is released only when that run is reversed by a
    # restatement, which re-links it to the replacement run.
    allocation_run = models.ForeignKey(
        "allocation.AllocationRun",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="income_expense_events",
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    posted_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    # Once posted, an event is a ledger fact: only the link to the run that consumes it may change.
    _POSTED_MUTABLE_FIELDS = frozenset({"allocation_run", "updated_at"})

    def save(self, *args, **kwargs):
        from decimal import Decimal

        if not self._state.adding:
            prior = IncomeExpenseEvent._base_manager.filter(pk=self.pk).values_list("status", flat=True).first()
            if prior == IncomeExpenseEventStatus.POSTED:
                update_fields = kwargs.get("update_fields")
                if update_fields is None or not set(update_fields) <= self._POSTED_MUTABLE_FIELDS:
                    raise ValidationError("A posted income/expense event is immutable.")

        if self.amount is None:
            self.amount = Decimal("0.00")

        overhead_keywords = [
            "salary", "wage", "rent", "premise", "utility", "electric",
            "software", "license", "it overhead", "marketing", "bonus",
            "depreciation", "branch", "head office"
        ]
        desc_lower = (self.description or "").lower()
        cat_lower = (self.category or "").lower()

        # Whole-word matching: "rent" must not match "current"/"parent".
        overhead_pattern = re.compile(r"\b(?:" + "|".join(re.escape(kw) for kw in overhead_keywords) + r")s?\b")
        is_suspicious_overhead = bool(
            overhead_pattern.search(desc_lower) or overhead_pattern.search(cat_lower)
        )

        if self.event_type == IncomeExpenseEventType.EXPENSE:
            if self.cost_classification == CostClassification.INDIRECT_OVERHEAD or is_suspicious_overhead:
                self.cost_classification = CostClassification.INDIRECT_OVERHEAD
                self.is_direct_expense = False
                self.is_overhead_leakage = True
                self.pool_chargeable_amount = Decimal("0.00")
                self.bank_absorbed_amount = self.amount
                if not self.shariah_note:
                    self.shariah_note = "SBP IBD 03/2012 Violation: Indirect overhead cannot be charged to depositor pool. Absorbed 100% by Bank P&L."
            else:
                self.cost_classification = CostClassification.DIRECT_PERMISSIBLE
                self.is_direct_expense = True
                self.is_overhead_leakage = False
                self.pool_chargeable_amount = self.amount
                self.bank_absorbed_amount = Decimal("0.00")
        elif self.event_type == IncomeExpenseEventType.INCOME:
            if (
                self.cost_classification == CostClassification.NON_PERMISSIBLE_INCOME
                or re.search(r"\bpenalt(?:y|ies)\b", cat_lower)
                or re.search(r"\binterest\b", desc_lower)
            ):
                self.cost_classification = CostClassification.NON_PERMISSIBLE_INCOME
                self.quarantined_to_charity = True
                self.pool_chargeable_amount = Decimal("0.00")
                self.bank_absorbed_amount = Decimal("0.00")
                if not self.shariah_note:
                    self.shariah_note = "Non-Permissible Income quarantined for Charity purification."
            else:
                self.cost_classification = CostClassification.PERMISSIBLE_INCOME
                self.quarantined_to_charity = False
                self.pool_chargeable_amount = self.amount
                self.bank_absorbed_amount = Decimal("0.00")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event_type} {self.category} {self.amount} - {self.pool.name} ({self.status})"


class ReconciliationStatus(models.TextChoices):
    MATCHED = "matched", "Matched"
    VARIANCE_FLAGGED = "variance_flagged", "Variance Flagged"
    CLEARED = "cleared", "Cleared"


class ReconciliationBatch(TenantScopedModel):
    """
    Screen 11: Reconciliation Center - Core, bank, subledger and GL matching.
    """

    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="reconciliation_batches"
    )
    reconciliation_date = models.DateField()
    source_system = models.CharField(max_length=100, default="Core Banking CBS / GL")
    total_records = models.IntegerField(default=0)
    matched_records = models.IntegerField(default=0)
    exception_count = models.IntegerField(default=0)
    variance_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=ReconciliationStatus.choices, default=ReconciliationStatus.MATCHED
    )
    control_total_status = models.CharField(max_length=20, default="BalancedPASS")
    performed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-reconciliation_date", "-created_at"]

    def __str__(self):
        return f"Reconciliation for {self.pool.name} @ {self.reconciliation_date} ({self.status})"


class ReconciliationItem(TenantScopedModel):
    batch = models.ForeignKey(
        ReconciliationBatch, on_delete=models.CASCADE, related_name="items"
    )
    account_reference = models.CharField(max_length=100)
    cbs_amount = models.DecimalField(max_digits=18, decimal_places=2)
    gl_amount = models.DecimalField(max_digits=18, decimal_places=2)
    variance = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, default="matched")
    resolution_notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.account_reference}: CBS={self.cbs_amount}, GL={self.gl_amount}"


class AccountMapping(TenantScopedModel):
    """
    Maps a logical pool account (apps.accounting.chart) to the enterprise GL account (BRD Section 10:
    "Pool subledger entries reconcile to the enterprise GL"). `pool` null = tenant default; a pool
    row overrides it. Journals are named from this mapping at posting time.
    """

    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, null=True, blank=True, related_name="account_mappings"
    )
    account_key = models.CharField(max_length=40)
    gl_code = models.CharField(max_length=40)
    gl_name = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "account_key"], condition=models.Q(pool__isnull=True),
                name="unique_account_mapping_tenant_default",
            ),
            models.UniqueConstraint(
                fields=["tenant", "pool", "account_key"], condition=models.Q(pool__isnull=False),
                name="unique_account_mapping_per_pool",
            ),
        ]
        ordering = ["account_key"]

    def __str__(self):
        scope = self.pool.code if self.pool_id else "tenant default"
        return f"{self.account_key} -> {self.gl_code} {self.gl_name} ({scope})"


class GLExportStatus(models.TextChoices):
    GENERATED = "generated", "Generated (awaiting the GL's answer)"
    CONFIRMED = "confirmed", "Confirmed posted in the enterprise GL"
    REJECTED = "rejected", "Rejected by the GL (batches free to export again)"


class GLExport(TenantScopedModel):
    """
    One hand-over of journal batches to the enterprise general ledger (BRD 10 / 12: "journal batches, posting status").
    The file is stored with its hash, so what was sent can be downloaded again and proved. A batch belongs to at most one
    export that is generated or confirmed: it cannot be sent twice unless the GL rejected the export it was in.
    """

    pool = models.ForeignKey("pools.Pool", on_delete=models.PROTECT, related_name="gl_exports")
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    batches = models.ManyToManyField(JournalBatch, related_name="gl_exports")
    row_count = models.PositiveIntegerField()
    total_debit = models.DecimalField(max_digits=18, decimal_places=2)
    total_credit = models.DecimalField(max_digits=18, decimal_places=2)
    content = models.TextField()
    content_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=10, choices=GLExportStatus.choices, default=GLExportStatus.GENERATED)
    exported_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")
    gl_reference = models.CharField(max_length=100, blank=True, default="")
    decided_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True, default="")

    _DECISION_FIELDS = frozenset({"status", "gl_reference", "decided_by", "decided_at", "decision_note", "updated_at"})

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # The file and its figures never change once generated; only the GL's answer is recorded afterwards.
        if not self._state.adding:
            fields = kwargs.get("update_fields")
            if fields is None or not set(fields) <= self._DECISION_FIELDS:
                raise ValidationError("A GL export file is immutable; only the GL's answer can be recorded.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("A GL export is a record of what was sent and cannot be deleted.")


class SuspenseSide(models.TextChoices):
    UNIDENTIFIED_RECEIPT = "unidentified_receipt", "Unidentified receipt (money in, owner not known)"
    UNEXPLAINED_SHORTFALL = "unexplained_shortfall", "Unexplained shortfall (money missing, reason not known)"


class SuspenseStatus(models.TextChoices):
    PROPOSED = "proposed", "Proposed (awaiting a checker)"
    OPEN = "open", "Open in suspense"
    CLEARING_PROPOSED = "clearing_proposed", "Clearing proposed"
    CLEARED = "cleared", "Cleared"
    REJECTED = "rejected", "Rejected"


class SuspenseItem(TenantScopedModel):
    """One amount held in the pool's suspense account, with who, why and where it finally went (accounting/suspense.py)."""

    pool = models.ForeignKey("pools.Pool", on_delete=models.PROTECT, related_name="suspense_items")
    side = models.CharField(max_length=24, choices=SuspenseSide.choices)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    counter_account_key = models.CharField(max_length=40, default="pool_cash")
    description = models.TextField()
    reference = models.CharField(max_length=100, blank=True, default="")
    opened_on = models.DateField()
    reconciliation_batch = models.ForeignKey(
        ReconciliationBatch, on_delete=models.PROTECT, null=True, blank=True, related_name="suspense_items"
    )
    status = models.CharField(max_length=20, choices=SuspenseStatus.choices, default=SuspenseStatus.PROPOSED)
    proposed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")
    opened_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    opened_at = models.DateTimeField(null=True, blank=True)
    opening_journal = models.ForeignKey(JournalBatch, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    clear_account_key = models.CharField(max_length=40, blank=True, default="")
    clear_reason = models.TextField(blank=True, default="")
    clear_proposed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    cleared_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    cleared_on = models.DateField(null=True, blank=True)
    clearing_journal = models.ForeignKey(JournalBatch, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    decision_note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["opened_on", "created_at"]
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name="suspense_amount_positive")]

    def delete(self, *args, **kwargs):
        raise ValidationError("A suspense item is part of the ledger trail and cannot be deleted; reject or clear it.")
