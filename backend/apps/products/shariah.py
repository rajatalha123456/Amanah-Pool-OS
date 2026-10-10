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
