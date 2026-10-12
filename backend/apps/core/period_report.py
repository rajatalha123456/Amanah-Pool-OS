"""
Periodic management / regulatory return (BRD Section 8 reporting).

One row per pool for a date range, computed only from recorded data. A number that has no source (e.g. a pool
with no signed run in the range) is returned as null, never zero-filled. The whole report carries a SHA-256
seal over its content so a copy that was edited afterwards no longer matches.
"""

import csv
import hashlib
import io
import json
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

ZERO = Decimal("0.00")


def _s(value):
    return None if value is None else str(value)


def _bank(pool, start, end):
    from apps.allocation.models import AllocationRun, AllocationRunStatus
    from apps.pools.models import DailyBalance

    runs = list(
        AllocationRun._base_manager.filter(
            pool=pool, status=AllocationRunStatus.SIGNED, value_date__gte=start, value_date__lte=end
        ).order_by("value_date")
    )
    last_balance = (
        DailyBalance._base_manager.filter(pool=pool, value_date__lte=end).order_by("-value_date")
        .values_list("value_date", flat=True).first()
    )
    closing = None
    if last_balance:
        closing = DailyBalance._base_manager.filter(pool=pool, value_date=last_balance).aggregate(t=Sum("balance_amount"))["t"]
    restated = AllocationRun._base_manager.filter(
        pool=pool, value_date__gte=start, value_date__lte=end, status=AllocationRunStatus.REVERSED
    ).count()
    if not runs:
        return {"closing_funds": _s(closing), "signed_runs": 0, "restated_runs": restated}
    return {
        "closing_funds": _s(closing),
        "signed_runs": len(runs),
        "restated_runs": restated,
        "gross_income": _s(sum((r.gross_income for r in runs), ZERO)),
        "direct_expenses": _s(sum((r.direct_expenses for r in runs), ZERO)),
        "distributable_profit": _s(sum((r.distributable_amount for r in runs), ZERO)),
        "manager_share": _s(sum((r.mudarib_share for r in runs), ZERO)),
        "participant_share": _s(sum((r.depositor_pool_share for r in runs), ZERO)),
        "per_transfer": _s(sum((r.per_amount for r in runs), ZERO)),
        "irr_transfer": _s(sum((r.irr_amount for r in runs), ZERO)),
        "rounding_residual": _s(sum((r.rounding_residual for r in runs), ZERO)),
    }


def _investment(pool, start, end):
    from apps.investments.models import (
        DistributionRunStatus,
        InvestmentDistributionRun,
        NAVSnapshot,
        NAVSnapshotStatus,
        Redemption,
        RedemptionStatus,
        Subscription,
    )

    nav = (
        NAVSnapshot._base_manager.filter(pool=pool, status=NAVSnapshotStatus.PUBLISHED, valuation_date__lte=end)
        .order_by("-valuation_date").first()
    )
    runs = list(
        InvestmentDistributionRun._base_manager.filter(
            pool=pool, status=DistributionRunStatus.SIGNED, period_end__gte=start, period_end__lte=end
        )
    )
    subs = Subscription._base_manager.filter(
        capital_account__pool=pool, transaction_date__gte=start, transaction_date__lte=end
    ).aggregate(t=Sum("amount"), n=Count("id"))
    reds = Redemption._base_manager.filter(
        capital_account__pool=pool, status=RedemptionStatus.PROCESSED, transaction_date__gte=start, transaction_date__lte=end
    ).aggregate(t=Sum("amount"), n=Count("id"))
    row = {
        "closing_funds": _s(nav.total_pool_value) if nav else None,
        "nav_per_unit": _s(nav.nav_per_unit) if nav else None,
        "subscriptions": _s(subs["t"] or ZERO), "subscription_count": subs["n"],
        "redemptions": _s(reds["t"] or ZERO), "redemption_count": reds["n"],
        "signed_runs": len(runs),
    }
    if runs:
        row.update({
            "gross_income": _s(sum((r.gross_income for r in runs), ZERO)),
            "direct_expenses": _s(sum((r.direct_expenses for r in runs), ZERO)),
            "distributable_profit": _s(sum((r.distributable_amount for r in runs), ZERO)),
            "manager_share": _s(sum((r.manager_share for r in runs), ZERO)),
            "participant_share": _s(sum((r.investor_share for r in runs), ZERO)),
        })
    return row


