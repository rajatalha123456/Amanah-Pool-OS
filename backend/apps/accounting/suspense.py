"""
Suspense (BRD 4 accounting subledger, 6.2 "reconcile assets, sources, pool equity and suspense", 10 "the platform never
silently balances through suspense", 13 finance dashboard).

An amount that cannot be placed yet is parked in the pool's suspense account as a named item, never as an anonymous
plug: who proposed it, why, how much, against which account, and from which reconciliation.

- unidentified receipt: money arrived but its owner is not known yet   -> Dr counter account (cash) / Cr suspense
- unexplained shortfall: money is missing and the reason is not known -> Dr suspense / Cr counter account (cash)

Opening and clearing are each proposed by a finance maker and approved by a different finance checker; the journal is
posted only on approval. Clearing moves the amount to the account it really belongs to. The suspense ledger balance must
always equal the open items (`ageing()`), and a period cannot close while an item is older than the allowed age.
"""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action

from .chart import ACCOUNTS
from .models import JournalBatchStatus, JournalEntry, JournalEntryType, SuspenseItem, SuspenseSide, SuspenseStatus
from .services import post_adjustment_journal

SUSPENSE_KEY = "suspense"
DEFAULT_MAX_AGE_DAYS = 30
OUTSTANDING = (SuspenseStatus.OPEN, SuspenseStatus.CLEARING_PROPOSED)


def _assert_account(key, label):
    if key not in ACCOUNTS or key == SUSPENSE_KEY:
        raise ValidationError({label: [f"Choose one of the pool accounts (not suspense): {key!r} is not one."]})


def _different(user, other_id, what):
    if other_id == user.id:
        raise ValidationError(f"{what} must be approved by a different person than the one who proposed it.")


def propose_open(*, pool, side, amount, description, user, counter_account_key="pool_cash", reference="",
                 opened_on=None, reconciliation_batch=None, request=None):
    from apps.pools.period_lock import assert_period_open

    amount = Decimal(str(amount or 0))
    if amount <= 0:
        raise ValidationError({"amount": ["The amount must be greater than zero."]})
    if side not in SuspenseSide.values:
        raise ValidationError({"side": [f"One of {', '.join(SuspenseSide.values)}."]})
    if not (description or "").strip():
        raise ValidationError({"description": ["Say what is known about the amount."]})
    _assert_account(counter_account_key, "counter_account_key")
    opened_on = opened_on or timezone.localdate()
    if isinstance(opened_on, str):
        opened_on = date.fromisoformat(opened_on)
    assert_period_open(pool, opened_on, what="a suspense item")
    item = SuspenseItem.objects.create(
        tenant=pool.tenant, pool=pool, side=side, amount=amount, description=description.strip(), reference=reference or "",
        counter_account_key=counter_account_key, opened_on=opened_on, reconciliation_batch=reconciliation_batch,
        proposed_by=user,
    )
    log_action(tenant=pool.tenant, actor=user, action="suspense_proposed", model_name="SuspenseItem", object_id=str(item.id),
               changes={"side": side, "amount": str(amount), "counter": counter_account_key}, reason=item.description,
               request=request)
    return item


def approve_open(item, user, request=None):
    if item.status != SuspenseStatus.PROPOSED:
        raise ValidationError(f"Only a proposed item can be opened (status: {item.status}).")
    _different(user, item.proposed_by_id, "Parking an amount in suspense")
    if item.side == SuspenseSide.UNIDENTIFIED_RECEIPT:
        debits, credits = [(item.counter_account_key, item.amount, "")], [(SUSPENSE_KEY, item.amount, "")]
    else:
        debits, credits = [(SUSPENSE_KEY, item.amount, "")], [(item.counter_account_key, item.amount, "")]
    with transaction.atomic():
        batch = post_adjustment_journal(tenant=item.tenant, pool=item.pool, on_date=item.opened_on, posted_by=user,
                                        debits=debits, credits=credits)
        item.status, item.opened_by, item.opened_at, item.opening_journal = SuspenseStatus.OPEN, user, timezone.now(), batch
        item.save(update_fields=["status", "opened_by", "opened_at", "opening_journal", "updated_at"])
    log_action(tenant=item.tenant, actor=user, action="suspense_opened", model_name="SuspenseItem", object_id=str(item.id),
               changes={"journal_batch_id": str(batch.id)}, request=request)
    return item


def reject_open(item, user, reason, request=None):
    if item.status != SuspenseStatus.PROPOSED:
        raise ValidationError(f"Only a proposed item can be rejected (status: {item.status}).")
    if not (reason or "").strip():
        raise ValidationError({"reason": ["Say why."]})
    _different(user, item.proposed_by_id, "The decision")
    item.status, item.decision_note = SuspenseStatus.REJECTED, reason.strip()
    item.save(update_fields=["status", "decision_note", "updated_at"])
    log_action(tenant=item.tenant, actor=user, action="suspense_rejected", model_name="SuspenseItem", object_id=str(item.id),
               reason=reason, request=request)
    return item


