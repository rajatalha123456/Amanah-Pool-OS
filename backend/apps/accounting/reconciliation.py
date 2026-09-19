"""
High-level reconciliation check for a pool's posted depositor payable balance.
"""

from decimal import Decimal

from django.db.models import Sum

from apps.core.exceptions_helper import create_exception_case
from apps.ai_agents.models import is_ai_model_enabled
from apps.pools.models import DailyBalance

from .models import JournalBatchStatus, JournalEntry


MISMATCH_TOLERANCE = Decimal("5")
HIGH_SEVERITY_THRESHOLD = Decimal("15")


def check_reconciliation(journal_batch):
    """
    Compares posted depositor payables with the pool's latest DailyBalance
    snapshot. This is a simplified v1 sanity check, not line-by-line matching.
    """

    if not is_ai_model_enabled("reconciliation_copilot"):
        return False

    journal_total = (
        JournalEntry.objects.filter(
            account_name__startswith="Depositor Payable",
            entry_type="credit",
            batch__status=JournalBatchStatus.POSTED,
            batch__pool=journal_batch.pool,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )

    latest_date = (
        DailyBalance.objects.filter(pool=journal_batch.pool)
        .order_by("-value_date")
        .values_list("value_date", flat=True)
        .first()
    )
    snapshot_total = Decimal("0")
    if latest_date is not None:
        snapshot_total = (
            DailyBalance.objects.filter(
                pool=journal_batch.pool,
                value_date=latest_date,
            ).aggregate(total=Sum("balance_amount"))["total"]
            or Decimal("0")
        )

    difference = abs(journal_total - snapshot_total)
    if snapshot_total == 0:
        percentage_difference = Decimal("0") if journal_total == 0 else Decimal("100")
    else:
        percentage_difference = difference / abs(snapshot_total) * 100

    if percentage_difference <= MISMATCH_TOLERANCE:
        return False

    create_exception_case(
        tenant=journal_batch.tenant,
        source_module="accounting",
        source_object_id=str(journal_batch.id),
        pool=journal_batch.pool,
        severity=(
            "high"
            if percentage_difference > HIGH_SEVERITY_THRESHOLD
            else "medium"
        ),
        title=f"Reconciliation mismatch detected for {journal_batch.pool.code}",
        description=(
            f"Posted depositor payable total is {journal_total:.2f}; latest "
            f"DailyBalance snapshot total is {snapshot_total:.2f}; exact "
            f"percentage difference is {percentage_difference:.2f}%."
        ),
        detected_by="system",
    )
    return True