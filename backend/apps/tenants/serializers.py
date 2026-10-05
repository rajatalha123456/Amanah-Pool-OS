from rest_framework import serializers
from .models import Tenant, LegalEntity


class LegalEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalEntity
        fields = (
            "id",
            "tenant",
            "name",
            "registration_number",
            "jurisdiction",
            "base_currency",
            "timezone",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class TenantSerializer(serializers.ModelSerializer):
    legal_entities = LegalEntitySerializer(many=True, read_only=True)
    user_count = serializers.SerializerMethodField()
    pool_count = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = (
            "id",
            "name",
            "code",
            "domain",
            "data_residency",
            "is_suspended",
            "is_active",
            "user_count",
            "pool_count",
            "legal_entities",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_user_count(self, obj):
        return obj.users.count() if hasattr(obj, "users") else 0

    def get_pool_count(self, obj):
        return obj.pools.count() if hasattr(obj, "pools") else 0
