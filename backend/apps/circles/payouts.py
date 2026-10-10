"""
Community-circle payout rules (BRD BR-008, BR-007, Section 6.5).

A payout is released only when collections, beneficiary eligibility, KYC and
dual approval all pass:

  1. a maker REQUESTS the payout for the member whose turn it is - this module
     verifies every pre-condition and computes the amount from the collections
     actually received (never from a client-supplied figure);
  2. an independent checker APPROVES it (must differ from the requester and the
     pool must carry an approved Shariah decision);
  3. the settlement is CONFIRMED with the bank's settlement reference.

Nothing here invents data: no contributions are auto-created, no certificates,
biometrics or bank details are fabricated. No fee, interest or time-value
uplift can be applied (BR-007): the amount is exactly the pot collected.
"""

import re
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from apps.participants.models import KYCStatus
from apps.products.shariah import shariah_decision_for

from .models import (
    ArrearsRecord,
    ArrearsStatus,
    CircleMember,
    CircleMemberStatus,
    Contribution,
    ContributionStatus,
    Payout,
    PayoutStatus,
    SettlementRailType,
)

IBAN_PATTERN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$")


def next_cycle_number(pool):
    return Payout.objects.filter(pool=pool, status=PayoutStatus.DISBURSED).count() + 1


def next_recipient(pool):
    return (
        CircleMember.objects.filter(
            pool=pool, status=CircleMemberStatus.ACTIVE, payout_position__isnull=False
        )
        .order_by("payout_position")
        .first()
    )


def _check(key, label, passed, detail=""):
    return {"key": key, "label": label, "passed": bool(passed), "detail": detail}


def build_preflight(pool, member, cycle_number, rail):
    """
    Evaluates every release pre-condition for paying `member` the pot of
    `cycle_number`. Returns {"checks": [...], "ok": bool, "amount": Decimal}.
    """

    active = CircleMember.objects.filter(pool=pool, status=CircleMemberStatus.ACTIVE)
    active_ids = set(active.values_list("id", flat=True))
    unassigned = active.filter(payout_position__isnull=True).count()
    turn = next_recipient(pool)

    received = Contribution.objects.filter(
        member__pool=pool, cycle_number=cycle_number, status=ContributionStatus.RECEIVED
    )
    received_member_ids = set(received.values_list("member_id", flat=True))
    missing = active_ids - received_member_ids
    amount = sum((c.amount for c in received), Decimal("0.00"))

    overdue = ArrearsRecord.objects.filter(
        member__pool=pool, cycle_number=cycle_number, status=ArrearsStatus.OVERDUE
    ).count()
    open_payout = Payout.objects.filter(
        pool=pool, status__in=[PayoutStatus.PENDING, PayoutStatus.APPROVED]
    ).first()
    decision = shariah_decision_for(pool)

    iban = (member.iban or "").replace(" ", "").upper()
    if rail == SettlementRailType.INTERNAL_BOOK:
        bank_ok, bank_detail = True, "Internal book transfer - no external account needed."
    else:
        bank_ok = bool(IBAN_PATTERN.match(iban)) and bool(member.bank_name)
        bank_detail = "" if bank_ok else "A valid IBAN and bank name are required on the member record."

    checks = [
        _check(
            "pool_is_circle",
            "Pool is a community circle",
            pool.product.operating_model == "community_circle",
            f"Operating model: {pool.product.operating_model}",
        ),
        _check(
            "draw_completed",
            "Payout order assigned to every active member",
            unassigned == 0 and bool(active_ids),
            f"{unassigned} active member(s) without a draw position" if unassigned else "",
        ),
        _check(
            "member_has_turn",
            "Recipient is the member whose turn it is",
            turn is not None and turn.id == member.id,
            "" if turn and turn.id == member.id else (
                f"Current turn: position {turn.payout_position}" if turn else "No member is eligible for a turn."
            ),
        ),
        _check(
            "contributions_complete",
            "All active members have contributed for this cycle",
            not missing and bool(active_ids),
            f"{len(missing)} member(s) still pending" if missing else "",
        ),
        _check("pot_funded", "Collected pot is greater than zero", amount > 0, f"Collected: {amount}"),
        _check(
            "no_overdue_arrears",
            "No unresolved arrears for this cycle",
            overdue == 0,
            f"{overdue} overdue arrears record(s)" if overdue else "",
        ),
        _check(
            "recipient_kyc",
            "Recipient KYC is verified",
            member.kyc_status == KYCStatus.VERIFIED,
            f"KYC status: {member.kyc_status}",
        ),
        _check("recipient_bank", "Recipient bank details are valid", bank_ok, bank_detail),
        _check(
            "shariah_decision",
            "Approved Shariah decision backs the pool's contract",
            decision is not None,
            decision.decision_code if decision else "No approved, in-force Shariah decision is linked to the contract.",
        ),
        _check(
            "no_open_payout",
            "No other payout is awaiting approval or settlement",
            open_payout is None,
            f"Open payout {open_payout.id}" if open_payout else "",
        ),
    ]
    return {"checks": checks, "ok": all(c["passed"] for c in checks), "amount": amount}


def create_payout_request(*, pool, member, user, rail, payout_date, cycle_number=None):
    computed_cycle = next_cycle_number(pool)
    if cycle_number is not None and int(cycle_number) != computed_cycle:
        raise ValidationError(f"The current cycle is {computed_cycle}, not {cycle_number}.")

    if rail not in SettlementRailType.values:
        raise ValidationError({"settlement_rail": ["Unknown settlement rail."]})

    preflight = build_preflight(pool, member, computed_cycle, rail)
    if not preflight["ok"]:
        failed = [f"{c['label']}: {c['detail']}".rstrip(": ") for c in preflight["checks"] if not c["passed"]]
        raise ValidationError({"preflight": failed})

    return Payout.objects.create(
        tenant=pool.tenant,
        member=member,
        pool=pool,
        cycle_number=computed_cycle,
        amount=preflight["amount"],
        payout_date=payout_date,
        status=PayoutStatus.PENDING,
        requested_by=user,
        settlement_rail=rail,
        recipient_iban=member.iban,
        recipient_bank=member.bank_name,
        draw_seed=None,
    )
