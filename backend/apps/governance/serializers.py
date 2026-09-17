from rest_framework import serializers

from .models import ExceptionCase


class ExceptionCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExceptionCase
        fields = (
            "id",
            "source_module",
            "source_object_id",
            "pool",
            "severity",
            "title",
            "description",
            "status",
            "detected_by",
            "assigned_to",
            "resolution_notes",
            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "detected_by",
            "resolution_notes",
            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
        )
