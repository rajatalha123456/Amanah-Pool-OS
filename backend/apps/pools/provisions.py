"""
Asset provisions, write-offs and recoveries (BRD 6.4 loss & impairment, Section 10 accounting).

Every entry is maker-checker: a finance maker records it, a different finance checker approves it.
Approval is what posts the journal and (for amounts that hit pool profit) the income/expense event
that the next allocation run derives its profit from (BR-005). Approved entries are immutable.

  provision:  Dr Provision Expense        / Cr Provision Reserve
  release:    Dr Provision Reserve        / Cr Provision Expense      (income event)
  write_off:  Dr Provision Reserve (used) + Dr Provision Expense (excess) / Cr Asset Portfolio
  recovery:   Dr Pool Cash                / Cr Recovery Income        (only on a written-off asset)
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounting.models import (
    IncomeExpenseEvent,
    IncomeExpenseEventStatus,
    IncomeExpenseEventType,
    JournalEntryType,
)
from apps.accounting.services import post_adjustment_journal

from .models import (
    Asset,
    AssetAssignment,
    AssetProvisionEntry,
    AssetProvisionStatus,
    AssetProvisionType,
    AssetStatus,
)
from .period_lock import assert_period_open

T = AssetProvisionType
APPROVED = AssetProvisionStatus.APPROVED
ZERO = Decimal("0.00")


def _sum(asset, entry_type, field="amount"):
    rows = AssetProvisionEntry._base_manager.filter(
        tenant_id=asset.tenant_id, asset=asset, entry_type=entry_type, status=APPROVED
    ).values_list(field, flat=True)
    return sum((Decimal(v) for v in rows), ZERO)


def asset_position(asset):
    """Approved-entry balances of one asset."""
    provided, released = _sum(asset, T.PROVISION), _sum(asset, T.RELEASE)
    utilised = _sum(asset, T.WRITE_OFF, "provision_utilised")
    written_off, recovered = _sum(asset, T.WRITE_OFF), _sum(asset, T.RECOVERY)
    return {
        "face_value": asset.face_value,
        "provision_balance": provided - released - utilised,
        "written_off": written_off,
        "recovered": recovered,
        "exposure": asset.face_value - written_off,
        "recoverable_balance": written_off - recovered,
    }


def validate_entry(asset, entry_type, amount, effective_date):
    """Pure checks at creation time (re-run at approval, since other entries may have landed)."""
    if amount <= 0:
        raise ValidationError({"amount": ["The amount must be positive."]})
    pos = asset_position(asset)
    if entry_type == T.PROVISION and amount > pos["exposure"] - pos["provision_balance"]:
        raise ValidationError({"amount": ["Provisions cannot exceed the asset's remaining exposure."]})
    if entry_type == T.RELEASE and amount > pos["provision_balance"]:
        raise ValidationError({"amount": ["Cannot release more than the current provision balance."]})
    if entry_type == T.WRITE_OFF and amount > pos["exposure"]:
        raise ValidationError({"amount": ["Cannot write off more than the remaining exposure."]})
    if entry_type == T.RECOVERY and amount > pos["recoverable_balance"]:
        raise ValidationError({"amount": ["Recovery cannot exceed what was written off and not yet recovered."]})


def holding_pool(asset, on_date):
    """The pool that held the asset on `on_date` (a recovery may follow the write-off's unassignment)."""
    assignments = AssetAssignment._base_manager.filter(tenant_id=asset.tenant_id, asset=asset)
    held = [
        a for a in assignments.order_by("-assigned_date")
        if a.assigned_date <= on_date and (a.unassigned_date is None or a.unassigned_date >= on_date)
    ]
    if held:
        return held[0].pool
    latest = assignments.order_by("-assigned_date").select_related("pool").first()
    if latest is None:
        raise ValidationError({"asset": ["The asset has never been assigned to a pool."]})
    return latest.pool


def create_entry(*, asset, entry_type, amount, effective_date, reason, user):
    if not reason.strip():
        raise ValidationError({"reason": ["A reason is required."]})
    pool = holding_pool(asset, effective_date)
    assert_period_open(pool, effective_date)
    if entry_type in (T.PROVISION, T.RELEASE, T.WRITE_OFF) and asset.status == AssetStatus.WRITTEN_OFF:
        raise ValidationError({"asset": ["The asset is already fully written off."]})
    validate_entry(asset, entry_type, amount, effective_date)
    return AssetProvisionEntry.objects.create(
        tenant=asset.tenant, asset=asset, pool=pool, entry_type=entry_type, amount=amount,
        effective_date=effective_date, reason=reason, created_by=user,
    )


def _event(entry, event_type, category, amount):
    if amount <= 0:
        return None
    return IncomeExpenseEvent.objects.create(
        tenant=entry.tenant, pool=entry.pool, event_type=event_type, category=category, amount=amount,
        event_date=entry.effective_date, status=IncomeExpenseEventStatus.POSTED,
        description=f"{category}: {entry.asset.reference_code} ({entry.reason})",
        created_by=entry.created_by, posted_by=entry.approved_by, posted_at=entry.approved_at,
    )


@transaction.atomic
def approve_entry(entry, checker):
    entry = AssetProvisionEntry._base_manager.select_for_update().get(pk=entry.pk)
    if entry.status != AssetProvisionStatus.PENDING:
        raise ValidationError(f"Only a pending entry can be approved (this one is {entry.status}).")
    if entry.created_by_id == checker.id:
        raise ValidationError("Four-eyes rule: the maker cannot approve their own entry.")
    asset = Asset._base_manager.select_for_update().get(pk=entry.asset_id)
    assert_period_open(entry.pool, entry.effective_date)
    validate_entry(asset, entry.entry_type, entry.amount, entry.effective_date)

    amount, pos = entry.amount, asset_position(asset)
    e_type, debit, credit = entry.entry_type, [], []
    expense_amount = income_amount = ZERO
    if e_type == T.PROVISION:
        debit, credit = [("provision_expense", amount)], [("provision_reserve", amount)]
        expense_amount = amount
    elif e_type == T.RELEASE:
        debit, credit = [("provision_reserve", amount)], [("provision_expense", amount)]
        income_amount = amount
    elif e_type == T.WRITE_OFF:
        utilised = min(amount, pos["provision_balance"])
        expense_amount = amount - utilised
        entry.provision_utilised = utilised
        debit = [("provision_reserve", utilised), ("provision_expense", expense_amount)]
        credit = [("asset_portfolio", amount)]
    else:
        debit, credit = [("pool_cash", amount)], [("recovery_income", amount)]
        income_amount = amount

    entry.status = AssetProvisionStatus.APPROVED
    entry.approved_by = checker
    entry.approved_at = timezone.now()
    entry.journal_batch = post_adjustment_journal(
        tenant=entry.tenant, pool=entry.pool, on_date=entry.effective_date, posted_by=checker,
        debits=[(k, v, asset.reference_code) for k, v in debit if v > 0],
        credits=[(k, v, asset.reference_code) for k, v in credit if v > 0],
    )
    label = {
        T.PROVISION: "Asset provision", T.RELEASE: "Provision release",
        T.WRITE_OFF: "Asset write-off", T.RECOVERY: "Recovery of written-off asset",
    }[e_type]
    entry.income_expense_event = (
        _event(entry, IncomeExpenseEventType.EXPENSE, label, expense_amount)
        or _event(entry, IncomeExpenseEventType.INCOME, label, income_amount)
    )
    entry.save()

    if e_type == T.WRITE_OFF and asset.face_value - (pos["written_off"] + amount) <= 0:
        asset.status = AssetStatus.WRITTEN_OFF
        asset.save(update_fields=["status", "updated_at"])
        AssetAssignment._base_manager.filter(asset=asset, unassigned_date__isnull=True).update(
            unassigned_date=entry.effective_date
        )
    return entry


def reject_entry(entry, checker, reason):
    if entry.status != AssetProvisionStatus.PENDING:
        raise ValidationError(f"Only a pending entry can be rejected (this one is {entry.status}).")
    if not reason.strip():
        raise ValidationError({"reason": ["A rejection reason is required."]})
    entry.status = AssetProvisionStatus.REJECTED
    entry.approved_by = checker
    entry.approved_at = timezone.now()
    entry.rejection_reason = reason
    entry.save()
    return entry
