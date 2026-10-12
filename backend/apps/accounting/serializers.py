from rest_framework import serializers

from .chart import ACCOUNTS
from .models import AccountMapping, IncomeExpenseEvent, JournalBatch, JournalEntry


class JournalEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = ("id", "account_name", "account_key", "gl_code", "entry_type", "amount")
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
            "allocation_run",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "tenant",
            "allocation_run",
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



class AccountMappingSerializer(serializers.ModelSerializer):
    pool_code = serializers.CharField(source="pool.code", read_only=True, default=None)

    class Meta:
        model = AccountMapping
        fields = ("id", "pool", "pool_code", "account_key", "gl_code", "gl_name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.pools.models import Pool

        self.fields["pool"] = serializers.PrimaryKeyRelatedField(
            queryset=Pool.objects.all(), required=False, allow_null=True
        )

    def validate_account_key(self, value):
        if value not in ACCOUNTS:
            raise serializers.ValidationError(f"Unknown logical account. Choose one of: {', '.join(ACCOUNTS)}.")
        return value

    def validate(self, attrs):
        key = attrs.get("account_key", getattr(self.instance, "account_key", None))
        pool = attrs.get("pool", getattr(self.instance, "pool", None))
        qs = AccountMapping.objects.filter(account_key=key, pool=pool)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A mapping for this account (and pool) already exists - edit it instead.")
        return attrs
