"""
Pool income and expense for an allocation period, derived from the ledger (BR-005).

A run's gross income and direct expenses are *not* typed in: they are the totals of the
pool's POSTED income/expense events dated inside the period that no other signed run has
already consumed. This is what keeps non-permissible income and bank-absorbed overheads
out of distributable profit:

  * permissible income      -> gross income
  * non-permissible income  -> excluded; routed to purification (PurificationEntry)
  * direct expense          -> direct expenses (only the pool-chargeable amount)
  * indirect overhead       -> excluded; absorbed by the bank (SBP IBD 03/2012)

Pending (unposted) events in the period block a run: close readiness requires every
event to be posted first.
"""

from decimal import Decimal

from django.db.models import Q

from apps.accounting.models import (
    CostClassification,
    IncomeExpenseEvent,
    IncomeExpenseEventStatus,
    IncomeExpenseEventType,
)

ZERO = Decimal("0.00")


def derive_income(pool, period_start, period_end, replaces_run=None):
    """
    Totals for [period_start, period_end]. Events already consumed by a *different* run
    are not available; those consumed by `replaces_run` are (a restatement re-reads the
    period it corrects).
    """

    in_period = IncomeExpenseEvent._base_manager.filter(
        tenant_id=pool.tenant_id, pool=pool, event_date__gte=period_start, event_date__lte=period_end
    )
    available = Q(allocation_run__isnull=True)
    if replaces_run is not None:
        available |= Q(allocation_run=replaces_run)

    posted = list(
        in_period.filter(status=IncomeExpenseEventStatus.POSTED).filter(available).order_by("event_date", "created_at")
    )
    pending_count = in_period.filter(status=IncomeExpenseEventStatus.PENDING).count()

    gross = ZERO
    non_permissible = ZERO
    direct = ZERO
    overhead = ZERO
    for event in posted:
        if event.event_type == IncomeExpenseEventType.INCOME:
            if event.cost_classification == CostClassification.NON_PERMISSIBLE_INCOME or event.quarantined_to_charity:
                non_permissible += event.amount
            else:
                gross += event.pool_chargeable_amount
        else:
            direct += event.pool_chargeable_amount
            overhead += event.bank_absorbed_amount

    return {
        "gross_income": gross,
        "direct_expenses": direct,
        "non_permissible_income": non_permissible,
        "bank_absorbed_overhead": overhead,
        "event_count": len(posted),
        "event_ids": [str(event.id) for event in posted],
        "pending_count": pending_count,
    }


def income_source_snapshot(totals):
    """JSON-safe record of the derivation, sealed into the run's calculation hash."""

    return {
        "mode": "derived_from_events",
        "event_count": totals["event_count"],
        "event_ids": totals["event_ids"],
        "gross_income": str(totals["gross_income"]),
        "direct_expenses": str(totals["direct_expenses"]),
        "excluded_non_permissible_income": str(totals["non_permissible_income"]),
        "excluded_bank_absorbed_overhead": str(totals["bank_absorbed_overhead"]),
    }


def manual_override_snapshot(reason, derived_totals):
    """A hand-typed figure is an override: the reason and the ledger-derived figures it replaces are sealed."""

    return {
        "mode": "manual_override",
        "reason": reason,
        "derived_gross_income": str(derived_totals["gross_income"]),
        "derived_direct_expenses": str(derived_totals["direct_expenses"]),
        "excluded_non_permissible_income": str(derived_totals["non_permissible_income"]),
    }


def resolve_income(
    pool,
    period_start,
    period_end,
    *,
    gross_override=None,
    expenses_override=None,
    override_reason="",
    replaces_run=None,
    block_on_pending=True,
):
    """
    Returns (gross_income, direct_expenses, income_source_snapshot, derived_totals).

    Without an override the figures come from the ledger. A hand-typed gross income is an
    override (BRD Section 11: every override needs a reason) and its reason is sealed with
    the run. Raises ValueError with a user-facing message when the figures cannot be
    established.
    """

    totals = derive_income(pool, period_start, period_end, replaces_run=replaces_run)

    if gross_override is None:
        if expenses_override is not None:
            raise ValueError("direct_expenses can only be supplied together with gross_income (manual override).")
        if block_on_pending and totals["pending_count"]:
            raise ValueError(
                f"{totals['pending_count']} income/expense event(s) in this period are still pending - "
                "post (or remove) them before running the allocation."
            )
        if totals["event_count"] == 0:
            raise ValueError(
                "No posted income/expense events fall in this period. Post the pool's events, "
                "or supply gross_income with an override_reason."
            )
        return totals["gross_income"], totals["direct_expenses"], income_source_snapshot(totals), totals

    reason = (override_reason or "").strip()
    if not reason:
        raise ValueError("A manual gross_income is an override and needs an override_reason.")
    expenses = Decimal(expenses_override) if expenses_override is not None else ZERO
    return Decimal(gross_override), expenses, manual_override_snapshot(reason, totals), totals
