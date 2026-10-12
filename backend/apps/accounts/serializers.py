from rest_framework import serializers

from .models import ApprovalMatrixRule, User, UserRole


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
            "preferred_language",
        )


class UpdatePreferredLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("preferred_language",)


class UserListSerializer(serializers.ModelSerializer):
    tenant_code = serializers.CharField(source="tenant.code", read_only=True, default=None)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "role",
            "tenant_code",
            "mfa_enabled",
            "is_active",
        )


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "role", "tenant")

    def validate_role(self, value):
        if value not in UserRole.values:
            raise serializers.ValidationError("Not a valid role.")
        return value


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name", "role", "tenant", "is_active", "preferred_language")
        extra_kwargs = {
            "full_name": {"required": False},
            "role": {"required": False},
            "tenant": {"required": False},
            "is_active": {"required": False},
            "preferred_language": {"required": False},
        }

    def validate_role(self, value):
        if value not in UserRole.values:
            raise serializers.ValidationError("Not a valid role.")
        return value


class ApprovalMatrixRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalMatrixRule
        fields = ("id", "action", "role", "max_amount", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_role(self, value):
        if value in (UserRole.INVESTOR_MEMBER, UserRole.PLATFORM_SUPER_ADMIN, UserRole.AUDITOR):
            raise serializers.ValidationError("This role cannot be given release-approval authority.")
        return value

    def validate_max_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("The limit must be positive (leave empty for unlimited).")
        return value

    def validate(self, attrs):
        # tenant is set by the view, so DRF's own unique-together check cannot see it.
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        action = attrs.get("action", getattr(self.instance, "action", None))
        role = attrs.get("role", getattr(self.instance, "role", None))
        if tenant is not None and action and role:
            qs = ApprovalMatrixRule.objects.filter(tenant=tenant, action=action, role=role)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("A rule for this approval and role already exists - edit it instead.")
        return attrs
