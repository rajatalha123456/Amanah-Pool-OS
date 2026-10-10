from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)
    actor_role = serializers.CharField(source="actor.role", read_only=True, default=None)
    actor_name = serializers.CharField(source="actor.full_name", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "tenant",
            "actor",
            "actor_email",
            "actor_role",
            "actor_name",
            "action",
            "model_name",
            "object_id",
            "changes",
            "reason",
            "ip_address",
            "created_at",
        )
        read_only_fields = fields

