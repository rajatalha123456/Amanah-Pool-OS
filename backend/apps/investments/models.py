from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TenantScopedModel


class CapitalAccountStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CLOSED = "closed", "Closed"


class KYCStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"


class RiskTolerance(models.TextChoices):
    CONSERVATIVE = "conservative", "Conservative"
    MODERATE = "moderate", "Moderate"
    AGGRESSIVE = "aggressive", "Aggressive"


class SubscriptionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSED = "processed", "Processed"


class RedemptionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSED = "processed", "Processed"
    REJECTED = "rejected", "Rejected"


class NAVSnapshotStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"


class ImpairmentEventStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"


class CapitalAccount(TenantScopedModel):
    """
    An investor's unitized holding in an investment_pool-model Pool.
    Investor identity is a plain name for now, not linked to a User -
    linking to an investor_member User is future scope.
    """

    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.PROTECT, related_name="capital_accounts"
    )
    investor_name = models.CharField(max_length=255)
    investor_reference = models.CharField(max_length=50)
    units_held = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    status = models.CharField(
        max_length=10, choices=CapitalAccountStatus.choices, default=CapitalAccountStatus.ACTIVE
    )
    # Optional link to the participant registry: its login user sees this account
    # in the self-service portal (and nobody else's).
    participant = models.ForeignKey(
        "participants.Participant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="capital_accounts",
    )
    # Musharakah: the managing partner's own capital. It counts towards the capital ratio that
    # governs loss (BR-006) but is not an investor line; its profit comes through the PSR.
    is_managing_partner = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "investor_reference"], name="unique_investor_reference_per_tenant"
            ),
        ]

    def __str__(self):
        return f"{self.investor_reference} - {self.investor_name}"


class InvestorProfile(TenantScopedModel):
    capital_account = models.OneToOneField(
        CapitalAccount, on_delete=models.CASCADE, related_name="investor_profile"
    )
    kyc_status = models.CharField(
        max_length=10, choices=KYCStatus.choices, default=KYCStatus.PENDING
    )
    kyc_tier = models.CharField(max_length=10, default="basic")
    id_document_type = models.CharField(max_length=50)
    id_document_number = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    address = models.TextField()
    risk_tolerance = models.CharField(max_length=15, choices=RiskTolerance.choices)
    suitability_assessment_notes = models.TextField(null=True, blank=True)
    verified_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_investor_profiles",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"KYC - {self.capital_account.investor_reference}"


class ImpairmentEvent(TenantScopedModel):
    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="impairment_events"
    )
    valuation_date = models.DateField()
    loss_amount = models.DecimalField(max_digits=18, decimal_places=2)
    loss_percentage = models.DecimalField(max_digits=8, decimal_places=6)
    reason = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=ImpairmentEventStatus.choices,
        default=ImpairmentEventStatus.DRAFT,
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_impairment_events",
    )

    def __str__(self):
        return f"Impairment {self.pool.code} - {self.loss_amount} ({self.status})"


class Subscription(TenantScopedModel):
    """
    A capital inflow into a CapitalAccount at a given NAV. Only ever
    created via apps.investments.views.CapitalAccountViewSet.subscribe(),
    which computes units_allotted and updates the account's units_held.
    """

    capital_account = models.ForeignKey(
        CapitalAccount, on_delete=models.PROTECT, related_name="subscriptions"
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    nav_per_unit = models.DecimalField(max_digits=18, decimal_places=6)
    units_allotted = models.DecimalField(max_digits=18, decimal_places=6)
    transaction_date = models.DateField()
    status = models.CharField(
        max_length=10, choices=SubscriptionStatus.choices, default=SubscriptionStatus.PENDING
    )

    def __str__(self):
        return f"Subscription {self.amount} @ {self.nav_per_unit} - {self.capital_account}"


class NAVSnapshot(TenantScopedModel):
    """
    A point-in-time NAV calculation for a pool. total_pool_value is a manual
    Finance Maker input for now (in practice this should come from a Balance
    Sheet / asset valuation feed - that integration is future scope).
    total_units_outstanding and nav_per_unit are computed by
    apps.investments.nav_engine.calculate_nav() at creation time, never
    entered directly.

    Multiple drafts for the same pool/valuation_date are allowed (e.g. a
    Finance Maker re-entering a corrected total_pool_value before it's
    published), but only one snapshot per pool/valuation_date may ever be
    published - enforced by the partial unique constraint below.
    """

    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="nav_snapshots"
    )
    valuation_date = models.DateField()
    total_pool_value = models.DecimalField(max_digits=18, decimal_places=2)
    total_units_outstanding = models.DecimalField(max_digits=18, decimal_places=6)
    nav_per_unit = models.DecimalField(max_digits=18, decimal_places=6)
    status = models.CharField(
        max_length=10, choices=NAVSnapshotStatus.choices, default=NAVSnapshotStatus.DRAFT
    )
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    published_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "pool", "valuation_date"],
                condition=models.Q(status=NAVSnapshotStatus.PUBLISHED),
                name="unique_published_nav_per_pool_per_date",
            ),
        ]

    def __str__(self):
        return f"NAV {self.nav_per_unit} for {self.pool} @ {self.valuation_date} ({self.status})"


