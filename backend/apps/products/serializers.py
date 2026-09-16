from rest_framework import serializers

from .models import ContractTemplate, Product, ShariahDecision


class ShariahDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShariahDecision
        fields = (
            "id",
            "tenant",
            "decision_code",
            "title",
            "description",
            "status",
            "effective_date",
            "approved_by",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "approved_by", "created_at", "updated_at")


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
