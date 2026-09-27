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
