"""
Sub-ledger to GL check for a posted allocation journal (BRD Section 10: "pool sub-ledger entries reconcile
to the enterprise GL").

The participant sub-ledger of a run is its allocation lines; the GL carries one depositor-payable control
account per participant class. After posting, the net credit to those control accounts in the batch must
equal the sum of the run's allocation lines. A difference means the GL and the sub-ledger have diverged and
raises an exception case for a person to investigate (this check never posts or corrects anything).

The earlier version compared cumulative depositor-payable credits (profit) with the latest daily balance
(deposits) - two unrelated figures - and raised a false exception after almost every run.
"""

from decimal import Decimal

from apps.ai_agents.models import is_ai_model_enabled
from apps.core.exceptions_helper import create_exception_case

from .models import JournalEntry, JournalEntryType

ZERO = Decimal("0.00")


def check_reconciliation(journal_batch):
    """Returns True when a mismatch was found (and an exception case raised)."""
    if not is_ai_model_enabled("reconciliation_copilot"):
        return False
    run = journal_batch.allocation_run
    if run is None:
        return False

    entries = JournalEntry._base_manager.filter(batch=journal_batch, account_key="depositor_payable")
    gl_net_credit = sum(
        (e.amount if e.entry_type == JournalEntryType.CREDIT else -e.amount for e in entries), ZERO
    )
    subledger_total = sum((line.allocated_amount for line in run.lines.all()), ZERO)
    difference = gl_net_credit - subledger_total
    if difference == 0:
        return False

    create_exception_case(
        tenant=journal_batch.tenant,
        source_module="accounting",
        source_object_id=str(journal_batch.id),
        pool=journal_batch.pool,
        severity="high",
        title=f"GL / sub-ledger mismatch on {journal_batch.pool.code} for {run.value_date}",
        description=(
            f"Depositor payable posted to the GL: {gl_net_credit}; participant sub-ledger (allocation lines): "
            f"{subledger_total}; difference {difference}."
        ),
        detected_by="system",
    )
    return True
