"""
Regression tests for the audit findings F-01 (reserve policy), F-02 (unvalidated balances), F-03 (super admin audit log),
F-04 (rule pack) and F-05 (account dates). Each test replays the exact request that the audit showed was accepted.
"""

from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.allocation.models import ReservePolicy
from apps.core.context import set_current_tenant
from apps.governance.models import ConfigChangeRequest, ConfigChangeStatus
from apps.tenants.models import Tenant


class AuditFixTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_project_data", tenant_code="FIX-T", allow_non_debug=True, stdout=StringIO())
        cls.tenant = Tenant.objects.get(code="FIX-T")

    def setUp(self):
        set_current_tenant(self.tenant)

    def tearDown(self):
        set_current_tenant(None)

    def user(self, role):
        return User.objects.filter(tenant=self.tenant, role=role).order_by("email").first()

    def call(self, user, method, url, body=None):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        response = getattr(self.client, method)(url, body, format="json", HTTP_X_TENANT_CODE="FIX-T")
        set_current_tenant(self.tenant)
        return response

    # F-01 ---------------------------------------------------------------------------------------
    def test_reserve_balance_cannot_be_set_and_a_rate_change_needs_a_different_checker(self):
        policy = ReservePolicy._base_manager.filter(tenant=self.tenant).first()
        balance, rate = policy.current_balance, policy.rate_percentage
        pm, checker = self.user("pool_manager"), self.user("finance_checker")
        url = f"/api/v1/allocation/reserve-policies/{policy.pk}/"

        r = self.call(pm, "patch", url, {"current_balance": "1.00", "change_reason": "fix"})
        policy.refresh_from_db()
        self.assertEqual(policy.current_balance, balance, f"balance written directly ({r.status_code})")
        self.assertEqual(r.status_code, 400, "a request that only tries to set the balance must be refused outright")

        r = self.call(pm, "patch", url, {"rate_percentage": "1.00"})
        self.assertEqual(r.status_code, 400, "a change without a reason must be refused")

        r = self.call(pm, "patch", url, {"rate_percentage": "1.00", "change_reason": "Board paper 12"})
        self.assertEqual(r.status_code, 202)
        policy.refresh_from_db()
        self.assertEqual(policy.rate_percentage, rate, "the rate changed before anyone approved it")

        change = ConfigChangeRequest.objects.get(pk=r.data["id"])
        self.assertEqual(self.call(pm, "post", f"/api/v1/governance/config-changes/{change.pk}/approve/").status_code, 403)
        self.assertEqual(self.call(checker, "post", f"/api/v1/governance/config-changes/{change.pk}/approve/").status_code, 200)
        policy.refresh_from_db()
        self.assertEqual(policy.rate_percentage, Decimal("1.00"))
        self.assertEqual(policy.current_balance, balance, "approving a rate change must never touch the balance")
        change.refresh_from_db()
        self.assertEqual(change.status, ConfigChangeStatus.APPROVED)

    # F-04 ---------------------------------------------------------------------------------------
    def test_rule_pack_change_is_only_proposed_until_approved(self):
        from apps.products.models import JurisdictionRulePack

        pack = JurisdictionRulePack._base_manager.filter(tenant=self.tenant).first()
        before = dict(pack.rules_config)
        zeroed = {**before, "wht_filer_pct": 0, "wht_non_filer_pct": 0}
        url = f"/api/v1/products/jurisdiction-rule-packs/{pack.pk}/"
        for role in ("risk_compliance", "platform_super_admin"):
            r = self.call(self.user(role), "patch", url, {"rules_config": zeroed, "change_reason": "Tax review"})
            self.assertEqual(r.status_code, 202, f"{role}: {r.data}")
            pack.refresh_from_db()
            self.assertEqual(pack.rules_config, before, f"{role} changed the rule pack in place")
            ConfigChangeRequest._base_manager.filter(pk=r.data["id"]).update(status=ConfigChangeStatus.REJECTED)

        r = self.call(self.user("risk_compliance"), "patch", url, {"rules_config": zeroed, "change_reason": "Tax review"})
        change_id = r.data["id"]
        self.assertEqual(self.call(self.user("risk_compliance"), "post", f"/api/v1/governance/config-changes/{change_id}/approve/").status_code, 403)
        self.assertEqual(self.call(self.user("authorized_signatory"), "post", f"/api/v1/governance/config-changes/{change_id}/approve/").status_code, 200)
        pack.refresh_from_db()
        self.assertEqual(pack.rules_config["wht_filer_pct"], 0)

    # F-05 ---------------------------------------------------------------------------------------
    def test_account_dates_and_identity_cannot_be_rewritten(self):
        from apps.participants.models import ParticipantAccount

        account = ParticipantAccount._base_manager.filter(tenant=self.tenant).first()
        opened = account.opened_date
        for role in ("pool_manager", "finance_maker"):
            r = self.call(self.user(role), "patch", f"/api/v1/participants/accounts/{account.pk}/", {"opened_date": "2020-01-01"})
            self.assertEqual(r.status_code, 400, role)
        account.refresh_from_db()
        self.assertEqual(account.opened_date, opened)

    # F-03 ---------------------------------------------------------------------------------------
    def test_super_admin_audit_log_hides_the_figures(self):
        from apps.core.audit import log_action

        log_action(tenant=self.tenant, actor=self.user("finance_checker"), action="approve", model_name="AllocationRun",
                   object_id="x", changes={"distributable_amount": "123456.78"}, reason="secret reason")
        admin, auditor = self.user("platform_super_admin"), self.user("auditor")
        body = str(self.call(admin, "get", "/api/v1/core/audit-log/").data)
        self.assertNotIn("123456.78", body)
        self.assertNotIn("secret reason", body)
        self.assertIn("AllocationRun", body, "who/what/when must stay visible")
        export = self.call(admin, "get", "/api/v1/core/audit-log/export/").content.decode()
        self.assertNotIn("123456.78", export)
        self.assertIn("123456.78", str(self.call(auditor, "get", "/api/v1/core/audit-log/").data), "the tenant's auditor still sees everything")

    # F-02 ---------------------------------------------------------------------------------------
    def test_pending_balances_block_a_run_and_never_earn_profit(self):
        from apps.allocation.engine import calculate_allocation
        from apps.pools.models import DailyBalance, DailyBalanceStatus, Pool

        row = DailyBalance._base_manager.filter(tenant=self.tenant, status=DailyBalanceStatus.VALIDATED).order_by("-value_date").first()
        pool, end = row.pool, row.value_date
        DailyBalance._base_manager.filter(pk=row.pk).update(status=DailyBalanceStatus.PENDING)
        with self.assertRaisesMessage(ValueError, "pending validation"):
            calculate_allocation(pool, end, Decimal("1000"), Decimal("0"), period_start=end)

    # F-09 ---------------------------------------------------------------------------------------
    def test_the_shariah_review_requirement_is_fixed_on_the_run(self):
        from django.test import override_settings

        from apps.allocation.models import AllocationRun

        run = AllocationRun._base_manager.filter(tenant=self.tenant, pool__product__operating_model="bank_pool").first()
        run.shariah_review_enforced = True
        with override_settings(ALLOCATION_SHARIAH_REVIEW_REQUIRED_FOR_BANK_POOL=False):
            self.assertTrue(run.shariah_review_required, "flipping the setting removed a stage from a run in progress")
            self.assertFalse(AllocationRun.shariah_review_rule_for(run.pool))

    # F-11 ---------------------------------------------------------------------------------------
    def test_an_open_serious_exception_blocks_the_release_of_profit(self):
        from rest_framework.exceptions import ValidationError

        from apps.governance.models import ExceptionCase
        from apps.pools.exception_gate import assert_no_open_serious_exception
        from apps.pools.models import Pool

        pool = Pool._base_manager.filter(tenant=self.tenant, product__operating_model="bank_pool").first()
        ExceptionCase._base_manager.filter(tenant=self.tenant, pool=pool).update(status="resolved")
        assert_no_open_serious_exception(pool, "an allocation run")  # nothing open: no error
        case = ExceptionCase._base_manager.filter(tenant=self.tenant).first()
        ExceptionCase._base_manager.filter(pk=case.pk).update(pool=pool, status="open", severity="high")
        with self.assertRaisesMessage(ValidationError, "still open"):
            assert_no_open_serious_exception(pool, "an allocation run")

    # F-04 (versioning) -----------------------------------------------------------------------------
    def test_a_rule_pack_keeps_its_history_and_a_run_under_old_rules_is_refused(self):
        from apps.allocation.models import AllocationRun
        from apps.pools.config_snapshot import assert_rule_pack_unchanged, bound_rule_pack, rule_pack_snapshot
        from apps.products.models import RulePackRevision
        from rest_framework.exceptions import ValidationError

        run = AllocationRun._base_manager.filter(tenant=self.tenant, pool__product__operating_model="bank_pool").first()
        pool = run.pool
        pack = bound_rule_pack(pool)
        first = rule_pack_snapshot(pool)
        self.assertEqual(first["content_hash"], RulePackRevision.record(pack).content_hash)
        count = RulePackRevision._base_manager.filter(pack=pack).count()

        # a run seals the pack it used
        run.config_snapshot = {**(run.config_snapshot or {}), "rule_pack": first}
        assert_rule_pack_unchanged(run, pool)  # unchanged: fine

        # saving the same content again adds no revision
        pack.save()
        self.assertEqual(RulePackRevision._base_manager.filter(pack=pack).count(), count)

        # a changed pack adds a revision and the sealed run is no longer valid
        pack.rules_config = {**pack.rules_config, "wht_filer_pct": 11}
        pack.save()
        self.assertEqual(RulePackRevision._base_manager.filter(pack=pack).count(), count + 1)
        with self.assertRaisesMessage(ValidationError, "rule pack changed"):
            assert_rule_pack_unchanged(run, pool)

        # history is immutable
        old = RulePackRevision._base_manager.filter(pack=pack).order_by("revision").first()
        from django.core.exceptions import ValidationError as DjangoValidationError

        with self.assertRaises(DjangoValidationError):
            old.content = {}
            old.save()
        with self.assertRaises(DjangoValidationError):
            old.delete()
        old.refresh_from_db()
        self.assertEqual(old.content["rules_config"]["wht_filer_pct"], first["rules_config"]["wht_filer_pct"])

    def test_the_revision_history_is_readable_through_the_api(self):
        from apps.products.models import JurisdictionRulePack

        pack = JurisdictionRulePack._base_manager.filter(tenant=self.tenant).first()
        pack.save()
        r = self.call(self.user("auditor"), "get", f"/api/v1/products/jurisdiction-rule-packs/{pack.pk}/revisions/")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.data), 1)
        self.assertEqual(self.call(self.user("investor_member"), "get", f"/api/v1/products/jurisdiction-rule-packs/{pack.pk}/revisions/").status_code, 403)

    # F-02 (signed daily close) ---------------------------------------------------------------------
    def test_a_run_cannot_be_checked_while_days_with_balances_are_unsigned(self):
        from apps.allocation.models import AllocationRun
        from apps.pools.daily_close import unsigned_balance_days
        from apps.pools.models import DailyBalance, DailyClose, DailyCloseStatus

        # September of the seeded bank pool has balances and no signed close: its run waits and cannot be checked.
        run = AllocationRun._base_manager.filter(tenant=self.tenant, status="pending_approval").first()
        self.assertIsNotNone(run)
        missing = unsigned_balance_days(run.pool, run.effective_period_start, run.value_date)
        self.assertTrue(missing, "the seeded September run should have unsigned days")
        r = self.call(self.user("finance_checker"), "post", f"/api/v1/allocation/allocation-runs/{run.pk}/check/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("no signed daily close", str(r.data))

        # days without balances (weekends, holidays) need no close: sign every day that has balances and it passes
        for day in missing:
            DailyClose._base_manager.update_or_create(
                tenant=self.tenant, pool=run.pool, value_date=day, defaults={"status": DailyCloseStatus.SIGNED, "gates": []}
            )
        self.assertEqual(unsigned_balance_days(run.pool, run.effective_period_start, run.value_date), [])
        # a day with no balance row at all was never in the list, so it never needed a close
        self.assertFalse(
            set(missing) & {d for d in (run.value_date.replace(day=1),) if not DailyBalance._base_manager.filter(pool=run.pool, value_date=d).exists()}
        )
        r = self.call(self.user("finance_checker"), "post", f"/api/v1/allocation/allocation-runs/{run.pk}/check/")
        self.assertEqual(r.status_code, 200, r.data)

    # BRD 14 scale: growing lists are paged ----------------------------------------------------------
    def test_growing_lists_are_paged_and_accounts_follow_the_page(self):
        from apps.participants.models import Participant, ParticipantAccount

        risk = self.user("risk_compliance")
        for url in ("/api/v1/participants/participants/", "/api/v1/participants/accounts/", "/api/v1/core/audit-log/",
                    "/api/v1/notifications/", "/api/v1/accounting/journal-batches/",
                    "/api/v1/accounting/income-expense-events/", "/api/v1/pools/daily-balances/"):
            r = self.call(risk, "get", url, {"page_size": 2})
            self.assertEqual(r.status_code, 200, url)
            self.assertEqual(set(r.data), {"count", "next", "previous", "results"}, url)
            self.assertLessEqual(len(r.data["results"]), 2, url)

        page = self.call(risk, "get", "/api/v1/participants/participants/", {"page_size": 3}).data["results"]
        ids = [p["id"] for p in page]
        accounts = self.call(risk, "get", "/api/v1/participants/accounts/", {"participants": ",".join(ids), "page_size": 500}).data
        expected = ParticipantAccount._base_manager.filter(tenant=self.tenant, participant_id__in=ids).count()
        self.assertEqual(accounts["count"], expected)
        self.assertTrue(all(str(a["participant"]) in {str(i) for i in ids} for a in accounts["results"]))
        self.assertGreater(Participant._base_manager.filter(tenant=self.tenant).count(), 3)

    # BRD 8: quarantine value, decide treatment, disclose -----------------------------------------------------------
    def test_quarantined_value_needs_a_board_decision_and_a_disclosure_before_the_case_closes(self):
        from apps.governance.models import ExceptionCase

        case = ExceptionCase._base_manager.filter(tenant=self.tenant).exclude(status__in=["resolved", "dismissed"]).first()
        url = f"/api/v1/governance/exceptions/{case.pk}/"
        risk, board = self.user("risk_compliance"), self.user("shariah_board")

        self.assertEqual(self.call(self.user("finance_maker"), "post", url + "quarantine/", {"amount": "10", "reason": "x"}).status_code, 403)
        self.assertEqual(self.call(risk, "post", url + "quarantine/", {"amount": "0", "reason": "x"}).status_code, 400)
        self.assertEqual(self.call(risk, "post", url + "quarantine/", {"amount": "9000.00"}).status_code, 400)
        held = self.call(risk, "post", url + "quarantine/", {"amount": "9000.00", "reason": "Penalty income received on 12 July"})
        self.assertEqual(held.status_code, 200, held.data)
        self.assertEqual(held.data["quarantine_status"], "held")
        self.assertEqual(self.call(risk, "post", url + "quarantine/", {"amount": "1", "reason": "again"}).status_code, 400)

        # the case cannot close while value is held and undecided
        self.assertEqual(self.call(risk, "post", url + "resolve/", {"resolution_notes": "done"}).status_code, 400)
        self.assertEqual(self.call(risk, "post", url + "dismiss/", {"resolution_notes": "done"}).status_code, 400)

        # only the Shariah Board decides the treatment, with its reasoning
        self.assertEqual(self.call(risk, "post", url + "decide-quarantine/", {"treatment": "purify", "note": "x"}).status_code, 403)
        self.assertEqual(self.call(board, "post", url + "decide-quarantine/", {"treatment": "keep_it", "note": "x"}).status_code, 400)
        self.assertEqual(self.call(board, "post", url + "decide-quarantine/", {"treatment": "purify"}).status_code, 400)
        decided = self.call(board, "post", url + "decide-quarantine/", {"treatment": "purify", "note": "Non-permissible penalty income"})
        self.assertEqual(decided.data["quarantine_status"], "decided")
        self.assertEqual(decided.data["quarantine_treatment"], "purify")

        # closing then needs the disclosure
        self.assertEqual(self.call(risk, "post", url + "resolve/", {"resolution_notes": "done"}).status_code, 400)
        closed = self.call(risk, "post", url + "resolve/", {"resolution_notes": "done", "disclosure_note": "Disclosed in the July pool report, note 4"})
        self.assertEqual(closed.status_code, 200, closed.data)
        self.assertEqual(closed.data["status"], "resolved")
        self.assertIn("note 4", closed.data["disclosure_note"])

    def test_a_case_without_quarantined_value_closes_as_before(self):
        from apps.governance.models import ExceptionCase

        case = ExceptionCase._base_manager.filter(tenant=self.tenant).exclude(status__in=["resolved", "dismissed"]).first()
        r = self.call(self.user("risk_compliance"), "post", f"/api/v1/governance/exceptions/{case.pk}/resolve/", {"resolution_notes": "checked"})
        self.assertEqual(r.status_code, 200, r.data)

    # DB audit: financial history is never lost to a cascading delete ---------------------------------------------
    def test_financial_relations_protect_their_parents_from_deletion(self):
        from django.apps import apps
        from django.db import models as dj

        must_protect = {
            "pools.DailyBalance": "pool", "allocation.AllocationRun": "pool", "accounting.JournalBatch": "pool",
            "accounting.IncomeExpenseEvent": "pool", "governance.ExceptionCase": "pool", "governance.PurificationEntry": "pool",
            "investments.CapitalAccount": "pool", "investments.Subscription": "capital_account",
            "investments.Redemption": "capital_account", "investments.InvestmentDistributionRun": "pool",
            "circles.Contribution": "member", "circles.Payout": "member", "pools.AssetTransferRequest": "assignment",
        }
        weak = [
            f"{label}.{field}" for label, field in must_protect.items()
            if apps.get_model(label)._meta.get_field(field).remote_field.on_delete is not dj.PROTECT
        ]
        self.assertEqual(weak, [], f"these relations still cascade on delete: {weak}")
