from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

URL = "/api/v1/dashboard/home/"
AUDIENCE_ROLES = [
    UserRole.POOL_MANAGER, UserRole.FINANCE_MAKER, UserRole.FINANCE_CHECKER, UserRole.SHARIAH_BOARD,
    UserRole.SHARIAH_SECRETARIAT, UserRole.RISK_COMPLIANCE, UserRole.AUDITOR, UserRole.AUTHORIZED_SIGNATORY,
    UserRole.PRODUCT_MANAGER,
]


class DashboardTests(APITestCase):
    """BRD 13: every audience gets its own dashboard, computed from data; an empty tenant shows nulls and zeros, not invented figures."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Dash T", code="DASH-T", data_residency="PK")
        set_current_tenant(self.tenant)
        original = self.client.request

        def keep(**kwargs):
            try:
                return original(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = keep

    def tearDown(self):
        set_current_tenant(None)

    def as_role(self, role):
        user = User.objects.create_user(email=f"{role}@example.com", password="p", full_name=role, role=role, tenant=self.tenant)
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def test_every_audience_gets_sections_with_labelled_metrics(self):
        for role in AUDIENCE_ROLES:
            with self.subTest(role=role):
                self.as_role(role)
                response = self.client.get(URL)
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(response.data["role"], role)
                self.assertTrue(response.data["sections"])
                for section in response.data["sections"]:
                    self.assertTrue(section["metrics"], section["title"])
                    for metric in section["metrics"]:
                        self.assertTrue(metric["label"])
                        self.assertIn(metric["tone"], ("normal", "attention"))

    def test_an_empty_tenant_shows_no_invented_figures(self):
        self.as_role(UserRole.POOL_MANAGER)
        metrics = {m["label"]: m["value"] for s in self.client.get(URL).data["sections"] for m in s["metrics"]}
        self.assertIsNone(metrics["Latest recorded daily funds (PKR)"])  # null, not 0
        self.assertEqual(metrics["Pools awaiting activation"], "0")

    def test_the_executive_view_covers_growth_forecast_and_jurisdiction_without_inventing_figures(self):
        self.as_role(UserRole.RISK_COMPLIANCE)
        data = self.client.get(URL, {"audience": "executive"}).data
        titles = [s["title"] for s in data["sections"]]
        self.assertEqual(titles, ["Funds and growth", "Profit and yield", "Liquidity and forecast", "Exceptions", "Jurisdiction view (open pools)"])
        metrics = {m["label"]: m["value"] for s in data["sections"] for m in s["metrics"]}
        self.assertIsNone(metrics["Funds under management (PKR)"])
        self.assertIsNone(metrics["Growth over about 30 days"])
        self.assertIsNone(metrics["Projected funds in 30 days (PKR)"])
        self.as_role(UserRole.INVESTOR_MEMBER)
        self.assertEqual(self.client.get(URL, {"audience": "executive"}).status_code, 404)

    def test_investors_and_the_platform_admin_have_no_staff_dashboard(self):
        for role in (UserRole.INVESTOR_MEMBER, UserRole.PLATFORM_SUPER_ADMIN):
            with self.subTest(role=role):
                self.as_role(role)
                self.assertEqual(self.client.get(URL).status_code, 404)


class HealthTests(APITestCase):
    def test_liveness_and_readiness_answer_without_a_login(self):
        self.assertEqual(self.client.get("/api/v1/health/").status_code, 200)
        ready = self.client.get("/api/v1/health/ready/")
        self.assertEqual((ready.status_code, ready.data["status"]), (200, "ready"))
