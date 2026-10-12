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
