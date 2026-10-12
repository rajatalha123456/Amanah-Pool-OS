"""
Retention routine. Only data classes with an *approved* policy are touched, and only in-app notifications that were
already read are actually deleted; support requests and AI records are reported as eligible for review but are
never removed automatically (they may be evidence in a dispute or an audit).
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import RetentionCategory, RetentionPolicy, RetentionPolicyStatus

MIN_DAYS = 30


def propose(*, tenant, user, data_category, retention_days, basis):
    if data_category not in RetentionCategory.values:
        raise ValidationError({"data_category": [f"Must be one of: {', '.join(RetentionCategory.values)}."]})
    try:
        retention_days = int(retention_days)
    except (TypeError, ValueError):
        raise ValidationError({"retention_days": ["A whole number of days is required."]})
    if retention_days < MIN_DAYS:
        raise ValidationError({"retention_days": [f"At least {MIN_DAYS} days."]})
    if not str(basis or "").strip():
        raise ValidationError({"basis": ["State the legal or policy basis for this period."]})
    return RetentionPolicy.objects.create(
        tenant=tenant, data_category=data_category, retention_days=retention_days, basis=str(basis).strip(), proposed_by=user
    )


def approve(policy, user):
    if policy.status != RetentionPolicyStatus.DRAFT:
        raise ValidationError(f"Only a draft policy can be approved (current status: '{policy.status}').")
    if policy.proposed_by_id == user.id:
        raise ValidationError("A different person than the proposer must approve the policy.")
    RetentionPolicy.objects.filter(
        tenant=policy.tenant, data_category=policy.data_category, status=RetentionPolicyStatus.APPROVED
    ).update(status=RetentionPolicyStatus.SUPERSEDED)
    policy.status, policy.approved_by, policy.approved_at = RetentionPolicyStatus.APPROVED, user, timezone.now()
    policy.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return policy


def _eligible(policy):
    from apps.ai_agents.models import AIRecommendation
    from apps.notifications.models import Notification

    from .models import SupportRequest, SupportRequestStatus

    cutoff = timezone.now() - timedelta(days=policy.retention_days)
    tenant = policy.tenant
    if policy.data_category == RetentionCategory.NOTIFICATIONS:
        return Notification._base_manager.filter(tenant=tenant, read_at__isnull=False, read_at__lt=cutoff)
    if policy.data_category == RetentionCategory.SUPPORT_REQUESTS:
        return SupportRequest._base_manager.filter(
            tenant=tenant, status=SupportRequestStatus.RESOLVED, updated_at__lt=cutoff
        )
    return AIRecommendation._base_manager.filter(tenant=tenant, created_at__lt=cutoff)


def run_retention(tenant, *, apply=False):
    """Returns one row per approved policy; deletes eligible notifications only when apply=True."""
    rows = []
    for policy in RetentionPolicy._base_manager.filter(tenant=tenant, status=RetentionPolicyStatus.APPROVED):
        eligible = _eligible(policy)
        count = eligible.count()
        deleted = 0
        if apply and policy.data_category == RetentionCategory.NOTIFICATIONS and count:
            deleted, _ = eligible.delete()
        rows.append({
            "data_category": policy.data_category, "retention_days": policy.retention_days, "eligible": count,
            "deleted": deleted,
            "action": "deleted" if deleted else ("review manually - never deleted automatically" if count and policy.data_category != RetentionCategory.NOTIFICATIONS else "none"),
        })
    return rows
