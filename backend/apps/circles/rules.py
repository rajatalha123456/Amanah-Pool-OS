"""Circle rules publication and member acceptance (BRD 6.5: members accept rules, schedule, order, hardship policy)."""

import hashlib
import json

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import CircleMember, CircleMemberStatus, CircleRules, RulesAcceptance

ACCEPTANCE_METHODS = ("in_person", "otp", "e_sign")


def current_rules(pool):
    return CircleRules.objects.filter(pool=pool).order_by("-version").first()


def publish_rules(
    *, pool, user, contribution_amount, cycle_days, order_policy, hardship_policy, schedule_note="", first_due_date=None,
    operating_model="qard", service_fee_per_cycle=0, mandates_required=False,
):
    if pool.product.operating_model != "community_circle":
        raise ValidationError({"pool": ["Rules apply to community circles only."]})
    if contribution_amount <= 0 or cycle_days <= 0:
        raise ValidationError("Contribution amount and cycle length must be positive.")
    if not order_policy.strip() or not hardship_policy.strip():
        raise ValidationError("The payout-order policy and the hardship policy are both required.")
    from decimal import Decimal

    contract_type = pool.product.contract_template.contract_type if pool.product.contract_template_id else ""
    fee = Decimal(str(service_fee_per_cycle or 0))
    if operating_model not in ("qard", "wakalah"):
        raise ValidationError({"operating_model": ["Must be qard or wakalah."]})
    if operating_model == "qard" and fee != 0:
        raise ValidationError({"service_fee_per_cycle": ["A Qard circle charges no fee."]})
    if operating_model == "wakalah":
        if contract_type != "wakalah":
            raise ValidationError({"operating_model": ["The Wakalah model needs a product whose approved contract is Wakalah."]})
        if fee < 0 or fee >= contribution_amount:
            raise ValidationError({"service_fee_per_cycle": ["The fee must be zero or more and below one contribution."]})
    previous = current_rules(pool)
    version = (previous.version if previous else 0) + 1
    body = {
        "pool": pool.code, "version": version, "contribution_amount": str(contribution_amount),
        "cycle_days": cycle_days, "schedule_note": schedule_note, "order_policy": order_policy,
        "hardship_policy": hardship_policy,
    }
    if first_due_date is not None:  # only sealed when set, so earlier rule versions keep their hashes
        body["first_due_date"] = str(first_due_date)
    if operating_model != "qard" or mandates_required:  # likewise: Qard rules without mandates keep their old hashes
        body.update({"operating_model": operating_model, "service_fee_per_cycle": str(fee), "mandates_required": mandates_required})
    return CircleRules.objects.create(
        tenant=pool.tenant, pool=pool, version=version, contribution_amount=contribution_amount,
        cycle_days=cycle_days, schedule_note=schedule_note, order_policy=order_policy,
        hardship_policy=hardship_policy, published_by=user, first_due_date=first_due_date,
        operating_model=operating_model, service_fee_per_cycle=fee, mandates_required=mandates_required,
        content_hash=hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(),
    )


def record_acceptance(*, member, user, method, evidence_reference=""):
    rules = current_rules(member.pool)
    if rules is None:
        raise ValidationError("No rules have been published for this circle yet.")
    if method not in ACCEPTANCE_METHODS:
        raise ValidationError({"method": [f"Must be one of: {', '.join(ACCEPTANCE_METHODS)}."]})
    if member.status != CircleMemberStatus.ACTIVE:
        raise ValidationError("Only active members can accept the rules.")
    if method != "in_person" and not evidence_reference.strip():
        raise ValidationError({"evidence_reference": ["An OTP / e-signature reference is required."]})
    acceptance, created = RulesAcceptance.objects.get_or_create(
        tenant=member.tenant, member=member, rules=rules,
        defaults={
            "accepted_at": timezone.now(), "method": method, "evidence_reference": evidence_reference,
            "recorded_by": user,
        },
    )
    if not created:
        raise ValidationError("This member has already accepted the current rules.")
    return acceptance


def acceptance_summary(pool):
    rules = current_rules(pool)
    active = list(CircleMember.objects.filter(pool=pool, status=CircleMemberStatus.ACTIVE))
    if rules is None:
        return {"rules": None, "accepted": 0, "total": len(active), "missing": [m.member_reference for m in active]}
    accepted_ids = set(RulesAcceptance.objects.filter(rules=rules).values_list("member_id", flat=True))
    return {
        "rules": rules,
        "accepted": sum(1 for m in active if m.id in accepted_ids),
        "total": len(active),
        "missing": [m.member_reference for m in active if m.id not in accepted_ids],
    }


def assert_rules_accepted(pool):
    summary = acceptance_summary(pool)
    if summary["rules"] is None:
        raise ValidationError("Publish the circle rules and have every member accept them first.")
    if summary["missing"]:
        raise ValidationError(
            f"{len(summary['missing'])} member(s) have not accepted rules v{summary['rules'].version}: "
            + ", ".join(summary["missing"])
        )


def publish_and_accept_all(pool, user, **overrides):
    """Convenience for seeding and tests: publish default rules and record every active member's acceptance."""
    from decimal import Decimal

    fields = {
        "contribution_amount": Decimal("10000.00"), "cycle_days": 30,
        "order_policy": "Payout order is fixed by a verifiable draw.",
        "hardship_policy": "Hardship is reviewed by Shariah oversight; no penalty applies.",
    }
    fields.update(overrides)
    rules = publish_rules(pool=pool, user=user, **fields)
    for member in CircleMember.objects.filter(pool=pool, status=CircleMemberStatus.ACTIVE):
        record_acceptance(member=member, user=user, method="in_person")
    return rules
