from rest_framework import serializers

from .models import ContractTemplate, JurisdictionRulePack, Product, ShariahDecision, ShariahQuorumVote


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
        )
        read_only_fields = (
            "id",
            "tenant",
            "status",
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
        votes = obj.quorum_votes.all()
        approvals = sum(1 for v in votes if v.decision_vote == "approve")
        rejections = sum(1 for v in votes if v.decision_vote == "reject")
        required = 2
        return {
            "required_votes": required,
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
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "status", "created_at", "updated_at")

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
