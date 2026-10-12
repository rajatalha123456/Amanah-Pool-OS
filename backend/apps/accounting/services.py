"""
Journal posting derived from a signed AllocationRun.

Postings use logical accounts (apps.accounting.chart) that resolve through the
tenant's / pool's AccountMapping to the enterprise GL account name and code
(BRD Section 10). Every entry records its logical `account_key` and `gl_code`.
"""

import logging
from decimal import Decimal

from django.db import transaction

from .chart import ChartResolver
from .models import JournalBatch, JournalBatchStatus, JournalEntry, JournalEntryType
from .reconciliation import check_reconciliation

logger = logging.getLogger("apps")

ZERO = Decimal("0.00")

class JournalIntegrityError(ValueError):
    """Raised when an allocation run cannot be posted as a balanced, tied-out journal."""


def _add(entries, chart, key, entry_type, amount, suffix=""):
    amount = Decimal(amount)
    if amount == 0:
        return
    name, code = chart.resolve(key, suffix)
    entries.append(
        {"account_name": name, "account_key": key, "gl_code": code, "entry_type": entry_type, "amount": amount}
    )


def _add_signed_credit(entries, chart, key, signed_credit, suffix=""):
    """Positive amount credits the account, negative amount debits it."""
    signed_credit = Decimal(signed_credit)
    if signed_credit >= 0:
        _add(entries, chart, key, JournalEntryType.CREDIT, signed_credit, suffix)
    else:
        _add(entries, chart, key, JournalEntryType.DEBIT, -signed_credit, suffix)


def build_allocation_entries(allocation_run):
    """
    Pure builder for the journal of a signed run. Two legs, both balanced:

    1. Period result: income recognised, direct expenses charged, the
       difference parked in `Pool Distributable Profit` (a debit balance if
       the pool made a loss).
    2. Appropriation: the distributable result is cleared to PER/IRR
       reserves, the Mudarib share, each participant class and - only for
       what half-up rounding leaves over - the disclosed rounding account.
       For a loss the participant lines are negative, i.e. the loss is
       absorbed by debiting the capital providers' accounts.
    """

    lines = list(allocation_run.lines.all())
    distributable = Decimal(allocation_run.distributable_amount)
    chart = ChartResolver(allocation_run.tenant_id, allocation_run.pool)
    entries = []

    # Leg 1 - recognise the period result.
    _add(entries, chart, "pool_income", JournalEntryType.DEBIT, allocation_run.gross_income)
    _add(entries, chart, "pool_direct_expense", JournalEntryType.CREDIT, allocation_run.direct_expenses)
    _add_signed_credit(entries, chart, "distributable_profit", distributable)

    # Leg 2 - appropriate the result.
    _add_signed_credit(entries, chart, "distributable_profit", -distributable)
    _add_signed_credit(entries, chart, "per_reserve", allocation_run.per_amount)
    _add_signed_credit(entries, chart, "irr_reserve", allocation_run.irr_amount)
    _add_signed_credit(entries, chart, "mudarib_payable", allocation_run.mudarib_share)
    # The GL carries one control account per participant class; the
    # per-participant sub-ledger is the allocation lines themselves.
    payable_by_class = {}
    for line in lines:
        payable_by_class[line.participant_class] = (
            payable_by_class.get(line.participant_class, Decimal("0")) + line.allocated_amount
        )
    for participant_class in sorted(payable_by_class):
        _add_signed_credit(entries, chart, "depositor_payable", payable_by_class[participant_class], participant_class)
    _add_signed_credit(entries, chart, "rounding_account", allocation_run.rounding_residual)

    return entries


def _totals(entries):
    total_debit = sum(
        (e["amount"] for e in entries if e["entry_type"] == JournalEntryType.DEBIT), ZERO
    )
    total_credit = sum(
        (e["amount"] for e in entries if e["entry_type"] == JournalEntryType.CREDIT), ZERO
    )
    return total_debit, total_credit


