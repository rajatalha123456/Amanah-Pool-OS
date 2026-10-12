"""
Pool lifecycle beyond activation (BRD 6.x: draft, review, approved, open, frozen, allocation, closed, archived).

  freeze     open / allocation -> frozen    a documented hold: no new subscriptions, redemptions, contributions,
                                            payouts or allocation runs until it is lifted
  unfreeze   frozen -> the status before    lifted by a *different* person than the one who froze the pool
  archive    closed -> archived             read-only for good; only a closed pool can be archived
"""

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import ConflictError

from .models import PoolStatus

FREEZABLE = (PoolStatus.OPEN, PoolStatus.ALLOCATION)


def assert_not_frozen(pool, what="this action"):
    """Money-moving actions call this; a frozen or archived pool refuses them."""
    if pool.status == PoolStatus.FROZEN:
        raise ConflictError(f"Pool {pool.code} is frozen ({pool.freeze_reason}); {what} is not allowed until it is unfrozen.")
    if pool.status == PoolStatus.ARCHIVED:
        raise ConflictError(f"Pool {pool.code} is archived; {what} is not allowed.")


def freeze(pool, user, reason):
    reason = (reason or "").strip()
    if len(reason) < 10:
        raise ValidationError({"reason": ["Give the reason for the freeze (at least 10 characters)."]})
    if pool.status not in FREEZABLE:
        raise ValidationError(f"Only an open pool can be frozen (current status: '{pool.status}').")
    previous = pool.status
    pool.frozen_from, pool.freeze_reason = previous, reason
    pool.frozen_by, pool.frozen_at = user, timezone.now()
    pool.status = PoolStatus.FROZEN
    pool.save(update_fields=["status", "frozen_from", "freeze_reason", "frozen_by", "frozen_at", "updated_at"])
    return previous


def unfreeze(pool, user, reason):
    reason = (reason or "").strip()
    if len(reason) < 10:
        raise ValidationError({"reason": ["Give the reason for lifting the freeze (at least 10 characters)."]})
    if pool.status != PoolStatus.FROZEN:
        raise ValidationError(f"The pool is not frozen (current status: '{pool.status}').")
    if pool.frozen_by_id and pool.frozen_by_id == user.id:
        raise ConflictError("The freeze must be lifted by a different person than the one who applied it.")
    restored = pool.frozen_from or PoolStatus.OPEN
    pool.status = restored
    pool.freeze_reason = ""
    pool.frozen_from = ""
    pool.save(update_fields=["status", "freeze_reason", "frozen_from", "updated_at"])
    return restored


def archive(pool, user):
    if pool.status != PoolStatus.CLOSED:
        raise ValidationError(f"Only a closed pool can be archived (current status: '{pool.status}').")
    pool.status = PoolStatus.ARCHIVED
    pool.save(update_fields=["status", "updated_at"])
