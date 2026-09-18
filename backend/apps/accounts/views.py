import base64
import io
import secrets
import string

import pyotp
import qrcode
from django.contrib.auth import authenticate
from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.audit import log_action

from .authentication import resolve_pending_mfa_user
from .models import User
from .permissions import HasAnyRole, IsPlatformSuperAdmin, IsPoolManager
from .serializers import (
    LoginSerializer,
    MfaSetupSerializer,
    MfaVerifySerializer,
    UserCreateSerializer,
    UserListSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


def _generate_password(length=14):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

TOTP_ISSUER = "Amanah Pool OS"


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        if user is None:
            return Response({"detail": "Invalid email or password."}, status=401)

        # MFA is temporarily disabled (dev/testing convenience) - issue tokens
        # directly instead of routing through /verify-mfa. The MFA views/flow
        # below are left in place so it can be re-enabled by reverting this.
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )


class MfaSetupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MfaSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = resolve_pending_mfa_user(serializer.validated_data["pending_token"])
        except InvalidToken as exc:
            return Response({"detail": str(exc)}, status=401)

        if not user.totp_secret:
            user.totp_secret = pyotp.random_base32()
            user.save(update_fields=["totp_secret"])

        provisioning_uri = pyotp.totp.TOTP(user.totp_secret).provisioning_uri(
            name=user.email, issuer_name=TOTP_ISSUER
        )

        qr_image = qrcode.make(provisioning_uri)
        buffer = io.BytesIO()
        qr_image.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        print(f"[MFA SETUP] {user.email} TOTP secret: {user.totp_secret}")

        return Response(
            {
                "secret": user.totp_secret,
                "qr_code_base64": f"data:image/png;base64,{qr_base64}",
            }
        )


class MfaVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MfaVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = resolve_pending_mfa_user(serializer.validated_data["pending_token"])
        except InvalidToken as exc:
            return Response({"detail": str(exc)}, status=401)

        if not user.totp_secret:
            return Response({"detail": "MFA has not been set up for this user."}, status=400)

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(serializer.validated_data["code"], valid_window=1):
            return Response({"detail": "Invalid or expired code."}, status=401)

        if not user.mfa_enabled:
            user.mfa_enabled = True
            user.save(update_fields=["mfa_enabled"])

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class PoolManagerOnlyTestView(APIView):
    """Temporary endpoint to demonstrate IsPoolManager. Remove once real endpoints exist."""

    permission_classes = [IsAuthenticated, IsPoolManager]

    def get(self, request):
        return Response({"detail": "Hello, pool manager."})


class FinanceOnlyTestView(APIView):
    """Temporary endpoint to demonstrate HasAnyRole. Remove once real endpoints exist."""

    permission_classes = [IsAuthenticated, HasAnyRole(["finance_maker", "finance_checker"])]

    def get(self, request):
        return Response({"detail": "Hello, finance."})


class UserManagementViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Platform Super Admin user administration. No hard delete is exposed
    on purpose - deactivation (is_active=False, via PATCH) is the only
    way to remove a user's access, so history/audit trails referencing
    them stay intact.
    """

    def get_queryset(self):
        # Deliberately NOT tenant-scoped via TenantScopedManager (User
        # isn't a TenantScopedModel) - a platform_super_admin needs to
        # see users across all tenants; everyone else is restricted to
        # their own tenant below.
        user = self.request.user
        queryset = User.objects.all().order_by("email")
        if user.role != "platform_super_admin":
            queryset = queryset.filter(tenant=user.tenant)
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserListSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), IsPlatformSuperAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        password = _generate_password()
        user = serializer.save()
        user.set_password(password)
        user.save(update_fields=["password"])

        log_action(
            tenant=user.tenant,
            actor=request.user,
            action="create",
            model_name="User",
            object_id=str(user.id),
            changes={"email": user.email, "role": user.role, "tenant_id": str(user.tenant_id) if user.tenant_id else None},
            request=request,
        )

        response_data = UserListSerializer(user).data
        response_data["generated_password"] = password
        return Response(response_data, status=201)

    def perform_update(self, serializer):
        instance = self.get_object()
        previous_is_active = instance.is_active
        previous_role = instance.role

        user = serializer.save()

        action_name = "update"
        if previous_is_active and not user.is_active:
            action_name = "deactivate"
        elif not previous_is_active and user.is_active:
            action_name = "activate"

        log_action(
            tenant=user.tenant,
            actor=self.request.user,
            action=action_name,
            model_name="User",
            object_id=str(user.id),
            changes={
                "role": {"before": previous_role, "after": user.role},
                "is_active": {"before": previous_is_active, "after": user.is_active},
            },
            request=self.request,
        )
