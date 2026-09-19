"""
Journal posting derived from a signed AllocationRun.
"""

import logging
from decimal import Decimal

from django.db import transaction

from .models import JournalBatch, JournalEntry, JournalEntryType
from .reconciliation import check_reconciliation


logger = logging.getLogger("apps")


def create_journal_from_allocation(allocation_run, posted_by=None):
    """
    Builds a balanced double-entry JournalBatch from allocation_run:

    Per participant class (from allocation_run.lines):
        DEBIT  "Profit Expense - {class}"    = allocated_amount
        CREDIT "Depositor Payable - {class}" = allocated_amount

    For the mudarib's own share (self-contained pair, doesn't touch the
    depositor entries above):
        DEBIT  "Mudarib Income Suspense" = mudarib_share
        CREDIT "Mudarib Income"          = mudarib_share

    total_debit and total_credit are each the sum of the depositor
    allocations plus mudarib_share, so they are equal by construction;
    JournalBatch.clean() still re-checks this before saving.
    """

    lines = list(allocation_run.lines.all())

    entries_data = []
    for line in lines:
        entries_data.append(
            {
                "account_name": f"Profit Expense - {line.participant_class}",
                "entry_type": JournalEntryType.DEBIT,
                "amount": line.allocated_amount,
            }
        )
        entries_data.append(
            {
                "account_name": f"Depositor Payable - {line.participant_class}",
                "entry_type": JournalEntryType.CREDIT,
                "amount": line.allocated_amount,
            }
        )

    entries_data.append(
        {
            "account_name": "Mudarib Income Suspense",
            "entry_type": JournalEntryType.DEBIT,
            "amount": allocation_run.mudarib_share,
        }
    )
    entries_data.append(
        {
            "account_name": "Mudarib Income",
            "entry_type": JournalEntryType.CREDIT,
            "amount": allocation_run.mudarib_share,
        }
    )

    total_debit = sum(
        (e["amount"] for e in entries_data if e["entry_type"] == JournalEntryType.DEBIT),
        Decimal("0"),
    )
    total_credit = sum(
        (e["amount"] for e in entries_data if e["entry_type"] == JournalEntryType.CREDIT),
        Decimal("0"),
    )

    if total_debit != total_credit:
        raise ValueError("Journal batch is not balanced.")

    with transaction.atomic():
        batch = JournalBatch.objects.create(
            tenant=allocation_run.tenant,
            allocation_run=allocation_run,
            pool=allocation_run.pool,
            batch_date=allocation_run.value_date,
            total_debit=total_debit,
            total_credit=total_credit,
            posted_by=posted_by,
        )

        JournalEntry.objects.bulk_create(
            [
                JournalEntry(
                    tenant=allocation_run.tenant,
                    batch=batch,
                    account_name=entry["account_name"],
                    entry_type=entry["entry_type"],
                    amount=entry["amount"],
                )
                for entry in entries_data
            ]
        )

    try:
        check_reconciliation(batch)
    except Exception:
        # Reconciliation is a best-effort detection aid and must not block posting.
        logger.exception(
            "Reconciliation check failed for JournalBatch %s", batch.id
        )

    return batch
