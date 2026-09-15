import base64
import io

import pyotp
import qrcode
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import issue_pending_mfa_token, resolve_pending_mfa_user
from .permissions import HasAnyRole, IsPoolManager
from .serializers import (
    LoginSerializer,
    MfaSetupSerializer,
    MfaVerifySerializer,
    UserSerializer,
)

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

        pending_token = issue_pending_mfa_token(user)

        if not user.mfa_enabled:
            return Response(
                {"mfa_setup_required": True, "pending_token": pending_token}
            )

        return Response({"mfa_required": True, "pending_token": pending_token})


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
