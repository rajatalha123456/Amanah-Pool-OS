from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import AllocationLine, AllocationRun, DepositorStatement, ProfitSharingRatio, WeightageBand
from .validators import check_no_overlap


class WeightageBandSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightageBand
        fields = (
            "id",
            "tenant",
            "pool",
            "participant_class",
            "weightage",
            "effective_from",
            "effective_to",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "status", "created_at", "updated_at")

    def validate(self, attrs):
        pool = attrs.get("pool", getattr(self.instance, "pool", None))
        participant_class = attrs.get(
            "participant_class", getattr(self.instance, "participant_class", None)
        )
        effective_from = attrs.get(
            "effective_from", getattr(self.instance, "effective_from", None)
        )
        effective_to = attrs.get("effective_to", getattr(self.instance, "effective_to", None))

        try:
            check_no_overlap(
                WeightageBand,
                pool=pool,
                effective_from=effective_from,
                effective_to=effective_to,
                exclude_id=self.instance.id if self.instance else None,
                extra_filter={"participant_class": participant_class},
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message) from exc

        return attrs


class PSRSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfitSharingRatio
        fields = (
            "id",
            "tenant",
            "pool",
            "depositor_share",
            "mudarib_share",
            "effective_from",
            "effective_to",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "status", "created_at", "updated_at")

    def validate(self, attrs):
        depositor_share = attrs.get(
            "depositor_share", getattr(self.instance, "depositor_share", None)
        )
        mudarib_share = attrs.get(
            "mudarib_share", getattr(self.instance, "mudarib_share", None)
        )

        if depositor_share is not None and mudarib_share is not None:
            if depositor_share + mudarib_share != Decimal("100.00"):
                raise serializers.ValidationError(
                    "depositor_share and mudarib_share must add up to 100.00."
                )

        pool = attrs.get("pool", getattr(self.instance, "pool", None))
        effective_from = attrs.get(
            "effective_from", getattr(self.instance, "effective_from", None)
        )
        effective_to = attrs.get("effective_to", getattr(self.instance, "effective_to", None))

        try:
            check_no_overlap(
                ProfitSharingRatio,
                pool=pool,
                effective_from=effective_from,
                effective_to=effective_to,
                exclude_id=self.instance.id if self.instance else None,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message) from exc

        return attrs


class AllocationLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = AllocationLine
        fields = (
            "id",
            "participant_class",
            "daily_funds",
            "weightage",
            "weighted_funds",
            "allocated_amount",
        )
        read_only_fields = fields


class AllocationRunSerializer(serializers.ModelSerializer):
    lines = AllocationLineSerializer(many=True, read_only=True)
    journal_batch = serializers.SerializerMethodField()
    shariah_review_required = serializers.BooleanField(read_only=True)

    class Meta:
        model = AllocationRun
        fields = (
            "id",
            "tenant",
            "pool",
            "value_date",
            "gross_income",
            "direct_expenses",
            "distributable_amount",
            "total_weighted_funds",
            "depositor_pool_share",
            "mudarib_share",
            "status",
            "calculation_hash",
            "created_by",
            "checked_by",
            "checked_at",
            "rejection_reason",
            "shariah_review_required",
            "shariah_signed_off_by",
            "shariah_signed_off_at",
            "shariah_review_note",
            "lines",
            "journal_batch",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_journal_batch(self, obj):
        # Local import to avoid a hard app-load-order dependency between
        # allocation and accounting at module import time.
        from apps.accounting.serializers import JournalBatchSerializer

        batch = getattr(obj, "journal_batch", None)
        return JournalBatchSerializer(batch).data if batch else None


class AllocationRunInputSerializer(serializers.Serializer):
    """
    Shared input shape for both POST /allocation-runs/simulate/ and
    POST /allocation-runs/. `pool` is assigned in __init__ rather than as
    a class-level PrimaryKeyRelatedField(queryset=Pool.objects.all()) -
    see the identical fix in pools.serializers.BulkBalanceImportSerializer
    (README: "Balance Import & Validation" implementation note) for why a
    class-level queryset against a TenantScopedManager permanently bakes
    in an empty result at import time.
    """

    value_date = serializers.DateField()
    gross_income = serializers.DecimalField(max_digits=18, decimal_places=2)
    direct_expenses = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=Decimal("0"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.pools.models import Pool

        self.fields["pool"] = serializers.PrimaryKeyRelatedField(queryset=Pool.objects.all())


class DepositorStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositorStatement
        fields = (
            "id",
            "allocation_run",
            "participant_class",
            "period_start",
            "period_end",
            "opening_balance",
            "net_deposits",
            "profit_allocated",
            "closing_balance",
            "narrative",
            "generated_at",
        )
        read_only_fields = fields