class Redemption(TenantScopedModel):
    """
    A capital outflow from a CapitalAccount at a given NAV. Only ever
    created via apps.investments.views.CapitalAccountViewSet.redeem(),
    which validates units_redeemed against the account's units_held and
    computes amount.
    """

    capital_account = models.ForeignKey(
        CapitalAccount, on_delete=models.PROTECT, related_name="redemptions"
    )
    units_redeemed = models.DecimalField(max_digits=18, decimal_places=6)
    nav_per_unit = models.DecimalField(max_digits=18, decimal_places=6)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    transaction_date = models.DateField()
    status = models.CharField(
        max_length=10, choices=RedemptionStatus.choices, default=RedemptionStatus.PENDING
    )
    requested_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    approved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Redemption {self.units_redeemed} @ {self.nav_per_unit} - {self.capital_account}"


class UnitMovementType(models.TextChoices):
    SUBSCRIPTION = "subscription", "Subscription"
    REDEMPTION = "redemption", "Redemption"
    IMPAIRMENT = "impairment", "Impairment"


class UnitMovement(TenantScopedModel):
    """
    Dated change in a capital account's units. The movements are what let a
    profit distribution weight each investor by the units they actually held on
    each day of the period (time-weighted), not by today's balance. A movement
    takes effect from the start of its effective_date.
    """

    capital_account = models.ForeignKey(CapitalAccount, on_delete=models.PROTECT, related_name="movements")
    effective_date = models.DateField()
    units_delta = models.DecimalField(max_digits=18, decimal_places=6)
    movement_type = models.CharField(max_length=20, choices=UnitMovementType.choices)
    reference_id = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["effective_date", "created_at"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Unit movements are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Unit movements are append-only.")

    def __str__(self):
        return f"{self.capital_account} {self.movement_type} {self.units_delta} @ {self.effective_date}"


class DistributionRunStatus(models.TextChoices):
    SIMULATED = "simulated", "Simulated"
    PENDING_APPROVAL = "pending_approval", "Pending Approval"
    # Same ceremony as a bank-pool run (BRD 6.3): independent check -> Shariah review -> release by the signatory.
    CHECKED = "checked", "Independent Check Complete"
    SHARIAH_REVIEW = "shariah_review", "Shariah Review Complete"
    SIGNED = "signed", "Signed"
    REJECTED = "rejected", "Rejected"
    REVERSED = "reversed", "Reversed"


class InvestmentDistributionRun(TenantScopedModel):
    """
    Profit (or loss) distribution of an investment pool for a period.

    Mudarabah: the manager (Mudarib) takes its approved PSR share of profit; the
    investors (Rabb-ul-Maal) share the rest pro-rata to their time-weighted
    units. A loss is borne by the investors alone, pro-rata to units - the
    Mudarib never shares in a capital loss and never receives a share of capital.
    Same control model as AllocationRun: maker-checker, sealed by a calculation
    hash, immutable once signed, corrected by reversal + linked rerun.
    """

    pool = models.ForeignKey("pools.Pool", on_delete=models.PROTECT, related_name="distribution_runs")
    period_start = models.DateField()
    period_end = models.DateField()
    gross_income = models.DecimalField(max_digits=18, decimal_places=2)
    direct_expenses = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    distributable_amount = models.DecimalField(max_digits=18, decimal_places=2)
    investor_share = models.DecimalField(max_digits=18, decimal_places=2)
    manager_share = models.DecimalField(max_digits=18, decimal_places=2)
    rounding_residual = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_average_units = models.DecimalField(max_digits=18, decimal_places=6)
    is_loss = models.BooleanField(default=False)
    config_snapshot = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=DistributionRunStatus.choices, default=DistributionRunStatus.SIMULATED
    )
    calculation_hash = models.CharField(max_length=64, blank=True, default="")
    replaces_run = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="restatements"
    )
    is_restatement = models.BooleanField(default=False)
    restatement_reason = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    checked_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    checked_at = models.DateTimeField(null=True, blank=True)
    shariah_signed_off_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    shariah_signed_off_at = models.DateTimeField(null=True, blank=True)
    shariah_review_note = models.TextField(null=True, blank=True)
    released_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    released_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    _SIGNED_MUTABLE_FIELDS = frozenset({"status", "restatement_reason", "updated_at"})

    def save(self, *args, **kwargs):
        if not self._state.adding:
            prior = (
                InvestmentDistributionRun._base_manager.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )
            if prior == DistributionRunStatus.REVERSED:
                raise ValidationError("A reversed distribution run is immutable.")
            if prior == DistributionRunStatus.SIGNED:
                update_fields = kwargs.get("update_fields")
                allowed = (
                    update_fields is not None
                    and set(update_fields) <= self._SIGNED_MUTABLE_FIELDS
                    and self.status in (DistributionRunStatus.SIGNED, DistributionRunStatus.REVERSED)
                )
                if not allowed:
                    raise ValidationError("A signed distribution run is immutable; use a reversal and linked rerun.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status in (DistributionRunStatus.SIGNED, DistributionRunStatus.REVERSED):
            raise ValidationError("Signed or reversed distribution runs cannot be deleted.")
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.pool} distribution {self.period_start}..{self.period_end} ({self.status})"


