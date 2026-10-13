from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    AllocationLine,
    AllocationRun,
    AllocationRunStatus,
    DepositorStatement,
    ProfitSharingRatio,
    ReservePolicy,
    WeightageBand,
)
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

    def validate_weightage(self, value):
        # A weightage multiplies the balance; zero or negative would remove or reverse a class's share of the profit.
        if value <= 0:
            raise serializers.ValidationError("The weightage must be greater than zero.")
        return value

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
            "wakalah_fee_pct",
            "effective_from",
            "effective_to",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "status", "created_at", "updated_at")

    def validate(self, attrs):
        fee = attrs.get("wakalah_fee_pct", getattr(self.instance, "wakalah_fee_pct", None)) or Decimal("0")
        pool_for_fee = attrs.get("pool", getattr(self.instance, "pool", None))
        if fee < 0 or fee > 100:
            raise serializers.ValidationError({"wakalah_fee_pct": "The fee must be between 0 and 100 (% per annum)."})
        if fee > 0 and pool_for_fee is not None:
            if pool_for_fee.product.contract_template.contract_type != "wakalah":
                raise serializers.ValidationError(
                    {"wakalah_fee_pct": "A Wakalah fee can only be set on a pool whose contract is Wakalah."}
                )
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

        # The jurisdiction rule pack caps the manager's share of profit (BR-001: rule pack is enforced, not decorative).
        if pool is not None and mudarib_share is not None:
            from apps.pools.config_snapshot import bound_rule_pack

            pack = bound_rule_pack(pool)
            cap = (pack.rules_config or {}).get("mudarib_share_cap_pct") if pack else None
            if cap is not None and mudarib_share > Decimal(str(cap)):
                raise serializers.ValidationError(
                    {"mudarib_share": f"Rule pack {pack.code} caps the manager's profit share at {cap}%."}
                )

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
    account_number = serializers.CharField(source="account.account_number", read_only=True, default=None)
    participant_name = serializers.CharField(source="account.participant.full_name", read_only=True, default=None)

    class Meta:
        model = AllocationLine
        fields = (
            "id",
            "participant_class",
            "account",
            "account_number",
            "participant_name",
            "daily_funds",
            "weightage",
            "weighted_funds",
            "allocated_amount",
        )
        read_only_fields = fields


_STAGE_ORDINAL = {
    AllocationRunStatus.SIMULATED: 0,
    AllocationRunStatus.PENDING_APPROVAL: 1,
    AllocationRunStatus.CHECKED: 2,
    AllocationRunStatus.SHARIAH_REVIEW: 3,
    AllocationRunStatus.SIGNED: 4,
    AllocationRunStatus.REVERSED: 4,
}


def _person(user):
    return (user.full_name or user.email) if user else None


def _iso(value):
    return value.isoformat() if value else None


