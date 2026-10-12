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
    email = models.EmailField(blank=True, default="")
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


class ConsentPurpose(models.TextChoices):
    DATA_PROCESSING = "data_processing", "Processing of personal data for the account"
    ELECTRONIC_STATEMENTS = "electronic_statements", "Electronic delivery of statements and notices"
    THIRD_PARTY_SHARING = "third_party_sharing", "Sharing with banks / regulators beyond legal duty"
    MARKETING = "marketing", "Product communications"


class ConsentStatus(models.TextChoices):
    GRANTED = "granted", "Granted"
    WITHDRAWN = "withdrawn", "Withdrawn"


class Consent(TenantScopedModel):
    """
    A participant's consent for one purpose (BRD privacy: purpose limitation, consent, data-subject workflows).
    A grant is a permanent record; withdrawing it stamps the withdrawal and keeps the history. Re-granting creates
    a new row, so the evidence of every period of consent survives.
    """

    participant = models.ForeignKey(Participant, on_delete=models.PROTECT, related_name="consents")
    purpose = models.CharField(max_length=30, choices=ConsentPurpose.choices)
    status = models.CharField(max_length=10, choices=ConsentStatus.choices, default=ConsentStatus.GRANTED)
    granted_at = models.DateTimeField()
    method = models.CharField(max_length=20)  # in_person, e_sign, otp, portal
    evidence_reference = models.CharField(max_length=100, blank=True, default="")
    recorded_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawal_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-granted_at"]
        constraints = [
            # At most one live consent per participant and purpose.
            models.UniqueConstraint(
                fields=["participant", "purpose"], condition=models.Q(status="granted"), name="one_live_consent_per_purpose"
            ),
        ]
