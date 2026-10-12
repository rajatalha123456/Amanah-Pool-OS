"""Casting a vote on a circle proposal: one rule set for a vote a staff member records and a member's own vote."""

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import CircleMemberStatus, CircleVote, ProposalStatus, VoteDecision

METHODS = ("in_person", "otp", "e_sign", "portal")


def cast_vote(*, proposal, member, decision, method, evidence_reference, recorder):
    if proposal.status != ProposalStatus.OPEN:
        raise ValidationError("This proposal is not open for voting.")
    if member.pool_id != proposal.pool_id:
        raise ValidationError("Member not found on this proposal's pool.")
    if member.status != CircleMemberStatus.ACTIVE:
        raise ValidationError("Only active members vote.")
    if decision not in VoteDecision.values:
        raise ValidationError({"decision": [f"Must be one of {VoteDecision.values}."]})
    if timezone.localdate() > proposal.voting_deadline:
        raise ValidationError(f"Voting closed on {proposal.voting_deadline}.")
    if method not in METHODS:
        raise ValidationError({"method": [f"Must be one of {', '.join(METHODS)}."]})
    evidence_reference = (evidence_reference or "").strip()
    if method in ("otp", "e_sign") and not evidence_reference:
        raise ValidationError({"evidence_reference": ["An OTP / e-signature reference is required."]})
    if CircleVote.objects.filter(proposal=proposal, member=member).exists():
        raise ValidationError("This member has already voted on this proposal.")
    return CircleVote.objects.create(
        tenant=proposal.tenant, proposal=proposal, member=member, decision=decision, method=method,
        evidence_reference=evidence_reference, recorded_by=recorder,
    )
