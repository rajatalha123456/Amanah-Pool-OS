from datetime import date, timedelta

from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, UserRole
from apps.tenants.models import FeatureFlag, Tenant, feature_enabled


class FlagsAndKeysTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="FK", code="FK-T", data_residency="PK")
        self.other = Tenant.objects.create(name="Other", code="FK-O", data_residency="PK")
        self.admin = User.objects.create_user(email="a@fk.test", password="x", full_name="A", role=UserRole.PLATFORM_SUPER_ADMIN, tenant=self.tenant)
        self.pm = User.objects.create_user(email="p@fk.test", password="x", full_name="P", role=UserRole.POOL_MANAGER, tenant=self.tenant)

    def api(self, user, tenant=None):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}", HTTP_X_TENANT_CODE=(tenant or self.tenant).code)
        return c

    def test_only_the_administrator_sets_a_flag_and_it_is_off_until_set(self):
        self.assertFalse(feature_enabled(self.tenant, "urdu-disclosure"))
        body = {"tenant": str(self.tenant.id), "key": "urdu-disclosure", "enabled": True, "note": "pilot"}
        self.assertEqual(self.api(self.pm).post("/api/v1/tenants/feature-flags/", body, format="json").status_code, 403)
        made = self.api(self.admin).post("/api/v1/tenants/feature-flags/", body, format="json")
        self.assertEqual(made.status_code, 201, made.data)
        self.assertTrue(feature_enabled(self.tenant, "urdu-disclosure"))
        self.assertEqual(self.api(self.pm).get("/api/v1/tenants/feature-flags/effective/").data, {"enabled": ["urdu-disclosure"]})
        off = self.api(self.admin).patch(f"/api/v1/tenants/feature-flags/{made.data['id']}/", {"enabled": False}, format="json")
        self.assertEqual(off.status_code, 200)
        self.assertFalse(feature_enabled(self.tenant, "urdu-disclosure"))

    def test_a_tenant_never_sees_another_tenants_flags(self):
        FeatureFlag.objects.create(tenant=self.other, key="secret", enabled=True)
        listing = self.api(self.pm).get("/api/v1/tenants/feature-flags/").data
        rows = listing if isinstance(listing, list) else listing.get("results", listing)
        self.assertEqual([r for r in rows if r["key"] == "secret"], [])

    def test_key_register_holds_no_key_material_and_flags_an_overdue_rotation(self):
        body = {"tenant": str(self.tenant.id), "purpose": "Database field encryption", "provider": "Bank HSM",
                "key_reference": "hsm://keys/db-main", "rotation_interval_days": 90}
        self.assertEqual(self.api(self.pm).post("/api/v1/tenants/encryption-keys/", body, format="json").status_code, 403)
        made = self.api(self.admin).post("/api/v1/tenants/encryption-keys/", body, format="json")
        self.assertEqual(made.status_code, 201, made.data)
        self.assertTrue(made.data["overdue"], "never rotated counts as overdue")
        url = f"/api/v1/tenants/encryption-keys/{made.data['id']}/rotated/"
        self.assertEqual(self.api(self.admin).post(url, {"rotated_on": str(date.today() + timedelta(days=1))}, format="json").status_code, 400)
        ok = self.api(self.admin).post(url, {"rotated_on": str(date.today() - timedelta(days=10))}, format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertFalse(ok.data["overdue"])
        old = self.api(self.admin).post(url, {"rotated_on": str(date.today() - timedelta(days=200))}, format="json")
        self.assertTrue(old.data["overdue"])
        self.assertNotIn("key_material", old.data)
