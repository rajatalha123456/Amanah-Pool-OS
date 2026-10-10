"""
Period-close enforcement (BRD 6.2 / 7.3).

A pool period whose close checklist is CERTIFIED or LOCKED accepts no new
imports, income/expense events or allocation runs. Back-dated work for such a
period must go through a formally approved restatement.
"""

from rest_framework.exceptions import ValidationError

from .models import PeriodCloseChecklist, PeriodCloseStatus

CLOSED_STATUSES = (PeriodCloseStatus.CERTIFIED, PeriodCloseStatus.LOCKED)


def get_closed_period(pool, on_date):
    return (
        PeriodCloseChecklist._base_manager.filter(
            tenant_id=pool.tenant_id,
            pool=pool,
            status__in=CLOSED_STATUSES,
            period_start__lte=on_date,
            period_end__gte=on_date,
        )
        .order_by("-period_end")
        .first()
    )


def assert_period_open(pool, on_date, what="record"):
    closed = get_closed_period(pool, on_date)
    if closed is not None:
        raise ValidationError(
            f"Cannot post {what} dated {on_date}: the period {closed.period_start} to "
            f"{closed.period_end} for pool '{pool.code}' is {closed.status}. "
            "Back-dated changes require an approved restatement."
        )
