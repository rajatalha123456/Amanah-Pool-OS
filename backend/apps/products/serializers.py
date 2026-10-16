from rest_framework import serializers

from .models import ContractTemplate, JurisdictionRulePack, Product, ShariahDecision, ShariahDecisionStatus, ShariahQuorumVote


class ShariahQuorumVoteSerializer(serializers.ModelSerializer):
    signatory_user_name = serializers.SerializerMethodField()

    class Meta:
        model = ShariahQuorumVote
        fields = (
            "id",
            "decision",
            "scholar_name",
            "scholar_title",
            "decision_vote",
            "fiqh_concurrence_notes",
            "digital_signature_hash",
            "review_round",
            "voted_at",
            "signatory_user",
            "signatory_user_name",
        )
        read_only_fields = ("id", "voted_at", "digital_signature_hash", "signatory_user_name")

    def get_signatory_user_name(self, obj):
        if obj.signatory_user:
            return obj.signatory_user.full_name or obj.signatory_user.email
        return None


class ShariahDecisionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    quorum_votes = ShariahQuorumVoteSerializer(many=True, read_only=True)
    quorum_summary = serializers.SerializerMethodField()

    def validate_supersedes(self, value):
        if value is None:
            return value
        if value.tenant_id != self.context["request"].user.tenant_id:
            raise serializers.ValidationError("Choose a ruling of your own tenant.")
        if value.status != ShariahDecisionStatus.APPROVED:
            raise serializers.ValidationError("Only an approved ruling can be superseded.")
        if self.instance is not None and value.pk == self.instance.pk:
            raise serializers.ValidationError("A ruling cannot supersede itself.")
        return value

    class Meta:
        model = ShariahDecision
        fields = (
            "id",
            "tenant",
            "decision_code",
            "title",
            "decision_type",
            "meeting_reference",
            "scholars_signatories",
            "fiqh_reference",
            "description",
            "mandatory_caveats",
            "fatwa_arabic_text",
            "status",
            "effective_date",
            "expiry_date",
            "document_url",
            "scope",
            "supersedes",
            "created_by",
            "created_by_name",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "is_active",
            "created_at",
            "updated_at",
            "quorum_votes",
            "quorum_summary",
            "review_round",
            "return_note",
        )
        read_only_fields = (
            "id",
            "tenant",
            "status",
            "review_round",
            "return_note",
            "created_by",
            "created_by_name",
            "approved_by",
            "approved_by_name",
            "approved_at",
            "created_at",
            "updated_at",
            "quorum_votes",
            "quorum_summary",
        )

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.full_name or obj.created_by.email
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.full_name or obj.approved_by.email
        return None

    def get_quorum_summary(self, obj):
        votes = [v for v in obj.quorum_votes.all() if v.review_round == obj.review_round]  # only the current round counts
        approvals = sum(1 for v in votes if v.decision_vote == "approve")
        rejections = sum(1 for v in votes if v.decision_vote == "reject")
        from .shariah import board_size, quorum_required

        required = quorum_required(obj.tenant_id)
        return {
            "required_votes": required,
            "board_size": board_size(obj.tenant_id),
            "approvals": approvals,
            "rejections": rejections,
            "is_quorum_met": approvals >= required,
            "status_label": f"{approvals}/{required} Signatures Collected",
        }


class ContractTemplateSerializer(serializers.ModelSerializer):
    shariah_decision_code = serializers.CharField(
        source="shariah_decision.decision_code", read_only=True, default=None
    )

    class Meta:
        model = ContractTemplate
        fields = (
            "id",
            "tenant",
            "name",
            "contract_type",
            "version",
            "clauses",
            "shariah_decision",
            "shariah_decision_code",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "status", "created_at", "updated_at")


class ContractTemplateBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractTemplate
        fields = ("id", "name", "contract_type", "version", "status")


class ProductSerializer(serializers.ModelSerializer):
    contract_template_detail = ContractTemplateBasicSerializer(
        source="contract_template", read_only=True
    )

    class Meta:
        model = Product
        fields = (
            "id",
            "tenant",
            "name",
            "code",
            "operating_model",
            "contract_template",
            "contract_template_detail",
            "status",
            "base_currency",
            "eligible_asset_types",
            "redemption_notice_days",
            "redemption_gate_pct",
            "minimum_subscription",
            "subscription_cap",
            "minimum_tenure_days",
            "required_kyc_tier",
            "max_participants",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "status", "created_at", "updated_at")

    def validate_redemption_gate_pct(self, value):
        if not 0 < value <= 100:
            raise serializers.ValidationError("The gate must be above 0 and at most 100 percent.")
        return value

    def validate_required_kyc_tier(self, value):
        from apps.participants.kyc_tiers import TIERS

        if value not in TIERS:
            raise serializers.ValidationError(f"Must be one of: {', '.join(TIERS)}.")
        return value

    def validate(self, attrs):
        minimum = attrs.get("minimum_subscription", getattr(self.instance, "minimum_subscription", None))
        cap = attrs.get("subscription_cap", getattr(self.instance, "subscription_cap", None))
        for name, value in (("minimum_subscription", minimum), ("subscription_cap", cap)):
            if value is not None and value <= 0:
                raise serializers.ValidationError({name: ["Must be above zero, or left empty for no limit."]})
        if minimum is not None and cap is not None and minimum > cap:
            raise serializers.ValidationError({"subscription_cap": ["The cap cannot be below the minimum subscription."]})
        return attrs

    def validate_eligible_asset_types(self, value):
        from apps.pools.models import AssetType

        valid = {choice for choice, _ in AssetType.choices}
        if not isinstance(value, list) or any(item not in valid for item in value):
            raise serializers.ValidationError(f"Must be a list of asset types from: {', '.join(sorted(valid))}.")
        return sorted(set(value))

    def validate_code(self, value):
        # Product.code is only enforced unique via a composite
        # UniqueConstraint(tenant, code) at the DB level, which DRF does
        # not auto-validate (only a plain unique=True field gets that for
        # free). Without this check, a duplicate code raises a raw
        # IntegrityError that surfaces as an unhandled 500 instead of a
        # clean 400 - same bug found and fixed for Pool.code while
        # building the New Pool Wizard.
        tenant = self.context["request"].user.tenant
        queryset = Product.objects.filter(tenant=tenant, code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A product with this code already exists.")
        return value


class JurisdictionRulePackSerializer(serializers.ModelSerializer):
    class Meta:
        model = JurisdictionRulePack
        fields = (
            "id",
            "tenant",
            "code",
            "name",
            "version",
            "effective_date",
            "is_active",
            "is_default",
            "description",
            "rules_config",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "created_at", "updated_at")

    # Only one rule pack is the tenant's default: when a change that makes another pack the default is applied, the
    # flag is taken away from the previous one in the same step.
    def _single_default(self, instance):
        if instance.is_default:
            JurisdictionRulePack._base_manager.filter(tenant_id=instance.tenant_id).exclude(pk=instance.pk).update(
                is_default=False
            )

    def create(self, validated_data):
        instance = super().create(validated_data)
        self._single_default(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self._single_default(instance)
        return instance
