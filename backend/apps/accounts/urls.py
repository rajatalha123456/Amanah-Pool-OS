from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    FinanceOnlyTestView,
    LoginView,
    MeView,
    MfaSetupView,
    MfaVerifyView,
    PoolManagerOnlyTestView,
    UserManagementViewSet,
)

router = DefaultRouter()
router.register("users", UserManagementViewSet, basename="user-management")

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("mfa/setup/", MfaSetupView.as_view(), name="auth-mfa-setup"),
    path("mfa/verify/", MfaVerifyView.as_view(), name="auth-mfa-verify"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path(
        "test-permissions/pool-manager-only/",
        PoolManagerOnlyTestView.as_view(),
        name="test-pool-manager-only",
    ),
    path(
        "test-permissions/finance-only/",
        FinanceOnlyTestView.as_view(),
        name="test-finance-only",
    ),
] + router.urls
