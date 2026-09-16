from rest_framework import serializers

from apps.products.serializers import ContractTemplateBasicSerializer

from .models import Asset, AssetAssignment, BalanceImportBatch, DailyBalance, Pool, PoolVersion


class ProductBasicSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    code = serializers.CharField()
    status = serializers.CharField()
    contract_template = ContractTemplateBasicSerializer()


class PoolSerializer(serializers.ModelSerializer):
    product_detail = serializers.SerializerMethodField()

    class Meta:
        model = Pool
        fields = (
            "id",
            "tenant",
            "name",
            "code",
            "product",
            "product_detail",
            "status",
            "effective_date",
            "closed_date",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "status", "closed_date", "created_at", "updated_at")

    def validate_code(self, value):
        # Pool.code is only enforced unique via a composite
        # UniqueConstraint(tenant, code) at the DB level, which DRF does
        # not auto-validate (only a plain unique=True field gets that for
        # free). Without this check, a duplicate code raises a raw
        # IntegrityError that surfaces as an unhandled 500 instead of a
        # clean 400 - found and fixed while building the New Pool Wizard.
        tenant = self.context["request"].user.tenant
        queryset = Pool.objects.filter(tenant=tenant, code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A pool with this code already exists.")
        return value

    def get_product_detail(self, obj):
        product = obj.product
        return ProductBasicSerializer(
            {
                "id": product.id,
                "name": product.name,
                "code": product.code,
                "status": product.status,
                "contract_template": product.contract_template,
            }
        ).data


class PoolVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoolVersion
        fields = (
            "id",
            "pool",
            "version_number",
            "snapshot",
            "created_by",
            "is_current",
            "created_at",
        )
        read_only_fields = fields


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = (
            "id",
            "tenant",
            "reference_code",
            "asset_type",
            "description",
            "face_value",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "status", "created_at", "updated_at")


class AssetAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetAssignment
        fields = (
            "id",
            "tenant",
            "asset",
            "pool",
            "assigned_date",
            "unassigned_date",
            "assigned_by",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "tenant", "unassigned_date", "assigned_by", "created_at", "updated_at")

    def validate(self, attrs):
        # Only relevant on create - unassign is a separate action, and
        # updates to an existing assignment shouldn't re-trigger this.
        if self.instance is None:
            asset = attrs.get("asset")
            if asset is not None and asset.assignments.filter(unassigned_date__isnull=True).exists():
                raise serializers.ValidationError(
                    "Asset already assigned to another pool. Unassign first."
                )
        return attrs


class DailyBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyBalance
        fields = (
            "id",
            "tenant",
            "pool",
            "participant_class",
            "value_date",
            "balance_amount",
            "source",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class BalanceImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceImportBatch
        fields = (
            "id",
            "tenant",
            "pool",
            "value_date",
            "total_records",
            "matched_records",
            "exception_count",
            "control_total_expected",
            "control_total_actual",
            "status",
            "imported_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class BulkBalanceImportRecordSerializer(serializers.Serializer):
    participant_class = serializers.CharField()
    balance_amount = serializers.DecimalField(max_digits=18, decimal_places=2)


class BulkBalanceImportSerializer(serializers.Serializer):
    value_date = serializers.DateField()
    control_total_expected = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    records = BulkBalanceImportRecordSerializer(many=True)

    def __init__(self, *args, **kwargs):
        # `pool` must be declared here (not as a class-level field) so its
        # queryset is built fresh per-instantiation, after TenantMiddleware
        # has set the tenant context - see the identical issue with
        # class-level ModelViewSet.queryset documented in README ("BE-007
        # bug"). A class-level `PrimaryKeyRelatedField(queryset=Pool.objects.all())`
        # would bake in an empty queryset at import time that .all() can
        # never undo.
        super().__init__(*args, **kwargs)
        self.fields["pool"] = serializers.PrimaryKeyRelatedField(queryset=Pool.objects.all())

    def validate_records(self, records):
        if not records:
            raise serializers.ValidationError("At least one record is required.")
        return records
