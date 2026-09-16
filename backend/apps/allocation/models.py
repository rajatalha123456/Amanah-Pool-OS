from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TenantScopedModel


class WeightageBandStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"


class PSRStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"


class WeightageBand(TenantScopedModel):
    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="weightage_bands"
    )
    participant_class = models.CharField(max_length=100)
    weightage = models.DecimalField(max_digits=5, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=WeightageBandStatus.choices, default=WeightageBandStatus.DRAFT
    )

    def __str__(self):
        return f"{self.pool.name} - {self.participant_class} ({self.weightage})"


class ProfitSharingRatio(TenantScopedModel):
    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="psr_schedules"
    )
    depositor_share = models.DecimalField(max_digits=5, decimal_places=2)
    mudarib_share = models.DecimalField(max_digits=5, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PSRStatus.choices, default=PSRStatus.DRAFT)

    def clean(self):
        if self.depositor_share is not None and self.mudarib_share is not None:
            # Values may arrive as plain strings (e.g. from a fixture or
            # `Model(**kwargs)` before field validation runs), so coerce
            # explicitly rather than relying on them already being Decimal.
            depositor_share = Decimal(self.depositor_share)
            mudarib_share = Decimal(self.mudarib_share)
            if depositor_share + mudarib_share != Decimal("100.00"):
                raise ValidationError(
                    "depositor_share and mudarib_share must add up to 100.00."
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pool.name} - {self.depositor_share}/{self.mudarib_share}"


class AllocationRunStatus(models.TextChoices):
    SIMULATED = "simulated", "Simulated"
    PENDING_APPROVAL = "pending_approval", "Pending Approval"
    SIGNED = "signed", "Signed"
    REJECTED = "rejected", "Rejected"


class AllocationRun(TenantScopedModel):
    """
    A profit allocation calculation for one pool/value_date. All computed
    fields here are populated from apps.allocation.engine.calculate_allocation()
    - this model only stores the result, it never recomputes anything itself.
    """

    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="allocation_runs"
    )
    value_date = models.DateField()
    gross_income = models.DecimalField(max_digits=18, decimal_places=2)
    direct_expenses = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    distributable_amount = models.DecimalField(max_digits=18, decimal_places=2)
    total_weighted_funds = models.DecimalField(max_digits=18, decimal_places=2)
    depositor_pool_share = models.DecimalField(max_digits=18, decimal_places=2)
    mudarib_share = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=AllocationRunStatus.choices, default=AllocationRunStatus.SIMULATED
    )
    calculation_hash = models.CharField(max_length=64, null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    checked_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checked_allocation_runs",
    )
    checked_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.pool.name} allocation @ {self.value_date} ({self.status})"


class AllocationLine(TenantScopedModel):
    allocation_run = models.ForeignKey(
        AllocationRun, on_delete=models.CASCADE, related_name="lines"
    )
    participant_class = models.CharField(max_length=100)
    daily_funds = models.DecimalField(max_digits=18, decimal_places=2)
    weightage = models.DecimalField(max_digits=5, decimal_places=2)
    weighted_funds = models.DecimalField(max_digits=18, decimal_places=2)
    allocated_amount = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        return f"{self.allocation_run} - {self.participant_class}"


class DepositorStatement(TenantScopedModel):
    """
    A plain-language, per-participant-class statement generated from a
    signed AllocationRun. period_start/period_end are both the run's
    value_date for now (single-day period; multi-day period tracking is
    future scope), and opening_balance is simplified to the
    AllocationLine's daily_funds until real opening-balance/period
    tracking exists.
    """

    allocation_run = models.ForeignKey(
        AllocationRun, on_delete=models.CASCADE, related_name="statements"
    )
    participant_class = models.CharField(max_length=100)
    period_start = models.DateField()
    period_end = models.DateField()
    opening_balance = models.DecimalField(max_digits=18, decimal_places=2)
    net_deposits = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    profit_allocated = models.DecimalField(max_digits=18, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=18, decimal_places=2)
    narrative = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.allocation_run} - {self.participant_class} statement"
