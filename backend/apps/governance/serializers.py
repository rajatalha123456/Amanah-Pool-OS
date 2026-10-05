from rest_framework import serializers

from apps.pools.models import Pool

from .models import ExceptionCase, PurificationEntry, RelatedPartyTransaction, SupportRequest


class ExceptionCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExceptionCase
        fields = (
            "id",
            "source_module",
            "source_object_id",
            "pool",
            "severity",
            "title",
            "description",
            "status",
            "detected_by",
            "assigned_to",
            "investigation_notes",
            "treatment_plan",
            "resolution_notes",
            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "detected_by",
            "investigation_notes",
            "treatment_plan",
            "resolution_notes",
            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
        )


class PurificationEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = PurificationEntry
        fields = (
            "id",
            "pool",
            "source_description",
            "amount",
            "identified_date",
            "status",
            "shariah_decision",
            "charity_recipient",
            "distributed_date",
            "approved_by",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "charity_recipient",
            "distributed_date",
            "approved_by",
            "created_at",
            "updated_at",
        )


class RelatedPartyTransactionSerializer(serializers.ModelSerializer):
    pool = serializers.PrimaryKeyRelatedField(queryset=Pool._base_manager.all())

    class Meta:
        model = RelatedPartyTransaction
        fields = (
            "id",
            "pool",
            "related_party_name",
            "relationship_type",
            "transaction_type",
            "amount",
            "transaction_date",
            "disclosure_status",
            "reviewed_by",
            "review_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "disclosure_status",
            "reviewed_by",
            "review_notes",
            "created_at",
            "updated_at",
        )

    def validate_pool(self, pool):
        request = self.context.get("request")
        if request and pool.tenant_id != request.user.tenant_id:
            raise serializers.ValidationError("Pool does not belong to the current tenant.")
        return pool


class SupportRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportRequest
        fields = (
            "id",
            "pool",
            "request_type",
            "subject",
            "description",
            "raised_by_name",
            "status",
            "priority",
            "assigned_to",
            "resolution_notes",
            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "assigned_to",
            "resolution_notes",
            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
        )


class ShariahAuditFindingSerializer(serializers.ModelSerializer):
    finding_ref = serializers.SerializerMethodField()
    description = serializers.CharField(source="observation", required=False)
    remediation_plan = serializers.CharField(
        source="management_response", required=False, allow_blank=True, allow_null=True
    )
    shariah_standard_ref = serializers.SerializerMethodField()
    identified_date = serializers.SerializerMethodField()
    remediation_deadline = serializers.SerializerMethodField()

    class Meta:
        from .models import ShariahAuditFinding

        model = ShariahAuditFinding
        fields = (
            "id",
            "audit_plan",
            "pool",
            "finding_ref",
            "title",
            "severity",
            "status",
            "observation",
            "description",
            "management_response",
            "remediation_plan",
            "shariah_standard_ref",
            "identified_date",
            "remediation_deadline",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_finding_ref(self, obj):
        return f"SAF-{str(obj.id)[:8].upper()}"

    def get_shariah_standard_ref(self, obj):
        return "AAOIFI-SS-18 (Mudharabah Governance)"

    def get_identified_date(self, obj):
        return obj.created_at.strftime("%Y-%m-%d") if obj.created_at else None

    def get_remediation_deadline(self, obj):
        return None

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, "copy") else dict(data)
        if "description" in data and "observation" not in data:
            data["observation"] = data["description"]
        if "remediation_plan" in data and "management_response" not in data:
            data["management_response"] = data["remediation_plan"]
        return super().to_internal_value(data)


class ShariahAuditPlanSerializer(serializers.ModelSerializer):
    findings = ShariahAuditFindingSerializer(many=True, read_only=True)
    year = serializers.IntegerField(source="plan_year", required=False)
    universe_scope = serializers.CharField(source="scope", required=False)
    target_samples = serializers.IntegerField(source="target_samples_count", required=False)
    tested_samples = serializers.IntegerField(source="tested_samples_count", required=False)
    scope_notes = serializers.CharField(
        source="notes", required=False, allow_blank=True, allow_null=True
    )

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, "copy") else dict(data)
        if "year" in data and "plan_year" not in data:
            data["plan_year"] = data["year"]
        if "universe_scope" in data and "scope" not in data:
            data["scope"] = data["universe_scope"]
        if "target_samples" in data and "target_samples_count" not in data:
            data["target_samples_count"] = data["target_samples"]
        if "tested_samples" in data and "tested_samples_count" not in data:
            data["tested_samples_count"] = data["tested_samples"]
        if "scope_notes" in data and "notes" not in data:
            data["notes"] = data["scope_notes"]
        return super().to_internal_value(data)

    class Meta:
        from .models import ShariahAuditPlan

        model = ShariahAuditPlan
        fields = (
            "id",
            "tenant",
            "plan_year",
            "year",
            "title",
            "scope",
            "universe_scope",
            "frequency",
            "status",
            "target_samples_count",
            "target_samples",
            "tested_samples_count",
            "tested_samples",
            "findings_count",
            "approved_by",
            "notes",
            "scope_notes",
            "findings",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "created_at", "updated_at")

