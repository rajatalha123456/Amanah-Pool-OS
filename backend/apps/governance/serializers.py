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
