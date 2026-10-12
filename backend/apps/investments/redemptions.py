"""
Redemption workflow (BRD 6.4: exit is subject to valuation, liquidity and terms).

  request  -> a maker (or the investor, for their own account) asks to redeem units; checks KYC,
              unit availability (net of other pending requests) and the product's notice period;
  approve  -> an independent finance checker prices the units at the latest published NAV, checks the
              pool's redemption gate, then moves the units and posts the journal;
  reject   -> the checker declines with a reason; nothing moves.

Product terms (apps.products.Product): `redemption_notice_days` (the dealing date must be at least this
many days after the request) and `redemption_gate_pct` (redemptions approved within any 30-day window
may not exceed this share of the latest published pool value).
"""

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounting.services import post_capital_movement_journal
from apps.pools.period_lock import assert_period_open

from .models import (
    KYCStatus,
    NAVSnapshot,
    NAVSnapshotStatus,
    Redemption,
    RedemptionStatus,
    UnitMovement,
    UnitMovementType,
)

GATE_WINDOW_DAYS = 30
CENT = Decimal("0.01")


def _nav_on(pool, on_date):
    return (
        NAVSnapshot.objects.filter(pool=pool, status=NAVSnapshotStatus.PUBLISHED, valuation_date__lte=on_date)
        .order_by("-valuation_date")
        .first()
    )


def reserved_units(account):
    total = Redemption.objects.filter(capital_account=account, status=RedemptionStatus.PENDING).aggregate(
        t=Sum("units_redeemed")
    )["t"]
    return total or Decimal("0")


def gate_usage(pool, on_date, nav):
    """Amount already redeemed in the 30 days to `on_date` and the gate limit (None = no gate)."""
    used = Redemption.objects.filter(
        capital_account__pool=pool, status=RedemptionStatus.PROCESSED,
        transaction_date__gt=on_date - timedelta(days=GATE_WINDOW_DAYS), transaction_date__lte=on_date,
    ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
    pct = Decimal(pool.product.redemption_gate_pct)
    limit = None if pct >= 100 else (nav.total_pool_value * pct / Decimal("100")).quantize(CENT)
    return used, limit


def request_redemption(*, account, units, dealing_date, user):
    pool = account.pool
    profile = getattr(account, "investor_profile", None)
    if profile is None or profile.kyc_status != KYCStatus.VERIFIED:
        raise ValidationError("KYC verification required before redemption.")
    if units <= 0:
        raise ValidationError({"units_redeemed": ["Units must be positive."]})
    available = account.units_held - reserved_units(account)
    if units > available:
        raise ValidationError(
            f"Cannot redeem {units} units: {account.units_held} held, {reserved_units(account)} already requested."
        )
    notice = pool.product.redemption_notice_days
    today = timezone.localdate()
    if notice and dealing_date < today + timedelta(days=notice):
        raise ValidationError(
            {"transaction_date": [f"This product needs {notice} days' notice: the earliest dealing date is {today + timedelta(days=notice)}."]}
        )
    assert_period_open(pool, dealing_date, what="a redemption")
    nav = _nav_on(pool, min(dealing_date, today))
    if nav is None:
        raise ValidationError("No published NAV is available for this pool; redemptions cannot be priced.")
    return Redemption.objects.create(
        tenant=account.tenant, capital_account=account, units_redeemed=units, nav_per_unit=nav.nav_per_unit,
        amount=(units * nav.nav_per_unit).quantize(CENT, rounding=ROUND_HALF_UP), transaction_date=dealing_date,
        status=RedemptionStatus.PENDING, requested_by=user,
    )


@transaction.atomic
def approve_redemption(redemption, checker):
    redemption = Redemption._base_manager.select_for_update().get(pk=redemption.pk)
    if redemption.status != RedemptionStatus.PENDING:
        raise ValidationError(f"Only a pending redemption can be approved (this one is {redemption.status}).")
    if redemption.requested_by_id == checker.id:
        raise ValidationError("Four-eyes rule: the requester cannot approve their own redemption.")
    account = redemption.capital_account.__class__._base_manager.select_for_update().get(
        pk=redemption.capital_account_id
    )
    pool = account.pool
    today = timezone.localdate()
    if redemption.transaction_date > today:
        raise ValidationError(f"The dealing date {redemption.transaction_date} has not arrived yet.")
    if redemption.units_redeemed > account.units_held:
        raise ValidationError("The account no longer holds enough units for this redemption.")
    assert_period_open(pool, redemption.transaction_date, what="a redemption")

    nav = _nav_on(pool, redemption.transaction_date)
    if nav is None:
        raise ValidationError("No published NAV is available for this pool; redemptions cannot be priced.")
    amount = (redemption.units_redeemed * nav.nav_per_unit).quantize(CENT, rounding=ROUND_HALF_UP)
    used, limit = gate_usage(pool, redemption.transaction_date, nav)
    if limit is not None and used + amount > limit:
        raise ValidationError(
            f"Redemption gate: {used} already redeemed in {GATE_WINDOW_DAYS} days; adding {amount} would exceed "
            f"the limit of {limit} ({pool.product.redemption_gate_pct}% of pool value)."
        )

    redemption.nav_per_unit = nav.nav_per_unit
    redemption.amount = amount
    redemption.status = RedemptionStatus.PROCESSED
    redemption.approved_by = checker
    redemption.approved_at = timezone.now()
    redemption.save()

    account.units_held -= redemption.units_redeemed
    account.save(update_fields=["units_held", "updated_at"])
    UnitMovement.objects.create(
        tenant=account.tenant, capital_account=account, effective_date=redemption.transaction_date,
        units_delta=-redemption.units_redeemed, movement_type=UnitMovementType.REDEMPTION,
        reference_id=str(redemption.id),
    )
    post_capital_movement_journal(
        kind="redemption", tenant=account.tenant, pool=pool, amount=amount,
        on_date=redemption.transaction_date, posted_by=checker,
    )
    return redemption


def reject_redemption(redemption, checker, reason):
    if redemption.status != RedemptionStatus.PENDING:
        raise ValidationError(f"Only a pending redemption can be rejected (this one is {redemption.status}).")
    if not reason.strip():
        raise ValidationError({"reason": ["A rejection reason is required."]})
    redemption.status = RedemptionStatus.REJECTED
    redemption.approved_by = checker
    redemption.approved_at = timezone.now()
    redemption.rejection_reason = reason
    redemption.save()
    return redemption
