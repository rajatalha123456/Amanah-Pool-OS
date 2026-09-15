from rest_framework import serializers

from .models import User


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class MfaSetupSerializer(serializers.Serializer):
    pending_token = serializers.CharField()


class MfaVerifySerializer(serializers.Serializer):
    pending_token = serializers.CharField()
    code = serializers.RegexField(regex=r"^\d{6}$", error_messages={
        "invalid": "Code must be 6 digits",
    })


class UserSerializer(serializers.ModelSerializer):
    tenant_code = serializers.CharField(source="tenant.code", read_only=True, default=None)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "role",
            "tenant",
            "tenant_code",
            "mfa_enabled",
        )