def verify_run_ties_out(allocation_run):
    """
    Hard pre-posting control: the components of a run must add up exactly to
    its distributable amount. The platform never balances a difference
    through suspense - only the (tolerance-bounded) rounding residual is
    allowed, and it is posted to the disclosed rounding account.
    """

    lines_total = sum((line.allocated_amount for line in allocation_run.lines.all()), ZERO)
    components = (
        Decimal(allocation_run.per_amount)
        + Decimal(allocation_run.irr_amount)
        + Decimal(allocation_run.mudarib_share)
        + lines_total
        + Decimal(allocation_run.rounding_residual)
    )
    if components != Decimal(allocation_run.distributable_amount):
        raise JournalIntegrityError(
            "Allocation run does not tie out: reserves + Mudarib share + participant lines + "
            f"rounding residual = {components}, distributable = {allocation_run.distributable_amount}."
        )

    line_count = allocation_run.lines.count()
    tolerance = Decimal("0.01") * (line_count + 3)
    if abs(Decimal(allocation_run.rounding_residual)) > tolerance:
        raise JournalIntegrityError(
            f"Rounding residual {allocation_run.rounding_residual} exceeds the permitted tolerance {tolerance}."
        )


def _post_batch(*, run, pool, tenant, batch_date, entries, posted_by, reverses_batch=None, investment_run=None):
    total_debit, total_credit = _totals(entries)
    if total_debit != total_credit:
        raise JournalIntegrityError("Journal batch is not balanced.")

    with transaction.atomic():
        batch = JournalBatch.objects.create(
            tenant=tenant,
            allocation_run=run,
            investment_run=investment_run,
            reverses_batch=reverses_batch,
            pool=pool,
            batch_date=batch_date,
            total_debit=total_debit,
            total_credit=total_credit,
            status=JournalBatchStatus.POSTED,
            posted_by=posted_by,
        )
        JournalEntry.objects.bulk_create(
            [
                JournalEntry(
                    tenant=tenant,
                    batch=batch,
                    account_name=entry["account_name"],
                    account_key=entry.get("account_key", ""),
                    gl_code=entry.get("gl_code", ""),
                    entry_type=entry["entry_type"],
                    amount=entry["amount"],
                )
                for entry in entries
            ]
        )
    return batch


def create_journal_from_allocation(allocation_run, posted_by=None):
    """
    Posts the balanced double-entry JournalBatch for a signed AllocationRun.
    Raises JournalIntegrityError (blocking approval) if the run does not tie
    out or the journal does not balance.
    """

    verify_run_ties_out(allocation_run)
    entries = build_allocation_entries(allocation_run)

    batch = _post_batch(
        run=allocation_run,
        pool=allocation_run.pool,
        tenant=allocation_run.tenant,
        batch_date=allocation_run.value_date,
        entries=entries,
        posted_by=posted_by,
    )

    # The reconciliation copilot is advisory (BRD Section 9: it cannot post or
    # write off); a mismatch raises an exception case for a human, and a
    # fault in the copilot itself must not undo a correctly tied-out posting.
    try:
        check_reconciliation(batch)
    except Exception:
        logger.exception("Reconciliation check failed for JournalBatch %s", batch.id)

    return batch


def create_reversal_journal(original_batch, posted_by=None):
    """Contra-posts every line of a posted batch (restatement / correction)."""

    entries = [
        {
            "account_name": entry.account_name,
            "account_key": entry.account_key,
            "gl_code": entry.gl_code,
            "entry_type": (
                JournalEntryType.CREDIT
                if entry.entry_type == JournalEntryType.DEBIT
                else JournalEntryType.DEBIT
            ),
            "amount": entry.amount,
        }
        for entry in original_batch.entries.all()
    ]
    return _post_batch(
        run=None,
        pool=original_batch.pool,
        tenant=original_batch.tenant,
        batch_date=original_batch.batch_date,
        entries=entries,
        posted_by=posted_by,
        reverses_batch=original_batch,
    )


