from datetime import date

from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.pools.models import Pool
from apps.products.models import (
    ContractTemplate, ContractType, OperatingModel, Product, ShariahDecision, ShariahDecisionStatus,
)
from apps.products.shariah import shariah_decision_for
from apps.tenants.models import Tenant

from .models import ShariahAuditFinding, ShariahAuditPlan

DECISIONS = "/api/v1/products/shariah-decisions/"
PLANS = "/api/v1/governance/shariah-audit-plans/"


class ShariahRegisterTests(APITestCase):
    """BRD section 8: decision scope, supersession, and the annual Shariah audit report."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Reg T", code="REG-T", data_residency="PK")
        set_current_tenant(self.tenant)
        original = self.client.request

        def keep(**kwargs):
            try:
                return original(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = keep
        self.board = self._user("board", UserRole.SHARIAH_BOARD)
        self.secretariat = self._user("sec", UserRole.SHARIAH_SECRETARIAT)
        self.auditor = self._user("aud", UserRole.AUDITOR)
        self.maker = self._user("maker", UserRole.FINANCE_MAKER)
        self.old = ShariahDecision.objects.create(
            tenant=self.tenant, decision_code="SD-OLD", title="Old ruling", description="d", scope="Retail Mudarabah",
            status=ShariahDecisionStatus.APPROVED, effective_date=date(2025, 1, 1), created_by=self.secretariat,
        )
        template = ContractTemplate.objects.create(
            tenant=self.tenant, name="C", contract_type=ContractType.MUDARABAH_UNRESTRICTED, version="1", clauses={},
            shariah_decision=self.old,
        )
        product = Product.objects.create(
            tenant=self.tenant, name="P", code="P1", operating_model=OperatingModel.BANK_POOL, contract_template=template
        )
        self.pool = Pool.objects.create(tenant=self.tenant, name="Pool", code="PL", product=product, effective_date=date(2026, 1, 1))

    def tearDown(self):
        set_current_tenant(None)

    def _user(self, name, role):
        return User.objects.create_user(email=f"{name}@example.com", password="password", full_name=name.title(), role=role, tenant=self.tenant)

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def test_a_ruling_has_a_scope_and_can_supersede_an_approved_one(self):
        self.as_user(self.secretariat)
        response = self.client.post(DECISIONS, {
            "decision_code": "SD-NEW", "title": "New ruling", "decision_type": "product_approval", "description": "d",
            "scope": "Retail Mudarabah and Wakalah", "supersedes": self.old.id, "effective_date": "2026-01-01",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.data["scope"], "Retail Mudarabah and Wakalah")
        self.assertEqual(response.data["supersedes"], self.old.id)

    def test_a_draft_or_foreign_ruling_cannot_be_superseded_and_a_ruling_cannot_supersede_itself(self):
        draft = ShariahDecision.objects.create(
            tenant=self.tenant, decision_code="SD-D", title="Draft", description="d", status=ShariahDecisionStatus.DRAFT,
            effective_date=date(2026, 1, 1),
        )
        self.as_user(self.secretariat)
        body = {"decision_code": "SD-X", "title": "X", "decision_type": "product_approval", "description": "d", "effective_date": "2026-01-01"}
        self.assertEqual(self.client.post(DECISIONS, {**body, "supersedes": draft.id}, format="json").status_code, 400)

    def test_approving_the_successor_supersedes_the_old_ruling_and_the_contract_follows_the_chain(self):
        new = ShariahDecision.objects.create(
            tenant=self.tenant, decision_code="SD-NEW", title="New", description="d", status=ShariahDecisionStatus.DRAFT,
            effective_date=date(2026, 1, 1), supersedes=self.old, created_by=self.secretariat,
        )
        self.assertEqual(shariah_decision_for(self.pool), self.old)  # in force before approval
        self.as_user(self.board)
        self.assertEqual(self.client.post(f"{DECISIONS}{new.id}/approve/").status_code, 200)
        self.old.refresh_from_db()
        self.assertEqual(self.old.status, ShariahDecisionStatus.SUPERSEDED)
        self.assertEqual(shariah_decision_for(self.pool), new)  # the contract still names SD-OLD; the successor is in force

    def test_a_superseded_ruling_with_no_approved_successor_backs_nothing(self):
        ShariahDecision.objects.filter(pk=self.old.pk).update(status=ShariahDecisionStatus.SUPERSEDED)
        self.assertIsNone(shariah_decision_for(Pool._base_manager.get(pk=self.pool.pk)))  # a fresh read of the pool

    def test_the_annual_audit_report_is_built_from_the_records_and_sealed(self):
        plan = ShariahAuditPlan.objects.create(
            tenant=self.tenant, plan_year=2026, title="2026 plan", target_samples_count=50, tested_samples_count=20,
        )
        ShariahAuditFinding.objects.create(
            tenant=self.tenant, audit_plan=plan, title="Late purification", severity="high", observation="o",
            management_response="Fixed in October.",
        )
        ShariahAuditFinding.objects.create(tenant=self.tenant, audit_plan=plan, title="Missing note", severity="low", observation="o")
        self.as_user(self.board)
        report = self.client.get(PLANS + "annual-report/?year=2026")
        self.assertEqual(report.status_code, 200, report.content)
        data = report.data
        self.assertEqual(data["plans"][0]["coverage_pct"], 40.0)
        self.assertEqual((data["findings"]["total"], data["findings"]["open"], data["findings"]["response_rate_pct"]), (2, 2, 50.0))
        self.assertEqual(data["findings"]["by_severity"], {"high": 1, "low": 1})
        self.assertEqual(len(data["content_hash"]), 64)
        empty = self.client.get(PLANS + "annual-report/?year=2030").data
        self.assertEqual((empty["findings"]["total"], empty["findings"]["response_rate_pct"]), (0, None))  # null, not zero-filled

    def test_only_governance_and_assurance_roles_read_the_annual_report(self):
        self.as_user(self.maker)
        self.assertEqual(self.client.get(PLANS + "annual-report/?year=2026").status_code, 403)
        self.as_user(self.auditor)
        self.assertEqual(self.client.get(PLANS + "annual-report/?year=2026").status_code, 200)
