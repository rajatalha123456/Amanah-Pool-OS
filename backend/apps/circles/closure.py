"""Circle closure: final reconciliation, surplus/shortfall and closing (BRD 6.5)."""

from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    ArrearsRecord,
    ArrearsStatus,
    CircleClosure,
    CircleMember,
    CircleMemberStatus,
    ClosureStatus,
    Contribution,
    ContributionStatus,
    Payout,
    PayoutStatus,
)

ZERO = Decimal("0.00")


def reconcile(pool):
    rows, blockers = [], []
    for member in CircleMember.objects.filter(pool=pool):
        contributed = sum(
            (c.amount for c in Contribution.objects.filter(member=member, status=ContributionStatus.RECEIVED)), ZERO
        )
        paid = list(Payout.objects.filter(member=member, status=PayoutStatus.DISBURSED))
        received = sum((p.amount for p in paid), ZERO)
        fees = sum((p.service_fee for p in paid), ZERO)
        rows.append(
            {
                "member_reference": member.member_reference, "member_name": member.member_name,
                "status": member.status, "contributed": str(contributed), "received": str(received),
                "net": str(contributed - received), "service_fees": str(fees),
            }
        )
        if member.status == CircleMemberStatus.ACTIVE:
            blockers.append(f"{member.member_reference} has not yet received their payout.")
    open_payouts = Payout.objects.filter(pool=pool, status__in=[PayoutStatus.PENDING, PayoutStatus.APPROVED]).count()
    if open_payouts:
        blockers.append(f"{open_payouts} payout(s) are still awaiting approval or settlement.")
    overdue = ArrearsRecord.objects.filter(member__pool=pool, status=ArrearsStatus.OVERDUE).count()
    if overdue:
        blockers.append(f"{overdue} unresolved arrears record(s).")
    collected = sum((Decimal(r["contributed"]) for r in rows), ZERO)
    disbursed = sum((Decimal(r["received"]) for r in rows), ZERO)
    fees = sum((Decimal(r["service_fees"]) for r in rows), ZERO)
    return {
        "members": rows, "total_collected": collected, "total_disbursed": disbursed, "total_service_fees": fees,
        "difference": collected - disbursed - fees, "blockers": blockers,
    }


def prepare_closure(pool, user, resolution_note=""):
    if pool.status == "closed":
        raise ValidationError("This circle is already closed.")
    if pool.product.operating_model != "community_circle":
        raise ValidationError("Only community circles can be closed this way.")
    result = reconcile(pool)
    if result["blockers"]:
        raise ValidationError({"blockers": result["blockers"]})
    if result["difference"] != 0 and not resolution_note.strip():
        raise ValidationError(
            {"resolution_note": [f"A surplus/shortfall of {result['difference']} must be explained and resolved."]}
        )
    values = {
        "status": ClosureStatus.PREPARED, "total_collected": result["total_collected"],
        "total_disbursed": result["total_disbursed"], "difference": result["difference"],
        "resolution_note": resolution_note, "prepared_by": user, "snapshot": {"members": result["members"]},
    }
    closure, _ = CircleClosure.objects.update_or_create(pool=pool, tenant=pool.tenant, defaults=values)
    return closure


def close_circle(pool, checker):
    closure = CircleClosure.objects.filter(pool=pool, status=ClosureStatus.PREPARED).first()
    if closure is None:
        raise ValidationError("Prepare the final reconciliation first.")
    if closure.prepared_by_id == checker.id:
        raise ValidationError("Four-eyes rule: the preparer cannot also close the circle.")
    fresh = reconcile(pool)
    if fresh["blockers"] or fresh["difference"] != closure.difference:
        raise ValidationError("Circle data changed since the reconciliation was prepared; prepare it again.")
    closure.status = ClosureStatus.CLOSED
    closure.closed_by = checker
    closure.closed_at = timezone.now()
    closure.save()
    pool.status = "closed"
    pool.closed_date = timezone.localdate()
    pool.save(update_fields=["status", "closed_date", "updated_at"])
    return closure
