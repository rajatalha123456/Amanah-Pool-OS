from rest_framework import serializers

from .models import (
    CapitalAccount,
    ImpairmentEvent,
    InvestmentDistributionLine,
    InvestmentDistributionRun,
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
            "participant",
            "is_managing_partner",
            "units_held",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "units_held", "status", "created_at", "updated_at")

    def validate(self, attrs):
        if self.instance is not None:
            # An account's pool and owner never change: units, movements and statements belong to them.
            for field in ("pool", "participant", "is_managing_partner"):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError({field: ["This cannot be changed once the account exists."]})
        if attrs.get("is_managing_partner"):
            pool = attrs.get("pool", getattr(self.instance, "pool", None))
            if pool is not None:
                if pool.product.contract_template.contract_type != "musharakah":
                    raise serializers.ValidationError(
                        {"is_managing_partner": "Only a Musharakah pool has a managing partner capital account."}
                    )
                others = CapitalAccount.objects.filter(pool=pool, is_managing_partner=True)
                if self.instance is not None:
                    others = others.exclude(pk=self.instance.pk)
                if others.exists():
                    raise serializers.ValidationError(
                        {"is_managing_partner": "This pool already has a managing partner capital account."}
                    )
        return attrs

    def __init__(self, *args, **kwargs):
        # Built per instance, after TenantMiddleware set the tenant (a class-level
        # queryset on a TenantScopedManager would be frozen empty at import time).
        super().__init__(*args, **kwargs)
        from apps.participants.models import Participant

        self.fields["participant"] = serializers.PrimaryKeyRelatedField(
            queryset=Participant.objects.all(), required=False, allow_null=True
        )


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
            "requested_by",
            "approved_by",
            "approved_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id", "amount", "status", "requested_by", "approved_by", "approved_at", "rejection_reason",
            "created_at", "updated_at",
        )


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


class DistributionLineSerializer(serializers.ModelSerializer):
    investor_reference = serializers.CharField(source="capital_account.investor_reference", read_only=True)
    investor_name = serializers.CharField(source="capital_account.investor_name", read_only=True)

    class Meta:
        model = InvestmentDistributionLine
        fields = (
            "id",
            "capital_account",
            "investor_reference",
            "investor_name",
            "average_units",
            "share_ratio",
            "allocated_amount",
        )
        read_only_fields = fields


class DistributionRunSerializer(serializers.ModelSerializer):
    lines = DistributionLineSerializer(many=True, read_only=True)
    journal_batch_id = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentDistributionRun
        fields = (
            "id",
            "pool",
            "period_start",
            "period_end",
            "gross_income",
            "direct_expenses",
            "distributable_amount",
            "investor_share",
            "manager_share",
            "rounding_residual",
            "total_average_units",
            "is_loss",
            "config_snapshot",
            "status",
            "calculation_hash",
            "replaces_run",
            "is_restatement",
            "restatement_reason",
            "created_by",
            "checked_by",
            "checked_at",
            "shariah_signed_off_by",
            "shariah_signed_off_at",
            "shariah_review_note",
            "released_by",
            "released_at",
            "rejection_reason",
            "lines",
            "journal_batch_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_journal_batch_id(self, obj):
        batch = getattr(obj, "journal_batch", None)
        return str(batch.id) if batch else None
