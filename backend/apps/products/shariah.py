"""Shared Shariah-approval lookups."""

from django.utils import timezone

from .models import ShariahDecision, ShariahDecisionStatus


def shariah_decision_for(pool):
    """The approved, in-force Shariah decision backing the pool's contract template, or None."""

    decision = pool.product.contract_template.shariah_decision
    # A contract keeps pointing at the ruling it was approved under. When the Board supersedes that ruling, the
    # approved successor is the one in force; the chain is followed, never silently rewritten on the contract.
    seen = set()
    while decision is not None and decision.status == ShariahDecisionStatus.SUPERSEDED and decision.pk not in seen:
        seen.add(decision.pk)
        decision = (
            ShariahDecision._base_manager.filter(supersedes=decision, status=ShariahDecisionStatus.APPROVED)
            .order_by("-approved_at")
            .first()
        )
    if decision is None or decision.status != ShariahDecisionStatus.APPROVED:
        return None
    today = timezone.localdate()
    if decision.effective_date > today or (decision.expiry_date and decision.expiry_date < today):
        return None
    return decision


def board_size(tenant_id):
    from apps.accounts.models import User, UserRole

    return User.objects.filter(tenant_id=tenant_id, role=UserRole.SHARIAH_BOARD, is_active=True).count()


def quorum_required(tenant_id):
    """Approvals needed for a ruling: two thirds of the tenant's active Board members, and never fewer than two."""
    import math

    return max(2, math.ceil(board_size(tenant_id) * 2 / 3))


def apply_supersession(decision):
    """Called when a ruling is approved: the ruling it replaces is marked superseded (history is kept)."""
    if decision.supersedes_id:
        ShariahDecision._base_manager.filter(
            pk=decision.supersedes_id, status=ShariahDecisionStatus.APPROVED
        ).update(status=ShariahDecisionStatus.SUPERSEDED)
