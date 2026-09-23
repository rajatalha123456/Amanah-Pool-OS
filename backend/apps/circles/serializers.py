from rest_framework import serializers

from .models import ArrearsRecord, CircleMember, CircleProposal, CircleVote, Contribution, Payout


class CircleMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CircleMember
        fields = (
            "id",
            "pool",
            "member_name",
            "member_reference",
            "payout_position",
            "status",
            "joined_date",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "payout_position", "status", "created_at", "updated_at")


class ContributionSerializer(serializers.ModelSerializer):
    member_reference = serializers.CharField(source="member.member_reference", read_only=True)
    member_name = serializers.CharField(source="member.member_name", read_only=True)
    pool = serializers.CharField(source="member.pool_id", read_only=True)
    pool_name = serializers.CharField(source="member.pool.name", read_only=True)
    pool_code = serializers.CharField(source="member.pool.code", read_only=True)

    class Meta:
        model = Contribution
        fields = (
            "id",
            "member",
            "member_reference",
            "member_name",
            "pool",
            "pool_name",
            "pool_code",
            "amount",
            "contribution_date",
            "cycle_number",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status", "created_at", "updated_at")


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = (
            "id",
            "member",
            "pool",
            "cycle_number",
            "amount",
            "payout_date",
            "status",
            "disbursed_by",
            "draw_seed",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "disbursed_by",
            "draw_seed",
            "created_at",
            "updated_at",
        )


class CircleVoteSerializer(serializers.ModelSerializer):
    member_reference = serializers.CharField(source="member.member_reference", read_only=True)
    member_name = serializers.CharField(source="member.member_name", read_only=True)

    class Meta:
        model = CircleVote
        fields = (
            "id",
            "proposal",
            "member",
            "member_reference",
            "member_name",
            "decision",
            "voted_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "voted_at", "created_at", "updated_at")


class CircleProposalSerializer(serializers.ModelSerializer):
    votes = CircleVoteSerializer(many=True, read_only=True)

    class Meta:
        model = CircleProposal
        fields = (
            "id",
            "pool",
            "title",
            "description",
            "proposal_type",
            "status",
            "created_by",
            "voting_deadline",
            "closed_at",
            "votes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status", "created_by", "closed_at", "votes", "created_at", "updated_at")


class ArrearsRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArrearsRecord
        fields = (
            "id",
            "member",
            "cycle_number",
            "expected_amount",
            "status",
            "hardship_reason",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "hardship_reason",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        )