class AllocationRunSerializer(serializers.ModelSerializer):
    lines = AllocationLineSerializer(many=True, read_only=True)
    journal_batch = serializers.SerializerMethodField()
    shariah_review_required = serializers.BooleanField(read_only=True)
    stages = serializers.SerializerMethodField()
    control_gates = serializers.SerializerMethodField()

    class Meta:
        model = AllocationRun
        fields = (
            "id",
            "tenant",
            "pool",
            "period_start",
            "value_date",
            "gross_income",
            "direct_expenses",
            "distributable_amount",
            "total_weighted_funds",
            "depositor_pool_share",
            "mudarib_share",
            "per_amount",
            "irr_amount",
            "rounding_residual",
            "is_loss",
            "config_snapshot",
            "status",
            "calculation_hash",
            "replaces_run",
            "is_restatement",
            "restatement_reason",
            "created_by",
            "checked_by",
            "checked_at",
            "released_by",
            "released_at",
            "stages",
            "control_gates",
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

    def _ordinal(self, run):
        if run.status != AllocationRunStatus.REJECTED:
            return _STAGE_ORDINAL.get(run.status, 0)
        # A rejected run stopped where its last completed stage left it.
        if run.shariah_signed_off_at:
            return 3
        return 2 if run.checked_at else 1

    def get_stages(self, obj):
        """The approval ceremony (UI Catalogue screen 14): prepared, independent check, Shariah review, final release."""

        ordinal = self._ordinal(obj)
        rejected = obj.status == AllocationRunStatus.REJECTED
        shariah = obj.shariah_review_required

        def stage(key, label, owner, index, by, at):
            if ordinal > index:
                state = "completed"
            elif ordinal == index:
                state = "rejected" if rejected else ("draft" if obj.status == AllocationRunStatus.SIMULATED else "in_review")
            else:
                state = "waiting"
            return {"key": key, "label": label, "owner": owner, "state": state, "by": _person(by), "at": _iso(at)}

        stages = [
            stage("prepared", "Prepared", "Finance Maker", 0, obj.created_by, obj.created_at),
            stage("independent_check", "Independent check", "Finance Checker", 1, obj.checked_by, obj.checked_at),
        ]
        release_index = 2
        if shariah:
            stages.append(
                stage("shariah_review", "Shariah review", "Shariah Secretariat / Board", 2,
                      obj.shariah_signed_off_by, obj.shariah_signed_off_at)
            )
            release_index = 3
        stages.append(
            stage("final_release", "Final release", "Authorized Signatory", release_index, obj.released_by, obj.released_at)
        )
        return stages

    def get_control_gates(self, obj):
        from apps.accounting.models import ReconciliationBatch

        reconciliation = (
            ReconciliationBatch._base_manager.filter(
                tenant_id=obj.tenant_id, pool_id=obj.pool_id, reconciliation_date__lte=obj.value_date
            )
            .order_by("-reconciliation_date")
            .first()
        )
        snapshot = obj.config_snapshot or {}
        return [
            {
                "key": "reconciled",
                "label": "Reconciled",
                "passed": bool(reconciliation and reconciliation.status in ("matched", "cleared")),
            },
            {
                "key": "shariah_parameters_sealed",
                "label": "Shariah parameters sealed",
                "passed": bool(snapshot.get("psr") and snapshot.get("weightage_bands") is not None and obj.calculation_hash),
            },
            {
                "key": "shariah_review",
                "label": "Shariah review complete" if obj.shariah_review_required else "Shariah review not required",
                "passed": (not obj.shariah_review_required) or obj.shariah_signed_off_at is not None,
            },
            {"key": "final_authority", "label": "Final authority", "passed": obj.released_at is not None},
        ]

    def get_journal_batch(self, obj):
        # Local import to avoid a hard app-load-order dependency between
        # allocation and accounting at module import time.
        from apps.accounting.serializers import JournalBatchSerializer

        batch = getattr(obj, "journal_batch", None)
        return JournalBatchSerializer(batch).data if batch else None


class ReservePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReservePolicy
        fields = (
            "id",
            "tenant",
            "pool",
            "reserve_type",
            "rate_percentage",
            "cap_percentage",
            "current_balance",
            "is_active",
            "created_at",
            "updated_at",
        )
        # The balance is system-controlled: it moves only when a signed run appropriates to the reserve or a
        # reversal takes it back (allocation/reserves.py). No API caller may set it.
        read_only_fields = ("id", "tenant", "current_balance", "created_at", "updated_at")

    def validate(self, attrs):
        """The rule pack's PER/IRR ceiling (a % of pool funds) limits the policy's balance cap."""
        pool = attrs.get("pool", getattr(self.instance, "pool", None))
        reserve_type = attrs.get("reserve_type", getattr(self.instance, "reserve_type", None))
        cap = attrs.get("cap_percentage", getattr(self.instance, "cap_percentage", None))
        if pool is not None and cap is not None and reserve_type in ("per", "irr"):
            from apps.pools.config_snapshot import bound_rule_pack

            pack = bound_rule_pack(pool)
            ceiling = (pack.rules_config or {}).get(f"{reserve_type}_ceiling_pct") if pack else None
            if ceiling is not None and Decimal(str(cap)) > Decimal(str(ceiling)):
                raise serializers.ValidationError(
                    {"cap_percentage": f"Rule pack {pack.code} limits the {reserve_type.upper()} balance to {ceiling}% of pool funds."}
                )
        return attrs


class RestatementInputSerializer(serializers.Serializer):
    restatement_reason = serializers.CharField(required=True)
    gross_income = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, default=None
    )
    direct_expenses = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, default=None
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


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

    value_date = serializers.DateField(help_text="Period end date.")
    period_start = serializers.DateField(
        required=False, allow_null=True, default=None, help_text="Period start; omit for a single-day run."
    )
    # Omit both to derive income/expenses from the pool's posted ledger events (BR-005).
    # A hand-typed gross_income is a manual override and needs an override_reason.
    gross_income = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, allow_null=True, default=None)
    direct_expenses = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, allow_null=True, default=None)
    override_reason = serializers.CharField(required=False, allow_blank=True, default="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.pools.models import Pool

        self.fields["pool"] = serializers.PrimaryKeyRelatedField(queryset=Pool.objects.all())

    def validate(self, attrs):
        period_start = attrs.get("period_start")
        if period_start and period_start > attrs["value_date"]:
            raise serializers.ValidationError({"period_start": "period_start cannot be after value_date."})
        return attrs


class DepositorStatementSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source="account.account_number", read_only=True, default=None)
    participant_name = serializers.CharField(source="account.participant.full_name", read_only=True, default=None)

    class Meta:
        model = DepositorStatement
        fields = (
            "id",
            "allocation_run",
            "participant_class",
            "account",
            "account_number",
            "participant_name",
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
