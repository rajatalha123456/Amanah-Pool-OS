from rest_framework import serializers

from .models import CircleMember, Contribution, Payout


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
    class Meta:
        model = Contribution
        fields = (
            "id",
            "member",
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
