from rest_framework import serializers

from .models import (
    CapitalAccount,
    ImpairmentEvent,
    InvestorProfile,
    NAVSnapshot,
    Redemption,
    Subscription,
)


class CapitalAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CapitalAccount
        fields = (
            "id",
            "pool",
            "investor_name",
            "investor_reference",
            "units_held",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "units_held", "status", "created_at", "updated_at")


class InvestorProfileSerializer(serializers.ModelSerializer):
    capital_account = serializers.PrimaryKeyRelatedField(queryset=CapitalAccount._base_manager.all())

    class Meta:
        model = InvestorProfile
        fields = (
            "id",
            "capital_account",
            "kyc_status",
            "id_document_type",
            "id_document_number",
            "date_of_birth",
            "address",
            "risk_tolerance",
            "suitability_assessment_notes",
            "verified_by",
            "verified_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "kyc_status",
            "verified_by",
            "verified_at",
            "created_at",
            "updated_at",
        )

    def validate_capital_account(self, account):
        request = self.context.get("request")
        if request and account.tenant_id != request.user.tenant_id:
            raise serializers.ValidationError("Capital account does not belong to the current tenant.")
        return account


class ImpairmentEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImpairmentEvent
        fields = (
            "id",
            "pool",
            "valuation_date",
            "loss_amount",
            "loss_percentage",
            "reason",
            "status",
            "approved_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "loss_percentage",
            "status",
            "approved_by",
            "created_at",
            "updated_at",
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = (
            "id",
            "capital_account",
            "amount",
            "nav_per_unit",
            "units_allotted",
            "transaction_date",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "units_allotted", "status", "created_at", "updated_at")


class RedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Redemption
        fields = (
            "id",
            "capital_account",
            "units_redeemed",
            "nav_per_unit",
            "amount",
            "transaction_date",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "amount", "status", "created_at", "updated_at")


class NAVSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = NAVSnapshot
        fields = (
            "id",
            "pool",
            "valuation_date",
            "total_pool_value",
            "total_units_outstanding",
            "nav_per_unit",
            "status",
            "created_by",
            "published_by",
            "published_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "total_units_outstanding",
            "nav_per_unit",
            "status",
            "created_by",
            "published_by",
            "published_at",
            "created_at",
            "updated_at",
        )
