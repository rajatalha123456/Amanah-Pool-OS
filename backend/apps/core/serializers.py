from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "tenant",
            "actor",
            "actor_email",
            "action",
            "model_name",
            "object_id",
            "changes",
            "reason",
            "ip_address",
            "created_at",
        )
        read_only_fields = fields
