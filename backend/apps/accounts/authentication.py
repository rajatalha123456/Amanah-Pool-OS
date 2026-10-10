from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import AccessToken

from .models import User

PENDING_MFA_LIFETIME_MINUTES = 5


def issue_pending_mfa_token(user: User) -> str:
    token = AccessToken()
    token["user_id"] = str(user.id)
    token["pending_mfa"] = True
    token.set_exp(lifetime=timedelta(minutes=PENDING_MFA_LIFETIME_MINUTES))
    return str(token)


def resolve_pending_mfa_user(pending_token: str) -> User:
    try:
        token = AccessToken(pending_token)
    except Exception as exc:
        raise InvalidToken("Pending MFA token is invalid or expired.") from exc

    if not token.get("pending_mfa"):
        raise InvalidToken("Token is not a valid pending-MFA token.")

    try:
        return User.objects.get(id=token["user_id"])
    except ObjectDoesNotExist as exc:
        raise InvalidToken("User for this token no longer exists.") from exc


class TenantBoundJWTAuthentication(JWTAuthentication):
    """
    JWT auth that (a) refuses the short-lived pending-MFA token as an API
    credential, and (b) binds the user to the tenant named in the
    X-Tenant-Code header (resolved by TenantMiddleware). A user that belongs
    to a tenant may only operate inside that tenant; only tenant-less
    platform users (platform super admin) may switch.
    """

    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        if token.get("pending_mfa"):
            raise InvalidToken("MFA has not been completed for this token.")
        return token

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, _token = result
        # DRF wraps the Django request; the middleware set .tenant on the original.
        request_tenant = getattr(request, "tenant", None)
        if request_tenant is None:
            # Tenant-exempt paths (health, auth, admin) carry no tenant context.
            return result

        if user.tenant_id is not None and user.tenant_id != request_tenant.id:
            raise PermissionDenied("You do not have access to this tenant.")

        return result
