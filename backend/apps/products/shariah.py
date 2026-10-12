"""Shared Shariah-approval lookups."""

from django.utils import timezone

from .models import ShariahDecisionStatus


def shariah_decision_for(pool):
    """The approved, in-force Shariah decision backing the pool's contract template, or None."""

    decision = pool.product.contract_template.shariah_decision
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
