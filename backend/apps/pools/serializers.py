from rest_framework import serializers

from apps.products.serializers import ContractTemplateBasicSerializer

from .models import Pool, PoolVersion


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
