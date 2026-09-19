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
