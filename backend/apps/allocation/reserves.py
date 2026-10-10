"""
Reserve (PER / IRR) balance movements driven by signed allocation runs.

A run's reserve appropriations are only *proposed* by the engine; the
reserve balances themselves change here, when the run is signed (or when a
signed run is reversed by a restatement), inside the caller's transaction.
"""

from decimal import Decimal

from .engine import reserve_headroom
from .models import ReservePolicy


def _policy_ids(run):
    reserves = (run.config_snapshot or {}).get("reserves") or {}
    return {
        kind: (reserves.get(kind) or {}).get("id")
        for kind in ("per", "irr")
    }


def _amounts(run):
    return {"per": Decimal(run.per_amount), "irr": Decimal(run.irr_amount)}


def apply_reserve_movements(run):
    """
    Adds the run's PER/IRR appropriations to the reserve balances, refusing
    if the cap has been reached since the run was simulated. Raises
    ValueError (caller turns it into a validation error); must run inside
    transaction.atomic().
    """

    total_funds = Decimal((run.config_snapshot or {}).get("total_daily_funds", "0"))
    for kind, policy_id in _policy_ids(run).items():
        amount = _amounts(run)[kind]
        if amount <= 0:
            continue
        if not policy_id:
            raise ValueError(f"Run carries a {kind.upper()} appropriation but no reserve policy snapshot.")

        policy = ReservePolicy._base_manager.select_for_update().get(pk=policy_id, tenant_id=run.tenant_id)
        headroom = reserve_headroom(policy, total_funds)
        if headroom is not None and amount > headroom:
            raise ValueError(
                f"{kind.upper()} appropriation {amount} exceeds the remaining reserve cap "
                f"headroom {headroom}; the reserve changed after this run was simulated - re-run it."
            )
        policy.current_balance = Decimal(policy.current_balance) + amount
        policy.save(update_fields=["current_balance", "updated_at"])


def reverse_reserve_movements(run):
    """Takes a reversed run's PER/IRR appropriations back out of the reserves."""

    for kind, policy_id in _policy_ids(run).items():
        amount = _amounts(run)[kind]
        if amount <= 0 or not policy_id:
            continue
        policy = ReservePolicy._base_manager.select_for_update().get(pk=policy_id, tenant_id=run.tenant_id)
        policy.current_balance = max(Decimal("0.00"), Decimal(policy.current_balance) - amount)
        policy.save(update_fields=["current_balance", "updated_at"])