def propose_clear(item, user, target_account_key, reason, request=None):
    if item.status != SuspenseStatus.OPEN:
        raise ValidationError(f"Only an open item can be cleared (status: {item.status}).")
    _assert_account(target_account_key, "target_account_key")
    if not (reason or "").strip():
        raise ValidationError({"reason": ["Say where the amount belongs and how that was established."]})
    item.status, item.clear_account_key, item.clear_reason = SuspenseStatus.CLEARING_PROPOSED, target_account_key, reason.strip()
    item.clear_proposed_by = user
    item.save(update_fields=["status", "clear_account_key", "clear_reason", "clear_proposed_by", "updated_at"])
    log_action(tenant=item.tenant, actor=user, action="suspense_clearing_proposed", model_name="SuspenseItem",
               object_id=str(item.id), changes={"target": target_account_key}, reason=reason, request=request)
    return item


def approve_clear(item, user, request=None):
    from apps.pools.period_lock import assert_period_open

    if item.status != SuspenseStatus.CLEARING_PROPOSED:
        raise ValidationError(f"There is no clearing awaiting approval (status: {item.status}).")
    _different(user, item.clear_proposed_by_id, "Clearing a suspense item")
    on = timezone.localdate()
    assert_period_open(item.pool, on, what="a suspense clearing")
    if item.side == SuspenseSide.UNIDENTIFIED_RECEIPT:
        debits, credits = [(SUSPENSE_KEY, item.amount, "")], [(item.clear_account_key, item.amount, "")]
    else:
        debits, credits = [(item.clear_account_key, item.amount, "")], [(SUSPENSE_KEY, item.amount, "")]
    with transaction.atomic():
        batch = post_adjustment_journal(tenant=item.tenant, pool=item.pool, on_date=on, posted_by=user,
                                        debits=debits, credits=credits)
        item.status, item.cleared_by, item.cleared_on, item.clearing_journal = SuspenseStatus.CLEARED, user, on, batch
        item.save(update_fields=["status", "cleared_by", "cleared_on", "clearing_journal", "updated_at"])
    log_action(tenant=item.tenant, actor=user, action="suspense_cleared", model_name="SuspenseItem", object_id=str(item.id),
               changes={"journal_batch_id": str(batch.id), "target": item.clear_account_key}, request=request)
    return item


def reject_clear(item, user, reason, request=None):
    if item.status != SuspenseStatus.CLEARING_PROPOSED:
        raise ValidationError(f"There is no clearing awaiting approval (status: {item.status}).")
    if not (reason or "").strip():
        raise ValidationError({"reason": ["Say why."]})
    _different(user, item.clear_proposed_by_id, "The decision")
    item.status, item.decision_note = SuspenseStatus.OPEN, reason.strip()
    item.clear_account_key, item.clear_reason, item.clear_proposed_by = "", "", None
    item.save(update_fields=["status", "decision_note", "clear_account_key", "clear_reason", "clear_proposed_by", "updated_at"])
    log_action(tenant=item.tenant, actor=user, action="suspense_clearing_rejected", model_name="SuspenseItem",
               object_id=str(item.id), reason=reason, request=request)
    return item


def max_age_days(pool):
    from apps.pools.config_snapshot import bound_rule_pack

    pack = bound_rule_pack(pool)
    value = (pack.rules_config or {}).get("suspense_max_age_days") if pack else None
    return int(value) if value not in (None, "") else DEFAULT_MAX_AGE_DAYS


def _signed(item):
    """Credit-positive: an unidentified receipt is a credit on suspense, a shortfall a debit."""
    return item.amount if item.side == SuspenseSide.UNIDENTIFIED_RECEIPT else -item.amount


def ledger_balance(pool, as_of=None):
    """Credit minus debit on the pool's suspense account, from posted journals."""
    entries = JournalEntry._base_manager.filter(
        tenant_id=pool.tenant_id, batch__pool=pool, batch__status=JournalBatchStatus.POSTED, account_key=SUSPENSE_KEY
    )
    if as_of:
        entries = entries.filter(batch__batch_date__lte=as_of)
    credit = entries.filter(entry_type=JournalEntryType.CREDIT).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    debit = entries.filter(entry_type=JournalEntryType.DEBIT).aggregate(s=Sum("amount"))["s"] or Decimal("0")
    return credit - debit


def ageing(pool, as_of=None):
    """Open items by age, the suspense ledger balance, and whether every amount in suspense is a named item."""
    as_of = as_of or timezone.localdate()
    if isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)
    limit = max_age_days(pool)
    buckets = {"0-30": Decimal("0"), "31-60": Decimal("0"), "61-90": Decimal("0"), "over 90": Decimal("0")}
    rows, net, overdue = [], Decimal("0"), 0
    items = SuspenseItem._base_manager.filter(
        tenant_id=pool.tenant_id, pool=pool, status__in=OUTSTANDING, opened_on__lte=as_of
    ).order_by("opened_on")
    for item in items:
        age = (as_of - item.opened_on).days
        bucket = "0-30" if age <= 30 else "31-60" if age <= 60 else "61-90" if age <= 90 else "over 90"
        buckets[bucket] += item.amount
        net += _signed(item)
        overdue += 1 if age > limit else 0
        rows.append({"id": str(item.id), "age_days": age, "bucket": bucket, "overdue": age > limit})
    balance = ledger_balance(pool, as_of)
    return {
        "pool": pool.code, "as_of": str(as_of), "max_age_days": limit, "open_items": len(rows), "overdue_items": overdue,
        "buckets": {k: str(v) for k, v in buckets.items()}, "items_net": str(net), "ledger_balance": str(balance),
        "itemized": balance == net, "items": rows,
    }
