"""
Journal posting derived from a signed AllocationRun.

Account names used by the pool sub-ledger (illustrative chart, to be mapped
to the enterprise GL per jurisdiction - BRD Section 10):

    Pool Income                    gross income recognised for the period
    Pool Direct Expense            approved direct pool expenses
    Pool Distributable Profit      clearing account for the period result
    PER Reserve / IRR Reserve      reserve appropriations
    Mudarib Share Payable          manager (Mudarib) share
    Depositor Payable - {class}    participant profit (or loss absorbed)
    Pool Rounding Account          disclosed rounding residual
"""

import logging
from decimal import Decimal

from django.db import transaction

from .models import JournalBatch, JournalBatchStatus, JournalEntry, JournalEntryType
from .reconciliation import check_reconciliation

logger = logging.getLogger("apps")

ZERO = Decimal("0.00")

POOL_INCOME = "Pool Income"
POOL_DIRECT_EXPENSE = "Pool Direct Expense"
POOL_DISTRIBUTABLE_PROFIT = "Pool Distributable Profit"
PER_RESERVE = "PER Reserve"
IRR_RESERVE = "IRR Reserve"
MUDARIB_PAYABLE = "Mudarib Share Payable"
ROUNDING_ACCOUNT = "Pool Rounding Account"


class JournalIntegrityError(ValueError):
    """Raised when an allocation run cannot be posted as a balanced, tied-out journal."""


def _add(entries, account_name, entry_type, amount):
    amount = Decimal(amount)
    if amount == 0:
        return
    entries.append({"account_name": account_name, "entry_type": entry_type, "amount": amount})


def _add_signed_credit(entries, account_name, signed_credit):
    """Positive amount credits the account, negative amount debits it."""
    signed_credit = Decimal(signed_credit)
    if signed_credit >= 0:
        _add(entries, account_name, JournalEntryType.CREDIT, signed_credit)
    else:
        _add(entries, account_name, JournalEntryType.DEBIT, -signed_credit)


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
    entries = []

    # Leg 1 - recognise the period result.
    _add(entries, POOL_INCOME, JournalEntryType.DEBIT, allocation_run.gross_income)
    _add(entries, POOL_DIRECT_EXPENSE, JournalEntryType.CREDIT, allocation_run.direct_expenses)
    _add_signed_credit(entries, POOL_DISTRIBUTABLE_PROFIT, distributable)

    # Leg 2 - appropriate the result.
    _add_signed_credit(entries, POOL_DISTRIBUTABLE_PROFIT, -distributable)
    _add_signed_credit(entries, PER_RESERVE, allocation_run.per_amount)
    _add_signed_credit(entries, IRR_RESERVE, allocation_run.irr_amount)
    _add_signed_credit(entries, MUDARIB_PAYABLE, allocation_run.mudarib_share)
    for line in lines:
        _add_signed_credit(entries, f"Depositor Payable - {line.participant_class}", line.allocated_amount)
    _add_signed_credit(entries, ROUNDING_ACCOUNT, allocation_run.rounding_residual)

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


def _post_batch(*, run, pool, tenant, batch_date, entries, posted_by, reverses_batch=None):
    total_debit, total_credit = _totals(entries)
    if total_debit != total_credit:
        raise JournalIntegrityError("Journal batch is not balanced.")

    with transaction.atomic():
        batch = JournalBatch.objects.create(
            tenant=tenant,
            allocation_run=run,
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
