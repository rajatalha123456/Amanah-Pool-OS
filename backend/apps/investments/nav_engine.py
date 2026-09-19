"""
Pure NAV calculation. No I/O beyond reading CapitalAccount rows - never
writes anything itself; apps.investments.views.NAVSnapshotViewSet is
responsible for persisting the result as a NAVSnapshot.
"""

from decimal import ROUND_HALF_UP, Decimal

from .models import CapitalAccount, CapitalAccountStatus


def calculate_nav(pool, total_pool_value):
    """
    total_units_outstanding = sum of units_held across this pool's active
    CapitalAccounts. nav_per_unit = total_pool_value / total_units_outstanding,
    rounded half-up to 6 decimal places (matching the field's decimal_places).

    Raises ValueError if there are no active units outstanding for this pool
    (division by zero - there's no meaningful NAV without any holders).
    """

    total_units_outstanding = (
        CapitalAccount.objects.filter(pool=pool, status=CapitalAccountStatus.ACTIVE)
        .values_list("units_held", flat=True)
    )
    total_units_outstanding = sum(total_units_outstanding, Decimal("0"))

    if total_units_outstanding == 0:
        raise ValueError("No active units outstanding for this pool — cannot calculate NAV.")

    nav_per_unit = (Decimal(total_pool_value) / total_units_outstanding).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )

    return {
        "total_units_outstanding": total_units_outstanding,
        "nav_per_unit": nav_per_unit,
    }
