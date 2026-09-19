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

    allocation_run = models.OneToOneField(
        "allocation.AllocationRun", on_delete=models.CASCADE, related_name="journal_batch"
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
        super().save(*args, **kwargs)

    def __str__(self):
        return f"JournalBatch for {self.pool.name} @ {self.batch_date}"


class JournalEntry(TenantScopedModel):
    batch = models.ForeignKey(JournalBatch, on_delete=models.CASCADE, related_name="entries")
    account_name = models.CharField(max_length=255)
    entry_type = models.CharField(max_length=10, choices=JournalEntryType.choices)
    amount = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        return f"{self.entry_type} {self.account_name} = {self.amount}"


class IncomeExpenseEventType(models.TextChoices):
    INCOME = "income", "Income"
    EXPENSE = "expense", "Expense"


class IncomeExpenseEventStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    POSTED = "posted", "Posted"


class IncomeExpenseEvent(TenantScopedModel):
    """
    A manually-recorded income or expense item for a pool (e.g. a
    provision reversal, an ad-hoc operational expense) that isn't produced
    by the AllocationRun -> JournalBatch pipeline. Tracked here as its own
    maker-checker record; posting it does not itself create JournalEntry
    rows - that integration is future scope, this model only tracks the
    event's own lifecycle for now.
    """

    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="income_expense_events"
    )
    event_type = models.CharField(max_length=10, choices=IncomeExpenseEventType.choices)
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    event_date = models.DateField()
    description = models.TextField()
    status = models.CharField(
        max_length=10, choices=IncomeExpenseEventStatus.choices, default=IncomeExpenseEventStatus.PENDING
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    posted_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.event_type} {self.category} {self.amount} - {self.pool.name} ({self.status})"
