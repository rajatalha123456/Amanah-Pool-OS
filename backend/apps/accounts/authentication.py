from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist
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
