"""
Access-control regression suite (audit P0-1): replays, against a fully seeded tenant, every write the audit
found open to the wrong role, and checks the investor deny-by-default scope.
"""

from io import StringIO

from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

ZERO_ID = "00000000-0000-0000-0000-000000000000"


class AccessControlTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_project_data", tenant_code="ACL-T", allow_non_debug=True, stdout=StringIO())
        cls.tenant = Tenant.objects.get(code="ACL-T")

    def setUp(self):
        set_current_tenant(self.tenant)

    def tearDown(self):
        set_current_tenant(None)

    def user(self, role):
        return User.objects.filter(tenant=self.tenant, role=role).order_by("email").first()

    def first(self, model, **filters):
        obj = model._base_manager.filter(tenant=self.tenant, **filters).first()
        return obj.id if obj else ZERO_ID

    def call(self, user, method, url, body=None):
        # A real access token, so the production authentication path (incl. the investor scope) runs.
        from rest_framework_simplejwt.tokens import RefreshToken

        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        response = getattr(self.client, method)(url, body, format="json", HTTP_X_TENANT_CODE="ACL-T")
        set_current_tenant(self.tenant)
        return response

    # -------------------------------------------------------------------------------------------
    def test_investor_cannot_reach_any_staff_endpoint(self):
        from apps.accounting.models import ReconciliationBatch
        from apps.allocation.models import ProfitSharingRatio, WeightageBand
        from apps.circles.models import CircleMember, CircleProposal
        from apps.governance.models import RelatedPartyTransaction, ShariahAuditPlan
        from apps.pools.models import Asset, AssetAssignment, PeriodCloseChecklist, Pool
        from apps.products.models import ContractTemplate, Product

        investor = self.user("investor_member")
        circle = Pool._base_manager.get(tenant=self.tenant, product__operating_model="community_circle")
        member = self.first(CircleMember)
        probes = [
            ("delete", f"/api/v1/allocation/psr-schedules/{self.first(ProfitSharingRatio)}/"),
            ("delete", f"/api/v1/allocation/weightage-bands/{self.first(WeightageBand)}/"),
            ("delete", f"/api/v1/accounting/reconciliation-batches/{self.first(ReconciliationBatch)}/"),
            ("patch", f"/api/v1/circles/circle-members/{member}/"),
            ("post", f"/api/v1/circles/circle-members/swap-turns/{circle.id}/"),
            ("post", f"/api/v1/circles/circle-proposals/{self.first(CircleProposal)}/vote/"),
            ("delete", f"/api/v1/governance/related-party-transactions/{self.first(RelatedPartyTransaction)}/"),
            ("post", f"/api/v1/governance/shariah-audit-plans/{self.first(ShariahAuditPlan)}/approve/"),
            ("patch", f"/api/v1/pools/pools/{self.first(Pool)}/"),
            ("delete", f"/api/v1/pools/assets/{self.first(Asset)}/"),
            ("post", f"/api/v1/pools/asset-assignments/{self.first(AssetAssignment)}/transfer/"),
            ("post", f"/api/v1/pools/period-closes/{self.first(PeriodCloseChecklist)}/lock/"),
            ("patch", f"/api/v1/products/products/{self.first(Product)}/"),
            ("patch", f"/api/v1/products/contract-templates/{self.first(ContractTemplate)}/"),
            ("post", "/api/v1/ai/fraud-collusion/detect/"),
            ("get", "/api/v1/auth/users/"),
            ("get", "/api/v1/circles/circle-members/"),
            ("get", "/api/v1/accounting/income-expense-events/"),
            ("get", "/api/v1/governance/exceptions/"),
            ("get", "/api/v1/governance/support-requests/"),
            ("get", "/api/v1/accounting/journal-batches/"),
            ("get", "/api/v1/tenants/"),
        ]
        for method, url in probes:
            with self.subTest(method=method, url=url):
                self.assertEqual(self.call(investor, method, url, {}).status_code, 403)

    def test_investor_self_service_still_works(self):
        investor = self.user("investor_member")
        for url in (
            "/api/v1/investments/capital-accounts/",
            "/api/v1/allocation/allocation-runs/my-statements/",
            "/api/v1/notifications/",
            "/api/v1/auth/me/",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.call(investor, "get", url).status_code, 200)

    def test_approved_economics_and_rulings_are_immutable(self):
        from apps.allocation.models import ProfitSharingRatio, WeightageBand
        from apps.products.models import ContractTemplate, ShariahDecision

        pm = self.user("pool_manager")
        psr = ProfitSharingRatio._base_manager.filter(tenant=self.tenant, status="approved").first()
        r = self.call(pm, "patch", f"/api/v1/allocation/psr-schedules/{psr.id}/", {"depositor_share": "10.00", "mudarib_share": "90.00"})
        self.assertEqual(r.status_code, 400)
        psr.refresh_from_db()
        self.assertNotEqual(str(psr.depositor_share), "10.00")
        band = WeightageBand._base_manager.filter(tenant=self.tenant, status="approved").first()
        self.assertEqual(self.call(pm, "patch", f"/api/v1/allocation/weightage-bands/{band.id}/", {"weightage": "9.99"}).status_code, 400)
        self.assertEqual(self.call(pm, "delete", f"/api/v1/allocation/psr-schedules/{psr.id}/").status_code, 405)

        product_manager = self.user("product_manager")
        template = ContractTemplate._base_manager.filter(tenant=self.tenant, status="approved").first()
        self.assertEqual(
            self.call(product_manager, "patch", f"/api/v1/products/contract-templates/{template.id}/", {"name": "x"}).status_code, 400
        )
        board = self.user("shariah_board")
        decision = ShariahDecision._base_manager.filter(tenant=self.tenant, status="approved").first()
        self.assertEqual(self.call(board, "patch", f"/api/v1/products/shariah-decisions/{decision.id}/", {"title": "x"}).status_code, 400)
        self.assertEqual(self.call(board, "delete", f"/api/v1/products/shariah-decisions/{decision.id}/").status_code, 400)

    def test_wrong_staff_roles_are_refused(self):
        from apps.circles.models import CircleMember
        from apps.investments.models import CapitalAccount
        from apps.pools.models import Pool

        account = CapitalAccount._base_manager.filter(tenant=self.tenant).first()
        other_pool = Pool._base_manager.filter(tenant=self.tenant).exclude(id=account.pool_id).first()
        self.assertEqual(
            self.call(self.user("auditor"), "patch", f"/api/v1/investments/capital-accounts/{account.id}/", {"pool": str(other_pool.id)}).status_code,
            403,
        )
        # Even an allowed role cannot move an account to another pool.
        self.assertEqual(
            self.call(self.user("pool_manager"), "patch", f"/api/v1/investments/capital-accounts/{account.id}/", {"pool": str(other_pool.id)}).status_code,
            400,
        )
        member = CircleMember._base_manager.filter(tenant=self.tenant).first()
        self.assertEqual(
            self.call(self.user("finance_maker"), "patch", f"/api/v1/circles/circle-members/{member.id}/", {"iban": "PK00HACK0000000000000000"}).status_code,
            403,
        )

    def test_model_guards_return_400_not_500(self):
        from apps.accounting.models import IncomeExpenseEvent

        posted = IncomeExpenseEvent._base_manager.filter(tenant=self.tenant, status="posted", event_type="expense").first()
        r = self.call(self.user("finance_maker"), "post", f"/api/v1/accounting/income-expense-events/{posted.id}/reclassify/",
                      {"cost_classification": "indirect_overhead"})
        self.assertEqual(r.status_code, 400)
