"""Approval matrix limits at release, and journals named through the accounting mapping."""

from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from apps.accounting.chart import ACCOUNTS
from apps.accounting.models import AccountMapping, JournalBatch
from apps.accounts.models import ApprovalMatrixRule, UserRole

from .ceremony_helpers import complete_ceremony
from .test_participant_ledger import ParticipantLedgerTestBase


class MatrixBase(ParticipantLedgerTestBase):
    def rule(self, role, limit, action="allocation_release", active=True):
        return ApprovalMatrixRule.objects.create(
            tenant=self.tenant, action=action, role=role, max_amount=limit, is_active=active
        )

    def prepared_run(self, gross="600.00"):
        run_id = self.create_run(gross=gross)
        self.authenticate(self.maker)
        base = reverse("allocation-run-detail", args=[run_id])
        self.assertEqual(self.client.post(base + "submit-for-checking/").status_code, status.HTTP_200_OK)
        return run_id


class ApprovalMatrixEnforcementTests(MatrixBase):
    def test_without_rules_the_role_permission_alone_decides(self):
        run_id = self.prepared_run()
        self.assertEqual(complete_ceremony(self, run_id).status_code, status.HTTP_200_OK)

    def test_release_above_the_signatorys_limit_is_refused(self):
        self.rule(UserRole.AUTHORIZED_SIGNATORY, Decimal("100.00"))
        run_id = self.prepared_run()  # distributable 600
        response = complete_ceremony(self, run_id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("limit", str(response.data).lower())

    def test_release_within_the_limit_or_unlimited_succeeds(self):
        self.rule(UserRole.AUTHORIZED_SIGNATORY, Decimal("5000.00"))
        self.assertEqual(complete_ceremony(self, self.prepared_run()).status_code, status.HTTP_200_OK)

    def test_unlimited_rule_allows_any_amount(self):
        self.rule(UserRole.AUTHORIZED_SIGNATORY, None)
        self.assertEqual(complete_ceremony(self, self.prepared_run(gross="99999999.00")).status_code, status.HTTP_200_OK)

    def test_a_role_that_is_not_in_the_matrix_cannot_release(self):
        self.rule(UserRole.FINANCE_CHECKER, None)  # the matrix names someone else
        response = complete_ceremony(self, self.prepared_run())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("finance_checker", str(response.data))

    def test_inactive_rules_are_ignored(self):
        self.rule(UserRole.AUTHORIZED_SIGNATORY, Decimal("1.00"), active=False)
        self.assertEqual(complete_ceremony(self, self.prepared_run()).status_code, status.HTTP_200_OK)

    def test_absolute_amount_rule(self):
        from apps.accounts.approval_matrix import assert_may_approve
        from rest_framework.exceptions import PermissionDenied

        self.rule(UserRole.AUTHORIZED_SIGNATORY, Decimal("100.00"))
        with self.assertRaises(PermissionDenied):
            assert_may_approve(self.signatory, self.tenant.id, "allocation_release", Decimal("-500.00"))
        assert_may_approve(self.signatory, self.tenant.id, "allocation_release", Decimal("-50.00"))


class ChartMappingTests(MatrixBase):
    def map_all(self, pool=None, prefix="GL"):
        for key in ACCOUNTS:
            AccountMapping.objects.create(
                tenant=self.tenant, pool=pool, account_key=key, gl_code=f"{prefix}-{key}", gl_name=f"{prefix} {ACCOUNTS[key]}"
            )

    def test_unmapped_accounts_keep_descriptive_names_and_no_code(self):
        batch = JournalBatch.objects.get(allocation_run_id=self.sign_run())
        entry = batch.entries.get(account_key="pool_income")
        self.assertEqual(entry.account_name, "Pool Income")
        self.assertEqual(entry.gl_code, "")

    def test_mapped_accounts_carry_gl_code_and_name(self):
        self.map_all()
        batch = JournalBatch.objects.get(allocation_run_id=self.sign_run())
        income = batch.entries.get(account_key="pool_income")
        self.assertEqual((income.account_name, income.gl_code), ("GL Pool Income", "GL-pool_income"))
        payables = batch.entries.filter(account_key="depositor_payable")
        self.assertTrue(all(e.account_name.startswith("GL Depositor Payable - ") for e in payables))
        self.assertEqual({e.gl_code for e in payables}, {"GL-depositor_payable"})
        self.assertEqual(batch.total_debit, batch.total_credit)

    def test_a_pool_mapping_overrides_the_tenant_default(self):
        self.map_all(prefix="TENANT")
        AccountMapping.objects.create(
            tenant=self.tenant, pool=self.pool, account_key="pool_income", gl_code="POOL-4100", gl_name="Special Pool Income"
        )
        batch = JournalBatch.objects.get(allocation_run_id=self.sign_run())
        self.assertEqual(batch.entries.get(account_key="pool_income").gl_code, "POOL-4100")
        self.assertEqual(batch.entries.get(account_key="mudarib_payable").gl_code, "TENANT-mudarib_payable")

    def test_a_remap_does_not_rewrite_posted_journals_and_reversals_keep_original_names(self):
        self.map_all(prefix="OLD")
        run_id = self.sign_run()
        AccountMapping.objects.filter(account_key="pool_income").update(gl_code="NEW-1", gl_name="Renamed Income")
        original = JournalBatch.objects.get(allocation_run_id=run_id)
        self.assertEqual(original.entries.get(account_key="pool_income").gl_code, "OLD-pool_income")

        # Restate: the reversal contra-posts exactly the original accounts.
        self.authenticate(self.maker)
        base = reverse("allocation-run-detail", args=[run_id])
        restated = self.client.post(
            base + "restate/",
            {"restatement_reason": "fix", "gross_income": "700.00", "direct_expenses": "0.00"},
            format="json",
        )
        self.assertEqual(restated.status_code, status.HTTP_201_CREATED, restated.data)
        self.client.post(reverse("allocation-run-detail", args=[restated.data["id"]]) + "submit-for-checking/")
        self.assertEqual(complete_ceremony(self, restated.data["id"]).status_code, status.HTTP_200_OK)
        reversal = JournalBatch.objects.get(reverses_batch=original)
        self.assertEqual(reversal.entries.get(account_key="pool_income").gl_code, "OLD-pool_income")
        new_batch = JournalBatch.objects.get(allocation_run_id=restated.data["id"])
        self.assertEqual(new_batch.entries.get(account_key="pool_income").gl_code, "NEW-1")


class ConfigApiTests(MatrixBase):
    def propose_and_approve(self, proposer, method, url, body, approver=None):
        """Config endpoints only propose (202); a different finance checker applies the change."""
        self.authenticate(proposer)
        proposed = getattr(self.client, method)(url, {**body, "change_reason": "Policy update"}, format="json")
        self.assertEqual(proposed.status_code, status.HTTP_202_ACCEPTED, proposed.data)
        self.authenticate(approver or self.checker)
        decided = self.client.post(reverse("config-change-detail", args=[proposed.data["id"]]) + "approve/")
        self.assertEqual(decided.status_code, status.HTTP_200_OK, decided.data)
        return decided

    def test_matrix_is_owned_by_risk_and_never_deleted(self):
        risk = self.risk
        url = reverse("approval-matrix-list")
        body = {"action": "allocation_release", "role": "authorized_signatory", "max_amount": "5000.00"}

        self.authenticate(self.maker)
        self.assertEqual(self.client.post(url, body, format="json").status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(risk)
        # A proposal needs a reason and creates nothing until approved.
        self.assertEqual(self.client.post(url, body, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        applied = self.propose_and_approve(risk, "post", url, body)
        rule = ApprovalMatrixRule.objects.get(pk=applied.data["applied_id"])
        self.assertEqual((rule.action, rule.role, rule.max_amount), ("allocation_release", "authorized_signatory", 5000))
        # One rule per action+role; limits must be positive; investors cannot be given authority.
        self.authenticate(risk)
        self.assertEqual(self.client.post(url, {**body, "change_reason": "x"}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.client.post(url, {**body, "role": "finance_checker", "max_amount": "-1", "change_reason": "x"}, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.post(url, {**body, "role": "investor_member", "change_reason": "x"}, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        detail = reverse("approval-matrix-detail", args=[rule.id])
        self.assertEqual(self.client.delete(detail).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.propose_and_approve(risk, "patch", detail, {"is_active": False})
        rule.refresh_from_db()
        self.assertFalse(rule.is_active)

    def test_proposer_cannot_approve_and_unauthorised_roles_cannot(self):
        url = reverse("approval-matrix-list")
        self.authenticate(self.risk)
        proposed = self.client.post(
            url, {"action": "allocation_release", "role": "authorized_signatory", "max_amount": "1.00",
                  "change_reason": "tighten"}, format="json",
        )
        change = reverse("config-change-detail", args=[proposed.data["id"]])
        self.assertEqual(self.client.post(change + "approve/").status_code, status.HTTP_403_FORBIDDEN)  # risk is not an approver
        self.authenticate(self.maker)
        self.assertEqual(self.client.post(change + "approve/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(ApprovalMatrixRule.objects.filter(max_amount=1).exists())
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(change + "reject/").status_code, status.HTTP_400_BAD_REQUEST)  # reason needed
        self.assertEqual(self.client.post(change + "reject/", {"reason": "Too tight"}, format="json").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(change + "approve/").status_code, status.HTTP_400_BAD_REQUEST)  # already decided

    def test_a_checker_who_proposed_a_mapping_cannot_approve_it(self):
        self.authenticate(self.checker)
        proposed = self.client.post(
            reverse("account-mapping-list"),
            {"account_key": "pool_income", "gl_code": "4101-001", "gl_name": "Pool Income", "change_reason": "chart"},
            format="json",
        )
        self.assertEqual(proposed.status_code, status.HTTP_202_ACCEPTED)
        denied = self.client.post(reverse("config-change-detail", args=[proposed.data["id"]]) + "approve/")
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Four-eyes", str(denied.data))

    def test_stale_update_is_refused_at_approval(self):
        rule = ApprovalMatrixRule.objects.create(
            tenant=self.tenant, action="allocation_release", role="authorized_signatory", max_amount=100
        )
        self.authenticate(self.risk)
        detail = reverse("approval-matrix-detail", args=[rule.id])
        proposed = self.client.patch(detail, {"max_amount": "200.00", "change_reason": "raise"}, format="json")
        ApprovalMatrixRule.objects.filter(pk=rule.pk).update(max_amount=150)  # changed meanwhile
        self.authenticate(self.checker)
        response = self.client.post(reverse("config-change-detail", args=[proposed.data["id"]]) + "approve/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("changed since", str(response.data))
        # and a second pending change for the same rule is refused
        self.authenticate(self.risk)
        again = self.client.patch(detail, {"max_amount": "300.00", "change_reason": "again"}, format="json")
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)

    def test_investors_cannot_read_the_matrix_or_the_mapping(self):
        self.authenticate(self.investor_a)
        self.assertEqual(self.client.get(reverse("approval-matrix-list")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(reverse("account-mapping-list")).status_code, status.HTTP_403_FORBIDDEN)

    def test_mapping_is_owned_by_finance_and_validated(self):
        url = reverse("account-mapping-list")
        body = {"account_key": "pool_income", "gl_code": "4101-001", "gl_name": "Pool Financing Income"}
        self.authenticate(self.risk)
        self.assertEqual(self.client.post(url, body, format="json").status_code, status.HTTP_403_FORBIDDEN)
        applied = self.propose_and_approve(self.maker, "post", url, body)
        self.assertEqual(AccountMapping.objects.get(pk=applied.data["applied_id"]).gl_code, "4101-001")
        self.authenticate(self.maker)
        dup = self.client.post(url, {**body, "change_reason": "again"}, format="json")  # duplicate
        self.assertEqual(dup.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.client.post(url, {**body, "account_key": "made_up", "change_reason": "x"}, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        # A pool-specific override of the same account is a different row.
        override = self.propose_and_approve(self.maker, "post", url, {**body, "pool": str(self.pool.id), "gl_code": "X-1"})
        self.assertEqual(AccountMapping.objects.get(pk=override.data["applied_id"]).pool_id, self.pool.id)
        self.authenticate(self.checker)
        catalog = self.client.get(reverse("account-mapping-catalog")).data
        self.assertIn("pool_income", {row["key"] for row in catalog})
