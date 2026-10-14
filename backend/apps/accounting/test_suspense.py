"""Suspense items (BRD 4, 6.2, 10): named, approved by a different person, journalled, aged, and cleared to where they belong."""

from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.core.context import set_current_tenant
from apps.pools.models import Pool
from apps.tenants.models import Tenant

from .models import JournalEntry, SuspenseItem
from .suspense import ageing, ledger_balance

BASE = "/api/v1/accounting/suspense-items/"


class SuspenseTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_project_data", tenant_code="SUS-T", allow_non_debug=True, stdout=StringIO())
        cls.tenant = Tenant.objects.get(code="SUS-T")
        cls.pool = Pool._base_manager.get(tenant=cls.tenant, code="POOL-TREAS-02")

    def setUp(self):
        set_current_tenant(self.tenant)

    def tearDown(self):
        set_current_tenant(None)

    def user(self, role):
        return User.objects.filter(tenant=self.tenant, role=role).order_by("email").first()

    def call(self, role, method, url, body=None):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.user(role)).access_token}")
        response = getattr(self.client, method)(url, body, format="json", HTTP_X_TENANT_CODE="SUS-T")
        set_current_tenant(self.tenant)
        return response

    def propose(self, side="unidentified_receipt", amount="2500.00", **extra):
        body = {"pool": str(self.pool.id), "side": side, "amount": amount, "description": "Raast credit, no reference", **extra}
        return self.call("finance_maker", "post", BASE, body)

    def test_an_amount_is_parked_only_after_a_different_checker_approves(self):
        before = ledger_balance(self.pool)
        proposed = self.propose()
        self.assertEqual(proposed.status_code, 201, proposed.data)
        self.assertEqual(proposed.data["status"], "proposed")
        self.assertEqual(ledger_balance(self.pool), before, "nothing is posted at proposal")
        url = f"{BASE}{proposed.data['id']}/"
        self.assertEqual(self.call("finance_maker", "post", url + "approve/").status_code, 403)
        opened = self.call("finance_checker", "post", url + "approve/")
        self.assertEqual(opened.status_code, 200, opened.data)
        self.assertEqual(opened.data["status"], "open")
        self.assertEqual(ledger_balance(self.pool), before + Decimal("2500.00"))
        lines = JournalEntry._base_manager.filter(batch_id=opened.data["opening_journal"])
        self.assertEqual({(e.account_key, e.entry_type) for e in lines}, {("pool_cash", "debit"), ("suspense", "credit")})

    def test_clearing_moves_the_amount_to_where_it_belongs_and_empties_suspense(self):
        before = ledger_balance(self.pool)
        item_id = self.propose(side="unexplained_shortfall", amount="700.00").data["id"]
        self.call("finance_checker", "post", f"{BASE}{item_id}/approve/")
        self.assertEqual(ledger_balance(self.pool), before - Decimal("700.00"))
        url = f"{BASE}{item_id}/"
        self.assertEqual(self.call("finance_maker", "post", url + "propose-clear/", {"target_account_key": "suspense", "reason": "x"}).status_code, 400)
        self.assertEqual(self.call("finance_maker", "post", url + "propose-clear/", {"target_account_key": "pool_direct_expense"}).status_code, 400)
        proposed = self.call("finance_maker", "post", url + "propose-clear/", {"target_account_key": "pool_direct_expense", "reason": "Bank charge, advice received"})
        self.assertEqual(proposed.data["status"], "clearing_proposed")
        self.assertEqual(self.call("finance_maker", "post", url + "approve-clear/").status_code, 403)
        cleared = self.call("finance_checker", "post", url + "approve-clear/")
        self.assertEqual(cleared.status_code, 200, cleared.data)
        self.assertEqual(cleared.data["status"], "cleared")
        self.assertEqual(ledger_balance(self.pool), before)
        lines = JournalEntry._base_manager.filter(batch_id=cleared.data["clearing_journal"])
        self.assertEqual({(e.account_key, e.entry_type) for e in lines}, {("pool_direct_expense", "debit"), ("suspense", "credit")})

    def test_a_rejected_clearing_returns_the_item_to_open(self):
        item_id = self.propose().data["id"]
        self.call("finance_checker", "post", f"{BASE}{item_id}/approve/")
        url = f"{BASE}{item_id}/"
        self.call("finance_maker", "post", url + "propose-clear/", {"target_account_key": "depositor_payable", "reason": "Customer X"})
        self.assertEqual(self.call("finance_checker", "post", url + "reject-clear/", {}).status_code, 400)
        back = self.call("finance_checker", "post", url + "reject-clear/", {"reason": "No customer confirmation yet"})
        self.assertEqual(back.data["status"], "open")
        self.assertEqual(back.data["clear_account_key"], "")

    def test_validation_and_immutability(self):
        self.assertEqual(self.propose(amount="0").status_code, 400)
        self.assertEqual(self.propose(side="plug").status_code, 400)
        self.assertEqual(self.propose(description="").status_code, 400)
        self.assertEqual(self.call("auditor", "post", BASE, {"pool": str(self.pool.id)}).status_code, 403)
        item = SuspenseItem._base_manager.get(pk=self.propose().data["id"])
        with self.assertRaises(DjangoValidationError):
            item.delete()

    def test_ageing_matches_the_ledger_and_old_items_block_the_period_close(self):
        from apps.pools.models import PeriodCloseChecklist
        from apps.pools.period_close_engine import compute_gates

        old_day = timezone.localdate() - timedelta(days=45)
        item_id = self.propose(opened_on=str(old_day)).data["id"]
        self.call("finance_checker", "post", f"{BASE}{item_id}/approve/")
        report = self.call("risk_compliance", "get", f"{BASE}ageing/?pool={self.pool.id}").data
        self.assertTrue(report["itemized"], report)
        self.assertEqual(report["overdue_items"], 1)
        self.assertEqual(Decimal(report["buckets"]["31-60"]), Decimal("2500.00"))

        period = PeriodCloseChecklist(
            tenant=self.tenant, pool=self.pool, period_start=old_day, period_end=timezone.localdate()
        )
        gates, _ = compute_gates(period)
        self.assertFalse(gates["suspense_cleared"]["passed"])
        self.assertIn("older than", gates["suspense_cleared"]["details"])

        # a shorter allowed age is a rule-pack setting
        self.assertEqual(ageing(self.pool)["max_age_days"], 30)
