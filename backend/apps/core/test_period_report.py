from io import StringIO

from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant


class PeriodReportTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_project_data", tenant_code="RPT-T", allow_non_debug=True, stdout=StringIO())
        cls.tenant = Tenant.objects.get(code="RPT-T")

    def setUp(self):
        set_current_tenant(self.tenant)

    def tearDown(self):
        set_current_tenant(None)

    def get(self, role, query="start=2026-07-01&end=2026-09-30"):
        user = User.objects.filter(tenant=self.tenant, role=role).order_by("email").first()
        self.client.force_authenticate(user=user)
        return self.client.get(f"/api/v1/core/period-report/?{query}", HTTP_X_TENANT_CODE="RPT-T")

    def test_report_has_a_row_per_pool_with_real_signed_figures(self):
        response = self.get("auditor")
        self.assertEqual(response.status_code, 200, response.data)
        rows = {r["pool_code"]: r for r in response.data["pools"]}
        self.assertEqual(len(rows), 4)
        bank = next(r for r in rows.values() if r["operating_model"] == "bank_pool" and r["signed_runs"])
        self.assertGreater(float(bank["distributable_profit"]), 0)
        self.assertEqual(len(response.data["content_hash"]), 64)
        circle = next(r for r in rows.values() if r["operating_model"] == "community_circle")
        self.assertIn("contributions_received", circle)

    def test_a_pool_without_a_signed_run_has_no_profit_figure(self):
        rows = self.get("auditor", "start=2020-01-01&end=2020-01-31").data["pools"]
        bank = next(r for r in rows if r["operating_model"] == "bank_pool")
        self.assertEqual(bank["signed_runs"], 0)
        self.assertNotIn("distributable_profit", bank)

    def test_same_data_gives_the_same_seal_and_csv_carries_it(self):
        first = self.get("risk_compliance").data["content_hash"]
        self.assertEqual(first, self.get("auditor").data["content_hash"])
        csv_response = self.get("auditor", "start=2026-07-01&end=2026-09-30&export=csv")
        self.assertIn(first, csv_response.content.decode())

    def test_investors_and_makers_cannot_read_it(self):
        self.assertEqual(self.get("investor_member").status_code, 403)
        self.assertEqual(self.get("finance_maker").status_code, 403)

    def test_bad_dates_are_rejected(self):
        self.assertEqual(self.get("auditor", "start=2026-09-30&end=2026-07-01").status_code, 400)
        self.assertEqual(self.get("auditor", "start=x&end=y").status_code, 400)
