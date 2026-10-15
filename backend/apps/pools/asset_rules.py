"""Asset eligibility and effective-dated transfer rules for asset-backed pools."""

from datetime import timedelta

from rest_framework.exceptions import ValidationError

from .models import AssetAssignment, AssetStatus
from .period_lock import assert_period_open

HOLDING_STATUSES = ("draft", "pending_approval", "approved", "open", "allocation")


def assert_asset_eligible(asset, pool, on_date):
    """The asset may be placed in `pool` from `on_date`, or a ValidationError explains why not."""
    if asset.status in (AssetStatus.MATURED, AssetStatus.WRITTEN_OFF):
        raise ValidationError({"asset": f"A {asset.status.replace('_', ' ')} asset cannot be assigned to a pool."})
    if asset.maturity_date and asset.maturity_date <= on_date:
        raise ValidationError({"assigned_date": "The asset has matured on or before the assignment date."})
    if pool.status not in HOLDING_STATUSES:
        raise ValidationError({"pool": f"A {pool.status} pool cannot receive assets."})
    eligible = pool.product.eligible_asset_types or []
    if eligible and asset.asset_type not in eligible:
        raise ValidationError(
            {
                "asset": f"{asset.asset_type} assets are not eligible for product {pool.product.code}; "
                f"eligible types: {', '.join(eligible)}."
            }
        )
    assert_period_open(pool, on_date)


def request_transfer(assignment, to_pool, effective_date, reason, valuation, valuation_basis, user):
    """A proposed transfer, fully validated now (and again on approval); nothing moves yet."""
    from decimal import Decimal, InvalidOperation

    from .models import AssetTransferRequest, AssetTransferStatus

    try:
        valuation = Decimal(str(valuation))
    except (InvalidOperation, TypeError):
        valuation = Decimal("0")
    if valuation <= 0:
        raise ValidationError({"valuation": ["The value of the asset at the transfer date is required (greater than zero)."]})
    if not (valuation_basis or "").strip():
        raise ValidationError({"valuation_basis": ["Say how the value was established (valuer, report or market source)."]})
    if assignment.unassigned_date is not None:
        raise ValidationError("Only a current assignment can be transferred.")
    if not (reason or "").strip():
        raise ValidationError({"reason": ["A transfer reason is required."]})
    if to_pool.id == assignment.pool_id:
        raise ValidationError({"to_pool": ["The asset is already in this pool."]})
    if effective_date <= assignment.assigned_date:
        raise ValidationError({"effective_date": ["The transfer must take effect after the current assignment began."]})
    assert_asset_eligible(assignment.asset, to_pool, effective_date)
    assert_period_open(assignment.pool, effective_date)
    if AssetTransferRequest.objects.filter(assignment=assignment, status=AssetTransferStatus.PENDING).exists():
        raise ValidationError("A transfer of this asset is already awaiting approval.")
    return AssetTransferRequest.objects.create(
        tenant=assignment.tenant, assignment=assignment, to_pool=to_pool, effective_date=effective_date,
        reason=reason.strip(), valuation=valuation, valuation_basis=valuation_basis.strip(), requested_by=user,
    )


def approve_transfer(request_obj, user):
    """A different person approves; the transfer is performed and the valuation recorded on the new assignment."""
    from django.db import transaction
    from django.utils import timezone

    from .models import AssetTransferRequest, AssetTransferStatus

    with transaction.atomic():
        req = AssetTransferRequest.objects.select_for_update().get(pk=request_obj.pk)
        if req.status != AssetTransferStatus.PENDING:
            raise ValidationError(f"This transfer is already {req.status}.")
        if req.requested_by_id == user.id:
            raise ValidationError("Four-eyes rule: the person who requested a transfer cannot approve it.")
        new = transfer_asset(req.assignment, req.to_pool, req.effective_date, req.reason, req.requested_by)
        new.transfer_valuation, new.transfer_valuation_basis = req.valuation, req.valuation_basis
        new.save(update_fields=["transfer_valuation", "transfer_valuation_basis", "updated_at"])
        req.status, req.decided_by, req.decided_at, req.new_assignment = AssetTransferStatus.APPROVED, user, timezone.now(), new
        req.save(update_fields=["status", "decided_by", "decided_at", "new_assignment", "updated_at"])
    return req


def reject_transfer(request_obj, user, reason):
    from django.utils import timezone

    from .models import AssetTransferStatus

    if request_obj.status != AssetTransferStatus.PENDING:
        raise ValidationError(f"This transfer is already {request_obj.status}.")
    if not (reason or "").strip():
        raise ValidationError({"reason": ["Say why the transfer is refused."]})
    if request_obj.requested_by_id == user.id:
        raise ValidationError("Four-eyes rule: the person who requested a transfer cannot decide it.")
    request_obj.status, request_obj.decided_by = AssetTransferStatus.REJECTED, user
    request_obj.decided_at, request_obj.decision_note = timezone.now(), reason.strip()
    request_obj.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
    return request_obj


def transfer_asset(assignment, to_pool, effective_date, reason, user):
    """
    Move a held asset to another pool with effect from `effective_date`: the old assignment ends the
    day before and a new one starts on it, so no day is double counted or lost. Both pools' periods
    must be open for that date.
    """
    if assignment.unassigned_date is not None:
        raise ValidationError("Only a current assignment can be transferred.")
    if not reason.strip():
        raise ValidationError({"reason": ["A transfer reason is required."]})
    if to_pool.id == assignment.pool_id:
        raise ValidationError({"to_pool": ["The asset is already in this pool."]})
    if effective_date <= assignment.assigned_date:
        raise ValidationError({"effective_date": ["The transfer must take effect after the current assignment began."]})

    assert_asset_eligible(assignment.asset, to_pool, effective_date)
    assert_period_open(assignment.pool, effective_date)

    assignment.unassigned_date = effective_date - timedelta(days=1)
    assignment.save(update_fields=["unassigned_date", "updated_at"])
    return AssetAssignment.objects.create(
        tenant=assignment.tenant, asset=assignment.asset, pool=to_pool, assigned_date=effective_date,
        assigned_by=user, transfer_reason=reason, transferred_from=assignment,
    )
