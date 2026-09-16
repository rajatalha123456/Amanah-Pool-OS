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
