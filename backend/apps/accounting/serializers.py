from rest_framework import serializers

from .models import JournalBatch, JournalEntry


class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = ("id", "account_name", "entry_type", "amount")
        read_only_fields = fields


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
