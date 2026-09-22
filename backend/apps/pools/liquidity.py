from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum

MIN_HISTORY_RECORDS = 5
TREND_WINDOW_DAYS = 30


def calculate_liquidity_forecast(pool, as_of_date, horizon_days=30):
    """
    Simple trend-based liquidity projection - NOT an ML forecast (see
    README "Liquidity Forecast" section for that future-scope note).

    1. Average daily net change in total pool balance over the last
       TREND_WINDOW_DAYS days of DailyBalance history (day-over-day
       total-balance delta, averaged).
    2. Known upcoming outflows over the next horizon_days:
       - investment_pool: pending Redemptions with transaction_date in
         [as_of_date, as_of_date + horizon_days].
       - community_circle: pending Payouts with payout_date in the same
         window.
       - anything else (e.g. bank_pool): no known-outflow source
         modeled yet, so known_outflows is 0.
    3. projected_balance = current_balance + (trend_per_day * horizon_days)
       - known_outflows.

    Returns insufficient_data=True (with current_balance/as_of_date/
    horizon_days but no trend/projection) rather than raising, when
    there are fewer than MIN_HISTORY_RECORDS DailyBalance rows for the
    pool - the forecast just isn't meaningful yet, which isn't an error.
    """
    from apps.circles.models import Payout, PayoutStatus
    from apps.investments.models import Redemption, RedemptionStatus
    from apps.pools.models import DailyBalance

    daily_balances = DailyBalance.objects.filter(pool=pool, value_date__lte=as_of_date).order_by("value_date")
    history_count = daily_balances.count()

    if history_count < MIN_HISTORY_RECORDS:
        return {
            "pool": str(pool.id),
            "as_of_date": as_of_date.isoformat(),
            "horizon_days": horizon_days,
            "insufficient_data": True,
            "current_balance": None,
            "trend_per_day": None,
            "known_outflows": None,
            "projected_balance": None,
        }

    # Total balance per day (DailyBalance has one row per
    # participant_class, so a day's "total" is the sum across classes).
    totals_by_date = {}
    for row in daily_balances.values("value_date").annotate(day_total=Sum("balance_amount")):
        totals_by_date[row["value_date"]] = row["day_total"]

    trend_window_start = as_of_date - timedelta(days=TREND_WINDOW_DAYS)
    dates_in_window = sorted(d for d in totals_by_date if d >= trend_window_start)

    if len(dates_in_window) < 2:
        trend_per_day = Decimal("0")
    else:
        deltas = [
            totals_by_date[dates_in_window[i]] - totals_by_date[dates_in_window[i - 1]]
            for i in range(1, len(dates_in_window))
        ]
        trend_per_day = sum(deltas) / len(deltas)

    current_balance = totals_by_date[max(totals_by_date)]

    known_outflows = Decimal("0")
    horizon_end = as_of_date + timedelta(days=horizon_days)
    operating_model = pool.product.operating_model

    if operating_model == "investment_pool":
        known_outflows = Redemption.objects.filter(
            capital_account__pool=pool,
            status=RedemptionStatus.PENDING,
            transaction_date__gte=as_of_date,
            transaction_date__lte=horizon_end,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    elif operating_model == "community_circle":
        known_outflows = Payout.objects.filter(
            pool=pool,
            status=PayoutStatus.PENDING,
            payout_date__gte=as_of_date,
            payout_date__lte=horizon_end,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    projected_balance = current_balance + (trend_per_day * horizon_days) - known_outflows

    return {
        "pool": str(pool.id),
        "as_of_date": as_of_date.isoformat(),
        "horizon_days": horizon_days,
        "insufficient_data": False,
        "current_balance": current_balance,
        "trend_per_day": trend_per_day,
        "known_outflows": known_outflows,
        "projected_balance": projected_balance,
    }
