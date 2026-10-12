"""Negligence cases in loss allocation (BR-006 / BRD 6.4)."""

from decimal import Decimal

from django.db.models import Q

from .models import NegligenceCase, NegligenceCaseStatus


def _overlapping(pool, start, end):
    return NegligenceCase._base_manager.filter(
        tenant_id=pool.tenant_id, pool=pool, period_start__lte=end, period_end__gte=start
    )


def open_cases(pool, start, end):
    """Cases still under investigation that concern any part of [start, end]."""

    return list(_overlapping(pool, start, end).filter(status=NegligenceCaseStatus.OPEN))


def liable_cases(pool, start, end, replaces_run=None):
    """
    Determined-liable cases covering the period whose amount has not yet been applied to a signed
    run. A restatement may re-use cases applied to the run it replaces.
    """

    available = Q(applied_run__isnull=True)
    if replaces_run is not None:
        available |= Q(applied_run=replaces_run)
    return list(_overlapping(pool, start, end).filter(status=NegligenceCaseStatus.LIABLE).filter(available))


def liability_total(cases, loss_abs):
    """Manager-borne amount: the sum of determined liabilities, never more than the loss itself."""

    total = sum((Decimal(case.liability_amount or 0) for case in cases), Decimal("0"))
    return min(total, Decimal(loss_abs))
