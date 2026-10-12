"""
BR-003: a change affecting economics needs a simulation and a customer / regulatory notification.

Approving a new profit-sharing ratio or weightage band for a *live* pool (open or allocation) is such a
change. Before it is approved:
  * the effective date must respect the rule pack's `notice_period_days` (advance notice), and
  * its impact is simulated on the pool's last signed period and attached to the notice.
After approval, staff, participant portal users and participants with an email address are notified.
A pool that is not live yet (still being set up) is not affected - nobody is relying on its terms.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.notifications import events
from apps.pools.config_snapshot import bound_rule_pack
from apps.pools.models import PoolStatus

from .models import (
    AllocationRun,
    AllocationRunStatus,
    PSRStatus,
    ProfitSharingRatio,
    WeightageBand,
    WeightageBandStatus,
)

LIVE_STATUSES = (PoolStatus.OPEN, PoolStatus.ALLOCATION, PoolStatus.FROZEN)


def _money(value):
    return f"PKR {Decimal(value):,.2f}"


def _covering(queryset, day):
    return queryset.filter(effective_from__lte=day).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=day))


def notice_days_for(pool):
    pack = bound_rule_pack(pool)
    try:
        return int((pack.rules_config or {}).get("notice_period_days", 0)) if pack else 0
    except (TypeError, ValueError):
        return 0


def check_notice_period(pool, effective_from):
    """Raises ValidationError if the change is live-pool and gives less than the required notice."""

    if pool.status not in LIVE_STATUSES:
        return None
    days = notice_days_for(pool)
    earliest = timezone.localdate() + timedelta(days=days)
    if effective_from < earliest:
        raise ValidationError(
            f"This changes the economics of a live pool: the rule pack requires {days} days' notice, so the "
            f"effective date must be on or after {earliest} (it is {effective_from})."
        )
    return days


def _last_signed_run(pool):
    return (
        AllocationRun._base_manager.filter(tenant_id=pool.tenant_id, pool=pool, status=AllocationRunStatus.SIGNED)
        .order_by("-value_date")
        .first()
    )


def psr_impact(pool, new_psr):
    run = _last_signed_run(pool)
    current = _covering(
        ProfitSharingRatio._base_manager.filter(tenant_id=pool.tenant_id, pool=pool, status=PSRStatus.APPROVED)
        .exclude(pk=new_psr.pk),
        timezone.localdate(),
    ).first()
    ratio = f"{new_psr.depositor_share}/{new_psr.mudarib_share}"
    before = f" (was {current.depositor_share}/{current.mudarib_share})" if current else ""
    if run is None or current is None:
        return f"New ratio depositors/Mudarib {ratio}{before}; no signed period exists to simulate on."
    d = Decimal(run.distributable_amount)
    mud_before = d * Decimal(current.mudarib_share) / 100
    mud_after = d * Decimal(new_psr.mudarib_share) / 100
    return (
        f"On {run.effective_period_start} to {run.value_date} (distributable {_money(d)}) the Mudarib share would be "
        f"{_money(mud_after)} instead of {_money(mud_before)} and depositors would receive "
        f"{_money(d - mud_after)} instead of {_money(d - mud_before)}."
    )


def band_impact(pool, band):
    current = _covering(
        WeightageBand._base_manager.filter(
            tenant_id=pool.tenant_id, pool=pool, participant_class=band.participant_class,
            status=WeightageBandStatus.APPROVED,
        ).exclude(pk=band.pk),
        timezone.localdate(),
    ).first()
    before = f"{current.weightage}" if current else "none"
    return (
        f"Weightage for class '{band.participant_class}' changes from {before} to {band.weightage}; "
        "participants in this class earn a proportionally different share of distributable profit."
    )


def announce(pool, actor, *, summary, impact, effective_from, notice_days):
    events.economics_change(
        pool, actor, summary=summary, impact=impact, effective_from=effective_from, notice_days=notice_days
    )
