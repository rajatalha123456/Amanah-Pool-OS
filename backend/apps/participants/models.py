from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TenantScopedModel


class KYCStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"


class TaxStatus(models.TextChoices):
    FILER = "filer", "Filer"
    NON_FILER = "non_filer", "Non-Filer"


class PayoutChannel(models.TextChoices):
    RAAST = "raast", "Raast"
    ONE_LINK = "one_link", "1LINK"
    IBT = "ibt", "Inter-branch transfer"


class AccountStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CLOSED = "closed", "Closed"


class Participant(TenantScopedModel):
    """
    A depositor / investor (BRD Section 11: Participant). The owner of one or
    more accounts in pools; profit is allocated and statements are issued per
    participant account, not per customer class.

    `participant_class` is the product/customer class used to look up the
    approved weightage band (e.g. "Retail Regular", "Premium Saver").
    `user` optionally links the participant to an investor/member login so the
    self-service portal only ever shows their own data.
    """

    reference = models.CharField(max_length=50)
    full_name = models.CharField(max_length=255)
    participant_class = models.CharField(max_length=100)
    kyc_status = models.CharField(max_length=10, choices=KYCStatus.choices, default=KYCStatus.PENDING)
    cnic_ntn = models.CharField(max_length=30, blank=True, default="")
    iban = models.CharField(max_length=34, blank=True, default="")
    bank_name = models.CharField(max_length=100, blank=True, default="")
    bic = models.CharField(max_length=11, blank=True, default="")
    tax_status = models.CharField(max_length=10, choices=TaxStatus.choices, default=TaxStatus.FILER)
    zakat_exempt = models.BooleanField(default=False)
    default_channel = models.CharField(max_length=10, choices=PayoutChannel.choices, default=PayoutChannel.RAAST)
    nominee_name = models.CharField(max_length=255, blank=True, default="")
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="participant_profile",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "reference"], name="unique_participant_reference_per_tenant"),
        ]
        ordering = ["reference"]

    def __str__(self):
        return f"{self.reference} - {self.full_name}"


class ParticipantAccount(TenantScopedModel):
    """A participant's account in one pool; the unit balances are imported against."""

    participant = models.ForeignKey(Participant, on_delete=models.PROTECT, related_name="accounts")
    pool = models.ForeignKey("pools.Pool", on_delete=models.PROTECT, related_name="participant_accounts")
    account_number = models.CharField(max_length=50)
    opened_date = models.DateField()
    closed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=AccountStatus.choices, default=AccountStatus.ACTIVE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "account_number"], name="unique_account_number_per_tenant"),
        ]
        ordering = ["account_number"]

    def clean(self):
        if self.closed_date and self.closed_date < self.opened_date:
            raise ValidationError("closed_date cannot be before opened_date.")

    @property
    def participant_class(self):
        return self.participant.participant_class

    def __str__(self):
        return f"{self.account_number} ({self.participant.full_name})"
