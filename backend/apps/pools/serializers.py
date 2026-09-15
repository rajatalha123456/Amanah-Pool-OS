from rest_framework import serializers

from apps.products.serializers import ContractTemplateBasicSerializer

from .models import Asset, AssetAssignment, Pool, PoolVersion


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
