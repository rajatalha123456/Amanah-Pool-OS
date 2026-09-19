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
        "pools.Pool", on_delete=models.CASCADE, related_name="capital_accounts"
    )
    investor_name = models.CharField(max_length=255)
    investor_reference = models.CharField(max_length=50)
    units_held = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    status = models.CharField(
        max_length=10, choices=CapitalAccountStatus.choices, default=CapitalAccountStatus.ACTIVE
    )

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
        CapitalAccount, on_delete=models.CASCADE, related_name="subscriptions"
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
        CapitalAccount, on_delete=models.CASCADE, related_name="redemptions"
    )
    units_redeemed = models.DecimalField(max_digits=18, decimal_places=6)
    nav_per_unit = models.DecimalField(max_digits=18, decimal_places=6)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    transaction_date = models.DateField()
    status = models.CharField(
        max_length=10, choices=RedemptionStatus.choices, default=RedemptionStatus.PENDING
    )

    def __str__(self):
        return f"Redemption {self.units_redeemed} @ {self.nav_per_unit} - {self.capital_account}"
