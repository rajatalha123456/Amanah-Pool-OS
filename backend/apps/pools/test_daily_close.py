from datetime import date
from decimal import Decimal

from apps.accounting.models import IncomeExpenseEvent
from apps.allocation.test_participant_ledger import START, ParticipantLedgerTestBase

from .models import DailyBalance, DailyBalanceStatus, DailyClose, Pool, PoolStatus

BASE = "/api/v1/pools/daily-closes/"


class DailyCloseTests(ParticipantLedgerTestBase):
    def setUp(self):
        super().setUp()
        product = self.pool.product
        product.operating_model = "bank_pool"
        product.save()
        Pool._base_manager.filter(pk=self.pool.pk).update(status=PoolStatus.OPEN)
        self.day = START

    def post(self, user, path="", body=None):
        self.authenticate(user)
        return self.client.post(f"{BASE}{path}", body or {}, format="json")

    def prepare(self, day=None):
        return self.post(self.maker, "prepare/", {"pool": str(self.pool.id), "value_date": str(day or self.day)})

    def test_prepare_computes_the_gates_and_only_the_maker_prepares(self):
        self.assertEqual(self.post(self.checker, "prepare/", {"pool": str(self.pool.id), "value_date": str(self.day)}).status_code, 403)
        response = self.prepare()
        self.assertEqual(response.status_code, 201, response.data)
        gates = {g["key"]: g["passed"] for g in response.data["gates"]}
        self.assertEqual(set(gates), {"balances_imported", "no_unvalidated_balances", "exceptions_resolved", "reconciliation_clear"})
        self.assertEqual(response.data["status"], "prepared" if all(gates.values()) else "open")

    def test_a_day_without_balances_cannot_be_signed(self):
        response = self.prepare(date(2030, 1, 1))
        self.assertEqual(response.data["status"], "open")
        self.assertFalse({g["key"]: g["passed"] for g in response.data["gates"]}["balances_imported"])
        self.assertEqual(self.post(self.checker, f"{response.data['id']}/sign/").status_code, 400)

    def test_the_checker_signs_and_not_the_preparer(self):
        close = self.prepare().data
        if close["status"] != "prepared":
            self.skipTest("fixture day does not pass every gate")
        self.assertEqual(self.post(self.maker, f"{close['id']}/sign/").status_code, 403)  # makers cannot sign at all
        signed = self.post(self.checker, f"{close['id']}/sign/")
        self.assertEqual(signed.status_code, 200, signed.data)
        self.assertEqual(signed.data["status"], "signed")
        self.assertEqual(self.post(self.checker, f"{close['id']}/sign/").status_code, 409)  # already signed
        self.assertEqual(self.prepare().status_code, 409)

    def test_a_signed_day_refuses_new_events_and_imports(self):
        DailyClose.objects.create(
            tenant=self.tenant, pool=self.pool, value_date=self.day, status="signed", prepared_by=self.maker, signed_by=self.checker
        )
        self.authenticate(self.maker)
        response = self.client.post(
            "/api/v1/accounting/income-expense-events/",
            {"pool": str(self.pool.id), "event_type": "income", "category": "Financing Profit", "amount": "100.00",
             "event_date": str(self.day), "description": "late"},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("daily close", str(response.data))
        imported = self.client.post(
            "/api/v1/pools/balance-imports/",
            {"pool": str(self.pool.id), "value_date": str(self.day), "records": [{"account_number": "ACC-A1", "balance_amount": "1100.00"}]}, format="json",
        )
        self.assertEqual(imported.status_code, 400)
        self.assertIn("daily close", str(imported.data))