class InvestmentDistributionLine(TenantScopedModel):
    run = models.ForeignKey(InvestmentDistributionRun, on_delete=models.CASCADE, related_name="lines")
    capital_account = models.ForeignKey(CapitalAccount, on_delete=models.PROTECT, related_name="distribution_lines")
    average_units = models.DecimalField(max_digits=18, decimal_places=6)
    share_ratio = models.DecimalField(max_digits=18, decimal_places=12)
    allocated_amount = models.DecimalField(max_digits=18, decimal_places=2)

    def _run_is_locked(self):
        return InvestmentDistributionRun._base_manager.filter(
            pk=self.run_id,
            status__in=[DistributionRunStatus.SIGNED, DistributionRunStatus.REVERSED],
        ).exists()

    def save(self, *args, **kwargs):
        if self._run_is_locked():
            raise ValidationError("Lines of a signed or reversed distribution run are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self._run_is_locked():
            raise ValidationError("Lines of a signed or reversed distribution run are immutable.")
        return super().delete(*args, **kwargs)


class NegligenceCaseStatus(models.TextChoices):
    OPEN = "open", "Under investigation"
    LIABLE = "liable", "Manager liable"
    CLEARED = "cleared", "Manager cleared"


class NegligenceCase(TenantScopedModel):
    """
    A manager negligence / misconduct allegation (BRD 6.4: "opens a controlled investigation case").
    While a case is open, loss allocation for the periods it concerns is frozen. Only the Shariah
    Board can determine it. A "liable" determination fixes the loss amount the manager must bear
    (BR-006: capital-ratio loss allocation applies "unless an approved liability determination
    applies"); the amount is applied once, to the first loss distribution that covers the case.
    """

    pool = models.ForeignKey("pools.Pool", on_delete=models.CASCADE, related_name="negligence_cases")
    title = models.CharField(max_length=255)
    allegation = models.TextField()
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=10, choices=NegligenceCaseStatus.choices, default=NegligenceCaseStatus.OPEN)
    raised_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    notes = models.JSONField(default=list, blank=True)  # append-only investigation log
    determination_note = models.TextField(blank=True, default="")
    liability_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    determined_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    determined_at = models.DateTimeField(null=True, blank=True)
    applied_run = models.ForeignKey(
        "InvestmentDistributionRun", on_delete=models.PROTECT, null=True, blank=True, related_name="negligence_cases"
    )

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            prior = NegligenceCase._base_manager.filter(pk=self.pk).values_list("status", flat=True).first()
            if prior in (NegligenceCaseStatus.LIABLE, NegligenceCaseStatus.CLEARED):
                update_fields = kwargs.get("update_fields")
                if update_fields is None or not set(update_fields) <= {"applied_run", "updated_at"}:
                    raise ValidationError("A determined negligence case is final.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Negligence cases are never deleted.")

    def __str__(self):
        return f"{self.title} ({self.status})"


class PoolDisclosure(TenantScopedModel):
    """Sealed investor disclosure of a pool's terms, fees and risks. Never edited; a change is a new version."""

    pool = models.ForeignKey("pools.Pool", on_delete=models.CASCADE, related_name="disclosures")
    version = models.IntegerField()
    summary = models.TextField(blank=True, default="")
    terms = models.JSONField()
    terms_hash = models.CharField(max_length=64)
    risk_warnings = models.TextField()
    fee_statement = models.TextField()
    # published_by is the person who prepared the disclosure; a different person approves it (BRD: Product /
    # Pool Manager drafts disclosures, Risk or the Shariah Board validates them).
    published_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")
    status = models.CharField(max_length=15, choices=[("pending_review", "Pending review"), ("published", "Published")],
                              default="published")
    approved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["pool", "version"], name="unique_pool_disclosure_version")]

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError

        if not self._state.adding:
            raise ValidationError("A published disclosure is immutable; publish a new version.")
        super().save(*args, **kwargs)


class DisclosureAcknowledgement(TenantScopedModel):
    capital_account = models.ForeignKey(CapitalAccount, on_delete=models.CASCADE, related_name="disclosure_acks")
    disclosure = models.ForeignKey(PoolDisclosure, on_delete=models.PROTECT, related_name="acknowledgements")
    acknowledged_at = models.DateTimeField()
    method = models.CharField(max_length=20)  # in_person, otp, e_sign, portal
    evidence_reference = models.CharField(max_length=100, blank=True, default="")
    by_investor = models.BooleanField(default=False)
    recorded_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["capital_account", "disclosure"], name="unique_disclosure_ack")
        ]
