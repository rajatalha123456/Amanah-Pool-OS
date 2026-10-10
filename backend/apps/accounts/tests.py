from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

from .models import User, UserRole


class PreferredLanguageApiTests(APITestCase):
    """
    Storage-only preference: GET /auth/me/ returns preferred_language and
    PATCH /auth/me/ lets a user change it. No backend message translation
    happens here - see README's Preferred Language note for scope.
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Language Tenant", code="LANG-1", data_residency="PK")
        set_current_tenant(self.tenant)
        self.user = User.objects.create_user(
            email="lang@example.com",
            password="password",
            full_name="Language User",
            role=UserRole.POOL_MANAGER,
            tenant=self.tenant,
        )
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        set_current_tenant(None)

    def test_me_defaults_to_english(self):
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferred_language"], "en")

    def test_patch_me_updates_preferred_language(self):
        response = self.client.patch(reverse("auth-me"), {"preferred_language": "ur"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferred_language"], "ur")

        self.user.refresh_from_db()
        self.assertEqual(self.user.preferred_language, "ur")

        # Confirm it persists and is returned on a subsequent GET.
        get_response = self.client.get(reverse("auth-me"))
        self.assertEqual(get_response.data["preferred_language"], "ur")

    def test_patch_me_rejects_invalid_language(self):
        response = self.client.patch(reverse("auth-me"), {"preferred_language": "fr"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_me_cannot_change_role_or_tenant(self):
        other_tenant = Tenant.objects.create(name="Other Tenant", code="LANG-2", data_residency="PK")
        response = self.client.patch(
            reverse("auth-me"),
            {"preferred_language": "ur", "role": UserRole.PLATFORM_SUPER_ADMIN, "tenant": str(other_tenant.id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, UserRole.POOL_MANAGER)
        self.assertEqual(self.user.tenant_id, self.tenant.id)


class TenantBindingAndMfaTests(APITestCase):
    """Real JWT auth (not force_authenticate) so TenantBoundJWTAuthentication runs."""

    def setUp(self):
        self.tenant_a = Tenant.objects.create(name="Tenant A", code="BIND-A", data_residency="PK")
        self.tenant_b = Tenant.objects.create(name="Tenant B", code="BIND-B", data_residency="PK")
        self.auditor = User.objects.create_user(
            email="auditor-a@example.com", password="Password123!", full_name="Auditor A",
            role=UserRole.AUDITOR, tenant=self.tenant_a,
        )
        self.super_admin = User.objects.create_user(
            email="root@example.com", password="Password123!", full_name="Root",
            role=UserRole.PLATFORM_SUPER_ADMIN, tenant=None,
        )

    def tearDown(self):
        set_current_tenant(None)

    def _bearer(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken

        return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}

    def test_user_can_access_own_tenant(self):
        response = self.client.get(
            reverse("audit-log-list"), HTTP_X_TENANT_CODE="BIND-A", **self._bearer(self.auditor)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_cannot_switch_to_another_tenant_via_header(self):
        response = self.client.get(
            reverse("audit-log-list"), HTTP_X_TENANT_CODE="BIND-B", **self._bearer(self.auditor)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenantless_super_admin_may_select_a_tenant(self):
        response = self.client.get(
            reverse("audit-log-list"), HTTP_X_TENANT_CODE="BIND-B", **self._bearer(self.super_admin)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_pending_mfa_token_is_not_a_valid_api_credential(self):
        from .authentication import issue_pending_mfa_token

        response = self.client.get(
            reverse("audit-log-list"),
            HTTP_X_TENANT_CODE="BIND-A",
            HTTP_AUTHORIZATION=f"Bearer {issue_pending_mfa_token(self.auditor)}",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_requires_mfa_when_enforced(self):
        response = self.client.post(
            reverse("auth-login"), {"email": "auditor-a@example.com", "password": "Password123!"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("mfa_setup_required"))
        self.assertIn("pending_token", response.data)
        self.assertNotIn("access", response.data)

    def test_super_admin_has_no_implicit_role_bypass(self):
        # Reserve policy writes are Pool Manager only; super admin must not pass.
        response = self.client.post(
            reverse("reserve-policy-list"), {}, HTTP_X_TENANT_CODE="BIND-A", **self._bearer(self.super_admin)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