def _circle(pool, start, end):
    from apps.circles.models import Contribution, ContributionStatus, Payout, PayoutStatus

    paid_in = Contribution._base_manager.filter(
        member__pool=pool, status=ContributionStatus.RECEIVED, contribution_date__gte=start, contribution_date__lte=end
    ).aggregate(t=Sum("amount"), n=Count("id"))
    paid_out = Payout._base_manager.filter(
        pool=pool, status=PayoutStatus.DISBURSED, payout_date__gte=start, payout_date__lte=end
    ).aggregate(t=Sum("amount"), n=Count("id"))
    return {
        "contributions_received": _s(paid_in["t"] or ZERO), "contribution_count": paid_in["n"],
        "payouts_disbursed": _s(paid_out["t"] or ZERO), "payout_count": paid_out["n"],
    }


def _controls(pool, start, end):
    from apps.accounting.models import JournalBatch
    from apps.governance.models import ExceptionCase, PurificationEntry
    from apps.pools.models import PeriodCloseChecklist

    exceptions = ExceptionCase._base_manager.filter(pool=pool)
    purification = PurificationEntry._base_manager.filter(
        pool=pool, identified_date__gte=start, identified_date__lte=end
    ).aggregate(t=Sum("amount"), n=Count("id"))
    batches = JournalBatch._base_manager.filter(pool=pool, batch_date__gte=start, batch_date__lte=end)
    unbalanced = sum(1 for b in batches if b.total_debit != b.total_credit)
    close = (
        PeriodCloseChecklist._base_manager.filter(pool=pool, period_start__lte=end, period_end__gte=start)
        .order_by("-period_end").first()
    )
    return {
        "exceptions_opened_in_period": exceptions.filter(created_at__date__gte=start, created_at__date__lte=end).count(),
        "exceptions_open_now": exceptions.filter(status__in=["open", "investigating"]).count(),
        "high_critical_open_now": exceptions.filter(
            status__in=["open", "investigating"], severity__in=["high", "critical"]
        ).count(),
        "non_permissible_income_identified": _s(purification["t"] or ZERO),
        "non_permissible_income_entries": purification["n"],
        "journal_batches": batches.count(),
        "unbalanced_journal_batches": unbalanced,
        "period_close_status": close.status if close else None,
    }


def build_period_report(tenant, start, end):
    from apps.pools.models import Pool

    rows = []
    for pool in Pool._base_manager.filter(tenant=tenant).select_related("product__contract_template").order_by("code"):
        model = pool.product.operating_model
        figures = {"bank_pool": _bank, "investment_pool": _investment, "community_circle": _circle}.get(model, lambda *a: {})(
            pool, start, end
        )
        rows.append({
            "pool_code": pool.code, "pool_name": pool.name, "operating_model": model,
            "contract_type": pool.product.contract_template.contract_type, "status": pool.status,
            **figures, **_controls(pool, start, end),
        })
    body = {
        "tenant": tenant.code, "period_start": str(start), "period_end": str(end),
        "generated_at": timezone.now().isoformat(), "pools": rows,
        "basis": (
            "Computed from signed runs, published NAVs, recorded balances, contributions, payouts, exceptions and "
            "journals in the period. A blank figure means no source record exists for it. Internal management "
            "report - not a regulatory filing."
        ),
    }
    seal = hashlib.sha256(json.dumps({k: v for k, v in body.items() if k != "generated_at"}, sort_keys=True, default=str).encode()).hexdigest()
    return {**body, "content_hash": seal}


def report_to_csv(report):
    columns = []
    for row in report["pools"]:
        for key in row:
            if key not in columns:
                columns.append(key)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in report["pools"]:
        writer.writerow(["" if row.get(c) is None else row.get(c) for c in columns])
    writer.writerow([])
    writer.writerow(["period", f"{report['period_start']} to {report['period_end']}"])
    writer.writerow(["content_hash", report["content_hash"]])
    return buffer.getvalue()
