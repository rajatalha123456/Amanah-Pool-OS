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
