"""
Approval matrix enforcement (BR-001 / BRD Section 4).

`assert_may_approve(user, tenant_id, action, amount)` is called at the point of a release-type
approval. With no active rules for the action the role permission alone decides; with rules,
the user's role must be listed and the amount must not exceed that role's limit.
"""

from decimal import Decimal

from rest_framework.exceptions import PermissionDenied

from .models import ApprovalMatrixRule


def active_rules(tenant_id, action):
    return list(ApprovalMatrixRule.objects.filter(tenant_id=tenant_id, action=action, is_active=True))


def assert_may_approve(user, tenant_id, action, amount=None):
    rules = active_rules(tenant_id, action)
    if not rules:
        return

    own = [rule for rule in rules if rule.role == user.role]
    if not own:
        allowed = ", ".join(sorted({rule.role for rule in rules}))
        raise PermissionDenied(f"Approval matrix: '{action}' may only be approved by: {allowed}.")

    if amount is None:
        return
    amount = abs(Decimal(amount))
    limits = [rule.max_amount for rule in own]
    if any(limit is None for limit in limits):
        return
    if amount > max(limits):
        raise PermissionDenied(
            f"Approval matrix: your limit for '{action}' is {max(limits)}; this approval is for {amount}. "
            "It needs a role with a higher limit."
        )
