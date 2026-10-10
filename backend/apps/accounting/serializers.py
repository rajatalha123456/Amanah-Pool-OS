from rest_framework import serializers

from .models import IncomeExpenseEvent, JournalBatch, JournalEntry


class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = ("id", "account_name", "entry_type", "amount")
        read_only_fields = fields


class IncomeExpenseEventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.ReadOnlyField(source="created_by.full_name")
    posted_by_name = serializers.ReadOnlyField(source="posted_by.full_name")
    pool_name = serializers.ReadOnlyField(source="pool.name")
    pool_code = serializers.ReadOnlyField(source="pool.code")

    class Meta:
        model = IncomeExpenseEvent
        fields = (
            "id",
            "tenant",
            "pool",
            "pool_name",
            "pool_code",
            "event_type",
            "cost_classification",
            "category",
            "amount",
            "pool_chargeable_amount",
            "bank_absorbed_amount",
            "is_direct_expense",
            "is_overhead_leakage",
            "quarantined_to_charity",
            "event_date",
            "description",
            "shariah_note",
            "status",
            "created_by",
            "created_by_name",
            "posted_by",
            "posted_by_name",
            "posted_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "tenant",
            "status",
            "created_by",
            "posted_by",
            "posted_at",
            "created_at",
            "updated_at",
            "pool_chargeable_amount",
            "bank_absorbed_amount",
            "is_direct_expense",
            "is_overhead_leakage",
            "quarantined_to_charity",
        )


class JournalBatchSerializer(serializers.ModelSerializer):
    entries = JournalEntrySerializer(many=True, read_only=True)

    class Meta:
        model = JournalBatch
        fields = (
            "id",
            "tenant",
            "allocation_run",
            "pool",
            "batch_date",
            "total_debit",
            "total_credit",
            "status",
            "posted_by",
            "entries",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ReconciliationItemSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import ReconciliationItem

        model = ReconciliationItem
        fields = (
            "id",
            "account_reference",
            "cbs_amount",
            "gl_amount",
            "variance",
            "status",
            "resolution_notes",
        )


class ReconciliationBatchSerializer(serializers.ModelSerializer):
    items = ReconciliationItemSerializer(many=True, read_only=True)

    class Meta:
        from .models import ReconciliationBatch

        model = ReconciliationBatch
        fields = (
            "id",
            "tenant",
            "pool",
            "reconciliation_date",
            "source_system",
            "total_records",
            "matched_records",
            "exception_count",
            "variance_amount",
            "status",
            "control_total_status",
            "performed_by",
            "notes",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "created_at", "updated_at")