def verify_distribution_ties_out(run):
    """Reserves-free tie-out for an investment distribution: manager + investors + residual = result."""

    lines_total = sum((line.allocated_amount for line in run.lines.all()), ZERO)
    components = Decimal(run.manager_share) + lines_total + Decimal(run.rounding_residual)
    if components != Decimal(run.distributable_amount):
        raise JournalIntegrityError(
            f"Distribution does not tie out: manager share + investor lines + rounding residual = {components}, "
            f"distributable = {run.distributable_amount}."
        )
    tolerance = Decimal("0.01") * (run.lines.count() + 2)
    if abs(Decimal(run.rounding_residual)) > tolerance:
        raise JournalIntegrityError(
            f"Rounding residual {run.rounding_residual} exceeds the permitted tolerance {tolerance}."
        )


def build_distribution_entries(run):
    """
    Same two-leg shape as an allocation run: (1) recognise the period result,
    (2) clear it to the manager's share, the investors' payable and - only for
    what rounding leaves over - the disclosed rounding account. A loss debits
    the investors' account (capital absorbs it); the manager line is zero.
    """

    distributable = Decimal(run.distributable_amount)
    investors_total = sum((line.allocated_amount for line in run.lines.all()), ZERO)
    chart = ChartResolver(run.tenant_id, run.pool)
    entries = []

    _add(entries, chart, "pool_income", JournalEntryType.DEBIT, run.gross_income)
    _add(entries, chart, "pool_direct_expense", JournalEntryType.CREDIT, run.direct_expenses)
    _add_signed_credit(entries, chart, "distributable_profit", distributable)

    _add_signed_credit(entries, chart, "distributable_profit", -distributable)
    _add_signed_credit(entries, chart, "mudarib_payable", run.manager_share)
    _add_signed_credit(entries, chart, "investor_profit_payable", investors_total, run.pool.code)
    _add_signed_credit(entries, chart, "rounding_account", run.rounding_residual)
    return entries


def create_journal_from_distribution(run, posted_by=None):
    verify_distribution_ties_out(run)
    return _post_batch(
        run=None,
        investment_run=run,
        pool=run.pool,
        tenant=run.tenant,
        batch_date=run.period_end,
        entries=build_distribution_entries(run),
        posted_by=posted_by,
    )


def post_capital_movement_journal(*, kind, tenant, pool, amount, on_date, posted_by=None):
    """
    Capital account postings (BRD Section 10):
      subscription: Dr Settlement Receivable / Cr Investor Capital
      redemption:   Dr Investor Capital      / Cr Redemption Payable
    """

    chart = ChartResolver(tenant.id, pool)
    if kind == "subscription":
        debit, credit = ("settlement_receivable", ""), ("investor_capital", pool.code)
    elif kind == "redemption":
        debit, credit = ("investor_capital", pool.code), ("redemption_payable", "")
    else:
        raise ValueError(f"Unknown capital movement '{kind}'.")

    entries = []
    _add(entries, chart, debit[0], JournalEntryType.DEBIT, amount, debit[1])
    _add(entries, chart, credit[0], JournalEntryType.CREDIT, amount, credit[1])
    return _post_batch(
        run=None, pool=pool, tenant=tenant, batch_date=on_date, entries=entries, posted_by=posted_by
    )


def post_adjustment_journal(*, tenant, pool, on_date, posted_by, debits, credits):
    """
    Posts a balanced journal from logical-account lines: `debits` / `credits` are lists of
    (account_key, amount, suffix). Used for provisions, write-offs and recoveries.
    """

    chart = ChartResolver(tenant.id, pool)
    entries = []
    for key, amount, suffix in debits:
        _add(entries, chart, key, JournalEntryType.DEBIT, amount, suffix)
    for key, amount, suffix in credits:
        _add(entries, chart, key, JournalEntryType.CREDIT, amount, suffix)
    return _post_batch(
        run=None, pool=pool, tenant=tenant, batch_date=on_date, entries=entries, posted_by=posted_by
    )
