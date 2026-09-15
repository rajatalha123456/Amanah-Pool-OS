from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, MeView, MfaSetupView, MfaVerifyView

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("mfa/setup/", MfaSetupView.as_view(), name="auth-mfa-setup"),
    path("mfa/verify/", MfaVerifyView.as_view(), name="auth-mfa-verify"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
]
