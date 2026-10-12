"""
Portfolio summary for the dashboards: every figure comes from recorded data, and a figure that cannot be
computed is returned as null (the UI shows "-"), never a placeholder.

  funds   bank pool        total of the latest day's recorded balances
          investment pool  total value of the latest published NAV
          community circle contributions received less payouts disbursed
  profit  the latest SIGNED run / distribution of the pool (simulated or pending runs are ignored)
  yield   that run's distributable profit over the period's average funds, annualised (actual/365)
"""

from decimal import Decimal

from django.db.models import Sum

ZERO = Decimal("0")


def _pct(value, base, days):
    if not base or not days:
        return None
    return str((value / base * Decimal(365) / Decimal(days) * 100).quantize(Decimal("0.01")))


def _bank(pool):
    from apps.allocation.models import AllocationRun, AllocationRunStatus
    from apps.pools.models import DailyBalance

    latest = DailyBalance._base_manager.filter(pool=pool).order_by("-value_date").values_list("value_date", flat=True).first()
    funds = None
    if latest:
        funds = DailyBalance._base_manager.filter(pool=pool, value_date=latest).aggregate(t=Sum("balance_amount"))["t"]
    run = (
        AllocationRun._base_manager.filter(pool=pool, status=AllocationRunStatus.SIGNED).order_by("-value_date").first()
    )
    profit = yield_pct = period = None
    if run:
        average_funds = sum((line.daily_funds for line in run.lines.all()), ZERO)
        days = (run.value_date - run.effective_period_start).days + 1
        profit = run.distributable_amount
        yield_pct = _pct(run.distributable_amount, average_funds, days)
        period = f"{run.effective_period_start} to {run.value_date}"
    return funds, profit, yield_pct, period


def _investment(pool):
    from apps.investments.models import (
        DistributionRunStatus,
        InvestmentDistributionRun,
        NAVSnapshot,
        NAVSnapshotStatus,
    )

    nav = NAVSnapshot._base_manager.filter(pool=pool, status=NAVSnapshotStatus.PUBLISHED).order_by("-valuation_date").first()
    funds = nav.total_pool_value if nav else None
    run = (
        InvestmentDistributionRun._base_manager.filter(pool=pool, status=DistributionRunStatus.SIGNED)
        .order_by("-period_end")
        .first()
    )
    profit = yield_pct = period = None
    if run:
        days = (run.period_end - run.period_start).days + 1
        profit = run.distributable_amount
        base = funds  # pool value at the latest NAV approximates average funds; labelled indicative in the UI
        yield_pct = _pct(run.distributable_amount, base, days)
        period = f"{run.period_start} to {run.period_end}"
    return funds, profit, yield_pct, period


def _circle(pool):
    from apps.circles.models import Contribution, ContributionStatus, Payout, PayoutStatus

    collected = Contribution._base_manager.filter(member__pool=pool, status=ContributionStatus.RECEIVED).aggregate(t=Sum("amount"))["t"] or ZERO
    paid = Payout._base_manager.filter(pool=pool, status=PayoutStatus.DISBURSED).aggregate(t=Sum("amount"))["t"] or ZERO
    return collected - paid, None, None, None


def portfolio_summary(pools):
    rows, total_funds, total_profit = [], ZERO, ZERO
    for pool in pools:
        model = pool.product.operating_model
        funds, profit, yield_pct, period = {"bank_pool": _bank, "investment_pool": _investment, "community_circle": _circle}.get(
            model, lambda p: (None, None, None, None)
        )(pool)
        if funds is not None:
            total_funds += funds
        if profit is not None:
            total_profit += profit
        rows.append({
            "pool": str(pool.id), "code": pool.code, "name": pool.name, "model": model, "status": pool.status,
            "contract_type": pool.product.contract_template.contract_type,
            "funds": str(funds) if funds is not None else None,
            "last_signed_profit": str(profit) if profit is not None else None,
            "annualised_yield_pct": yield_pct,
            "profit_period": period,
        })
    return {
        "pools": rows,
        "total_funds": str(total_funds),
        "total_signed_profit": str(total_profit),
        "basis": "Funds: latest recorded balances / published NAV / circle collections net of payouts. "
        "Profit and yield: latest signed run per pool only.",
    }
