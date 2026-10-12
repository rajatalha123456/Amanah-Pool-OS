"""BR-001: a pool cannot activate without approved contract, rule pack, accounting mapping and approval matrix."""

from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounting.chart import ACCOUNTS, REQUIRED_BY_MODEL
from apps.accounting.models import AccountMapping
from apps.accounts.models import ApprovalMatrixRule, User, UserRole
from apps.allocation.models import (
    PSRStatus,
    ProfitSharingRatio,
    ReservePolicy,
    ReserveType,
    WeightageBand,
    WeightageBandStatus,
)
from apps.core.context import set_current_tenant
from apps.pools.models import Pool, PoolStatus, PoolVersion
from apps.products.models import (
    ContractTemplate,
    ContractTemplateStatus,
    JurisdictionRulePack,
    Product,
    ProductStatus,
    ShariahDecision,
    ShariahDecisionStatus,
)
from apps.tenants.models import Tenant


class ActivationBase(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Activation", code="ACTIV", data_residency="PK")
        set_current_tenant(self.tenant)
        original_request = self.client.request

        def request_keeping_tenant(**kwargs):
            try:
                return original_request(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = request_keeping_tenant

        self.pm = self._user("pm", UserRole.POOL_MANAGER)
        self.checker = self._user("checker", UserRole.FINANCE_CHECKER)
        self.investor = self._user("investor", UserRole.INVESTOR_MEMBER)
        self.risk = self._user("risk", UserRole.RISK_COMPLIANCE)
        self.finance_checker = self._user("fchecker", UserRole.FINANCE_CHECKER)

        self.decision = ShariahDecision.objects.create(
            tenant=self.tenant, decision_code="SD-ACT-1", title="Mudarabah pool", description="d",
            status=ShariahDecisionStatus.APPROVED, effective_date=date(2026, 1, 1),
            approved_by=self._user("board", UserRole.SHARIAH_BOARD),
        )
        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name="Mudarabah Master", contract_type="mudarabah_unrestricted", version="1",
            clauses={}, shariah_decision=self.decision, status=ContractTemplateStatus.APPROVED,
        )
        self.product = Product.objects.create(
            tenant=self.tenant, name="Retail Mudarabah", code="RM", operating_model="bank_pool",
            contract_template=contract, status=ProductStatus.APPROVED,
        )
        self.pool = Pool.objects.create(
            tenant=self.tenant, name="Pool A", code="POOL-A", product=self.product,
            effective_date=date(2026, 1, 1), status=PoolStatus.APPROVED,
        )

    def tearDown(self):
        set_current_tenant(None)

    def _user(self, name, role):
        return User.objects.create_user(
            email=f"{name}@activation.example.com", password="password", full_name=name.title(),
            role=role, tenant=self.tenant,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    # ---- the pieces BR-001 asks for
    def add_economics(self):
        ProfitSharingRatio.objects.create(
            tenant=self.tenant, pool=self.pool, depositor_share=Decimal("70.00"), mudarib_share=Decimal("30.00"),
            effective_from=date(2026, 1, 1), status=PSRStatus.APPROVED,
        )
        WeightageBand.objects.create(
            tenant=self.tenant, pool=self.pool, participant_class="retail", weightage=Decimal("1.00"),
            effective_from=date(2026, 1, 1), status=WeightageBandStatus.APPROVED,
        )

    def add_rule_pack(self):
        return JurisdictionRulePack.objects.create(
            tenant=self.tenant, code="PK-SBP", name="SBP Framework", version="2025.01",
            effective_date=date(2025, 1, 1), is_default=True,
        )

    def add_mapping(self, keys=None):
        for key in keys or REQUIRED_BY_MODEL["bank_pool"]:
            AccountMapping.objects.create(
                tenant=self.tenant, account_key=key, gl_code=f"GL-{key[:6]}", gl_name=f"Mapped {ACCOUNTS[key]}"
            )

    def add_matrix(self):
        return ApprovalMatrixRule.objects.create(
            tenant=self.tenant, action="allocation_release", role=UserRole.AUTHORIZED_SIGNATORY,
            max_amount=Decimal("1000000.00"),
        )

    def add_everything(self):
        self.add_economics()
        self.add_rule_pack()
        self.add_mapping()
        self.add_matrix()

    def open_pool(self):
        self.authenticate(self.checker)  # BRD 6.1: an independent checker activates
        return self.client.post(reverse("pool-open", args=[self.pool.id]))


class ActivationGateTests(ActivationBase):
    def test_a_bare_pool_cannot_open_and_every_gap_is_reported(self):
        response = self.open_pool()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        text = str(response.data)
        for expected in ("profit-sharing ratio", "weightage bands", "rule pack", "Accounting mapping", "approval matrix"):
            self.assertIn(expected.lower(), text.lower(), expected)
        self.pool.refresh_from_db()
        self.assertEqual(self.pool.status, PoolStatus.APPROVED)
        self.assertFalse(PoolVersion.objects.filter(pool=self.pool).exists())

    def test_readiness_endpoint_lists_every_check(self):
        self.authenticate(self.pm)
        data = self.client.get(reverse("pool-activation-readiness", args=[self.pool.id])).data
        self.assertFalse(data["ready"])
        keys = {c["key"]: c["passed"] for c in data["checks"]}
        self.assertTrue(keys["product_approved"] and keys["contract_approved"] and keys["shariah_decision"])
        self.assertFalse(keys["rule_pack"] or keys["psr_approved"] or keys["accounting_mapping"] or keys["approval_matrix"])

    def test_each_missing_piece_blocks_on_its_own(self):
        pieces = {
            "psr_approved": lambda: ProfitSharingRatio.objects.filter(pool=self.pool).delete(),
            "rule_pack": lambda: JurisdictionRulePack.objects.all().delete(),
            "accounting_mapping": lambda: AccountMapping.objects.filter(account_key="rounding_account").delete(),
            "approval_matrix": lambda: ApprovalMatrixRule.objects.all().delete(),
            "contract_approved": lambda: ContractTemplate.objects.update(status=ContractTemplateStatus.DRAFT),
            "shariah_decision": lambda: ShariahDecision.objects.update(status=ShariahDecisionStatus.DRAFT),
        }
        for failing_key, break_it in pieces.items():
            ProfitSharingRatio.objects.all().delete()
            WeightageBand.objects.all().delete()
            JurisdictionRulePack.objects.all().delete()
            AccountMapping.objects.all().delete()
            ApprovalMatrixRule.objects.all().delete()
            ContractTemplate.objects.update(status=ContractTemplateStatus.APPROVED)
            ShariahDecision.objects.update(status=ShariahDecisionStatus.APPROVED)
            self.add_everything()
            break_it()
            self.authenticate(self.pm)
            data = self.client.get(reverse("pool-activation-readiness", args=[self.pool.id])).data
            failed = [c["key"] for c in data["checks"] if not c["passed"]]
            self.assertIn(failing_key, failed, failing_key)
            self.assertEqual(self.open_pool().status_code, status.HTTP_400_BAD_REQUEST, failing_key)

    def test_complete_configuration_opens_and_seals_a_real_version(self):
        self.add_everything()
        response = self.open_pool()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.pool.refresh_from_db()
        self.assertEqual(self.pool.status, PoolStatus.OPEN)
        self.assertEqual(self.pool.rule_pack.code, "PK-SBP")  # the default pack is bound on activation

        snapshot = PoolVersion.objects.get(pool=self.pool, version_number=1).snapshot
        self.assertEqual(snapshot["psr"]["investor_share_pct"], 70.0)
        self.assertEqual(snapshot["psr"]["manager_share_pct"], 30.0)
        self.assertEqual([b["code"] for b in snapshot["weightage_bands"]], ["retail"])
        self.assertEqual(snapshot["rule_pack"]["code"], "PK-SBP")
        self.assertEqual(snapshot["shariah_decision"]["decision_code"], "SD-ACT-1")
        self.assertEqual(snapshot["governance"]["approving_scholar"], "Board")
        self.assertEqual(snapshot["approval_matrix"][0]["role"], "authorized_signatory")
        self.assertIn("rounding_account", snapshot["account_mapping"])
        # Nothing invented: no placeholder benchmark / scholar / tiers.
        self.assertNotIn("benchmarks", snapshot)
        self.assertNotIn("Usmani", str(snapshot))
        self.assertNotIn("TIER-", str(snapshot))

    def test_only_a_checker_can_open_and_only_a_pool_manager_can_seal(self):
        self.add_everything()
        self.authenticate(self.pm)
        self.assertEqual(self.client.post(reverse("pool-open", args=[self.pool.id])).status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(self.investor)
        self.assertEqual(self.client.post(reverse("pool-open", args=[self.pool.id])).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.post(reverse("pool-create-version", args=[self.pool.id]), {"change_rationale": "x"}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_community_circle_needs_no_economics_or_chart(self):
        self.product.operating_model = "community_circle"
        self.product.save()
        template = self.product.contract_template
        template.contract_type = "qard"  # a Qard circle; a Mudarabah contract would be a rule conflict
        template.save()
        self.add_rule_pack()
        ApprovalMatrixRule.objects.create(
            tenant=self.tenant, action="payout_approve", role=UserRole.FINANCE_CHECKER, max_amount=None
        )
        self.assertEqual(self.open_pool().status_code, status.HTTP_200_OK)


class PoolVersionTests(ActivationBase):
    def setUp(self):
        super().setUp()
        self.add_everything()
        self.assertEqual(self.open_pool().status_code, status.HTTP_200_OK)

    def seal(self, **payload):
        self.authenticate(self.pm)
        return self.client.post(reverse("pool-create-version", args=[self.pool.id]), payload, format="json")

    def test_a_version_needs_a_rationale_and_a_real_change(self):
        self.assertEqual(self.seal().status_code, status.HTTP_400_BAD_REQUEST)
        unchanged = self.seal(change_rationale="Nothing happened")
        self.assertEqual(unchanged.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not changed", str(unchanged.data))

    def test_sealing_captures_the_approved_change_not_typed_in_values(self):
        ReservePolicy.objects.create(
            tenant=self.tenant, pool=self.pool, reserve_type=ReserveType.PER,
            rate_percentage=Decimal("2.50"), cap_percentage=Decimal("6.00"),
        )
        # Typed-in economics in the payload are ignored: only recorded configuration is sealed.
        response = self.seal(change_rationale="Introduce PER", psr={"mudarib_share_pct": 99})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        snapshot = response.data["snapshot"]
        self.assertEqual(snapshot["psr"]["manager_share_pct"], 30.0)
        self.assertEqual(snapshot["reserve_policy"]["per"]["rate_pct"], 2.5)
        self.assertEqual(response.data["version_number"], 2)
        self.assertEqual(PoolVersion.objects.filter(pool=self.pool, is_current=True).count(), 1)

    def test_comparison_reports_the_real_difference_without_placeholders(self):
        ReservePolicy.objects.create(
            tenant=self.tenant, pool=self.pool, reserve_type=ReserveType.PER,
            rate_percentage=Decimal("2.50"), cap_percentage=Decimal("6.00"),
        )
        self.seal(change_rationale="Introduce PER")
        diff = self.client.get(reverse("pool-compare-versions", args=[self.pool.id]), {"v1": 1, "v2": 2}).data
        changed = {item["key"]: item for item in diff["diff_matrix"] if item["is_changed"]}
        self.assertIn("per_rate_pct", changed)
        self.assertIn("change_rationale", changed)
        self.assertEqual(changed["per_rate_pct"]["v1_value"], None)
        self.assertEqual(changed["per_rate_pct"]["v2_value"], 2.5)
        self.assertEqual(diff["summary"]["risk_impact"], "HIGH")
        self.assertNotIn("KIBOR", str(diff))
        self.assertNotIn("Usmani", str(diff))

    def test_a_changed_rule_pack_or_mapping_is_a_real_change_too(self):
        AccountMapping.objects.filter(account_key="rounding_account").update(gl_code="NEW-CODE")
        self.assertEqual(self.seal(change_rationale="Re-coded rounding account").status_code, status.HTTP_201_CREATED)


class RuleConflictTests(ActivationBase):
    def test_a_manager_share_above_the_rule_pack_cap_blocks_activation(self):
        self.add_everything()
        JurisdictionRulePack.objects.filter(tenant=self.tenant).update(rules_config={"mudarib_share_cap_pct": 10.0})
        response = self.open_pool()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("exceeds the rule pack cap", str(response.data))

    def test_a_contract_that_does_not_fit_the_model_blocks_activation(self):
        self.add_everything()
        template = self.product.contract_template
        template.contract_type = "qard"
        template.save()
        response = self.open_pool()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot run a bank_pool", str(response.data))
