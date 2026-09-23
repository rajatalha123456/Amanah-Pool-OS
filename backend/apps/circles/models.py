from django.db import models

from apps.core.models import TenantScopedModel


class CircleMemberStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAID_OUT = "paid_out", "Paid Out"
    WITHDRAWN = "withdrawn", "Withdrawn"


class ContributionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RECEIVED = "received", "Received"


class PayoutStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    DISBURSED = "disbursed", "Disbursed"


class ArrearsStatus(models.TextChoices):
    OVERDUE = "overdue", "Overdue"
    HARDSHIP_GRANTED = "hardship_granted", "Hardship Granted"
    RESOLVED = "resolved", "Resolved"


class CircleMember(TenantScopedModel):
    """
    A participant in a community_circle-model Pool (a ROSCA - rotating
    savings and credit association). payout_position is null until
    apps.circles.rotation.run_draw() assigns it; once assigned it fixes
    that member's place in the payout rotation for the life of the
    circle.
    """

    pool = models.ForeignKey(
        "pools.Pool", on_delete=models.CASCADE, related_name="circle_members"
    )
    member_name = models.CharField(max_length=255)
    member_reference = models.CharField(max_length=50)
    payout_position = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=CircleMemberStatus.choices, default=CircleMemberStatus.ACTIVE
    )
    joined_date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "member_reference"], name="unique_circle_member_reference_per_tenant"
            ),
            models.UniqueConstraint(
                fields=["pool", "payout_position"],
                condition=models.Q(payout_position__isnull=False),
                name="unique_payout_position_per_pool",
            ),
        ]

    def __str__(self):
        return f"{self.member_reference} - {self.member_name} ({self.pool.name})"


class Contribution(TenantScopedModel):
    member = models.ForeignKey(CircleMember, on_delete=models.CASCADE, related_name="contributions")
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    contribution_date = models.DateField()
    cycle_number = models.IntegerField()
    status = models.CharField(
        max_length=20, choices=ContributionStatus.choices, default=ContributionStatus.PENDING
    )

    def __str__(self):
        return f"{self.member.member_reference} cycle {self.cycle_number} ({self.status})"


class Payout(TenantScopedModel):
    """
    draw_seed stores the secrets.token_hex() seed produced by
    apps.circles.rotation.run_draw() for the draw that determined this
    member's payout_position, kept here (as well as on the draw's own
    audit log entry) so any individual payout can be traced back to the
    randomization that assigned its recipient's turn.
    """

    member = models.ForeignKey(CircleMember, on_delete=models.CASCADE, related_name="payouts")
    pool = models.ForeignKey("pools.Pool", on_delete=models.CASCADE, related_name="circle_payouts")
    cycle_number = models.IntegerField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    payout_date = models.DateField()
    status = models.CharField(max_length=20, choices=PayoutStatus.choices, default=PayoutStatus.PENDING)
    disbursed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    draw_seed = models.CharField(max_length=64, null=True, blank=True)

    def __str__(self):
        return f"{self.member.member_reference} cycle {self.cycle_number} - {self.amount} ({self.status})"


class ProposalType(models.TextChoices):
    AMOUNT_CHANGE = "amount_change", "Amount Change"
    MEMBER_ADDITION = "member_addition", "Member Addition"
    RULE_CHANGE = "rule_change", "Rule Change"
    OTHER = "other", "Other"


class ProposalStatus(models.TextChoices):
    OPEN = "open", "Open"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CLOSED = "closed", "Closed"


class VoteDecision(models.TextChoices):
    APPROVE = "approve", "Approve"
    REJECT = "reject", "Reject"
    ABSTAIN = "abstain", "Abstain"


class CircleProposal(TenantScopedModel):
    """
    A proposal put to a vote among a circle's active members - e.g.
    changing the contribution amount, adding a member, or changing a
    rule. Voting is recorded via CircleVote and tallied when a Pool
    Manager closes the proposal (see CircleProposalViewSet.close).
    """

    pool = models.ForeignKey("pools.Pool", on_delete=models.CASCADE, related_name="circle_proposals")
    title = models.CharField(max_length=255)
    description = models.TextField()
    proposal_type = models.CharField(max_length=20, choices=ProposalType.choices)
    status = models.CharField(max_length=20, choices=ProposalStatus.choices, default=ProposalStatus.OPEN)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    voting_deadline = models.DateField()
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.status})"


class CircleVote(TenantScopedModel):
    proposal = models.ForeignKey(CircleProposal, on_delete=models.CASCADE, related_name="votes")
    member = models.ForeignKey(CircleMember, on_delete=models.CASCADE, related_name="circle_votes")
    decision = models.CharField(max_length=20, choices=VoteDecision.choices)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["proposal", "member"], name="unique_vote_per_member_per_proposal"),
        ]

    def __str__(self):
        return f"{self.member.member_reference} -> {self.proposal.title} ({self.decision})"


class ArrearsRecord(TenantScopedModel):
    """
    Tracks a member falling behind on an expected contribution for a
    cycle. Created manually (via CircleMemberViewSet.flag_arrears) for
    now - automatic detection from cycle deadlines is out of scope
    until deadlines are modeled. A hardship waiver can only be granted
    by Shariah oversight (Secretariat or Board), never by Risk &
    Compliance alone, since waiving a member's obligation is a
    Shariah-governance decision, not an operational one.
    """

    member = models.ForeignKey(CircleMember, on_delete=models.CASCADE, related_name="arrears_records")
    cycle_number = models.IntegerField()
    expected_amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, choices=ArrearsStatus.choices, default=ArrearsStatus.OVERDUE)
    hardship_reason = models.TextField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.member.member_reference} cycle {self.cycle_number} ({self.status})"
