from rest_framework import serializers

from .models import IncomeExpenseEvent, JournalBatch, JournalEntry


class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = ("id", "account_name", "entry_type", "amount")
        read_only_fields = fields


class IncomeExpenseEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomeExpenseEvent
        fields = (
            "id",
            "tenant",
            "pool",
            "event_type",
            "category",
            "amount",
            "event_date",
            "description",
            "status",
            "created_by",
            "posted_by",
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

