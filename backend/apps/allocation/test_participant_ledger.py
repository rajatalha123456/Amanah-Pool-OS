from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounting.models import JournalBatch
from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.participants.models import KYCStatus, Participant, ParticipantAccount
from apps.pools.models import DailyBalance, Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .engine import calculate_allocation
from .models import (
    AllocationLine,
    AllocationRun,
    AllocationRunStatus,
    DepositorStatement,
    PSRStatus,
    ProfitSharingRatio,
    WeightageBand,
    WeightageBandStatus,
)

START = date(2026, 9, 1)
END = date(2026, 9, 10)
DAYS = [START + timedelta(days=i) for i in range(10)]


class ParticipantLedgerTestBase(APITestCase):
    """
    Pool with three accounts over 1-10 Sep 2026:
      * ACC-A1 (retail, Ali):   1,000 every day
      * ACC-A2 (retail, Ali):   opened 6 Sep, 3,000 from then on  -> average 1,500
      * ACC-B1 (premium, Bano): 2,000 every day; weightage 1.5 until 5 Sep, 2.0 after
                                 -> average weighted 3,500 (effective weightage 1.75)
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Ledger", code="LEDGER", data_residency="PK")
        set_current_tenant(self.tenant)

        original_request = self.client.request

        def request_keeping_tenant(**kwargs):
            try:
                return original_request(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = request_keeping_tenant

        self.maker = self._user("maker", UserRole.FINANCE_MAKER)
        self.checker = self._user("checker", UserRole.FINANCE_CHECKER)
        self.pool_manager = self._user("poolmanager", UserRole.POOL_MANAGER)
        self.risk = self._user("risk", UserRole.RISK_COMPLIANCE)
        self.investor_b = self._user("bano", UserRole.INVESTOR_MEMBER)
        self.investor_a = self._user("ali", UserRole.INVESTOR_MEMBER)

        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name="C", contract_type="mudarabah_unrestricted", version="1", clauses={}
        )
        product = Product.objects.create(
            tenant=self.tenant, name="P", code="P-L", operating_model="investment_pool", contract_template=contract
        )
        self.pool = Pool.objects.create(
            tenant=self.tenant, name="Pool", code="POOL-L", product=product, effective_date=date(2026, 1, 1)
        )

        self.ali = self._participant("P-ALI", "Ali Khan", "retail", self.investor_a)
        self.bano = self._participant("P-BANO", "Bano Bibi", "premium", self.investor_b)
        self.a1 = self._account(self.ali, "ACC-A1", date(2026, 1, 1))
        self.a2 = self._account(self.ali, "ACC-A2", date(2026, 9, 6))
        self.b1 = self._account(self.bano, "ACC-B1", date(2026, 1, 1))

        for day in DAYS:
            self._balance(self.a1, day, "1000.00")
            self._balance(self.b1, day, "2000.00")
            if day >= date(2026, 9, 6):
                self._balance(self.a2, day, "3000.00")

        self._band("retail", "1.00", date(2026, 1, 1), None)
        self._band("premium", "1.50", date(2026, 1, 1), date(2026, 9, 5))
        self._band("premium", "2.00", date(2026, 9, 6), None)
        ProfitSharingRatio.objects.create(
            tenant=self.tenant, pool=self.pool, depositor_share=Decimal("70.00"), mudarib_share=Decimal("30.00"),
            effective_from=date(2026, 1, 1), status=PSRStatus.APPROVED,
        )

    def tearDown(self):
        set_current_tenant(None)

    def _user(self, name, role):
        return User.objects.create_user(
            email=f"{name}@ledger.example.com", password="password", full_name=name.title(),
            role=role, tenant=self.tenant,
        )

    def _participant(self, reference, name, participant_class, user=None):
        return Participant.objects.create(
            tenant=self.tenant, reference=reference, full_name=name, participant_class=participant_class,
            kyc_status=KYCStatus.VERIFIED, user=user,
        )

    def _account(self, participant, number, opened):
        return ParticipantAccount.objects.create(
            tenant=self.tenant, participant=participant, pool=self.pool, account_number=number, opened_date=opened
        )

    def _balance(self, account, day, amount):
        return DailyBalance.objects.create(
            tenant=self.tenant, pool=self.pool, account=account,
            participant_class=account.participant.participant_class,
            value_date=day, balance_amount=Decimal(amount), status="validated",
        )

    def _band(self, participant_class, weightage, start, end):
        return WeightageBand.objects.create(
            tenant=self.tenant, pool=self.pool, participant_class=participant_class,
            weightage=Decimal(weightage), effective_from=start, effective_to=end,
            status=WeightageBandStatus.APPROVED,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def create_run(self, gross="600.00"):
        self.authenticate(self.maker)
        response = self.client.post(
            reverse("allocation-run-list"),
            {
                "pool": str(self.pool.id), "period_start": str(START), "value_date": str(END),
                "gross_income": gross, "direct_expenses": "0.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data["id"]

    def sign_run(self, **kwargs):
        run_id = self.create_run(**kwargs)
        self.authenticate(self.maker)
        base = reverse("allocation-run-detail", args=[run_id])
        self.assertEqual(self.client.post(base + "submit-for-checking/").status_code, status.HTTP_200_OK)
        self.authenticate(self.checker)
        response = self.client.post(base + "approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return run_id

    def by_account(self, result):
        return {line["account_number"]: line for line in result["lines"]}


class PeriodEngineTests(ParticipantLedgerTestBase):
    def test_average_funds_and_daily_weightage_over_the_period(self):
        result = calculate_allocation(self.pool, END, Decimal("600.00"), Decimal("0.00"), period_start=START)
        lines = self.by_account(result)

        self.assertEqual(lines["ACC-A1"]["daily_funds"], Decimal("1000.00"))
        self.assertEqual(lines["ACC-A2"]["daily_funds"], Decimal("1500.00"))  # 3,000 x 5 of 10 days
        self.assertEqual(lines["ACC-B1"]["daily_funds"], Decimal("2000.00"))
        self.assertEqual(lines["ACC-B1"]["weightage"], Decimal("1.75"))  # 1.5 for 5 days, 2.0 for 5 days
        self.assertEqual(lines["ACC-B1"]["weighted_funds"], Decimal("3500.00"))
        self.assertEqual(result["total_weighted_funds"], Decimal("6000.00"))
        self.assertEqual(result["config_snapshot"]["period"]["days"], 10)

        # Profit follows weighted funds: B1 holds 3,500 of 6,000.
        total_lines = sum(line["allocated_amount"] for line in result["lines"])
        self.assertAlmostEqual(
            lines["ACC-B1"]["allocated_amount"] / total_lines, Decimal("3500") / Decimal("6000"), places=3
        )

    def test_one_line_per_account_not_per_class(self):
        result = calculate_allocation(self.pool, END, Decimal("600.00"), Decimal("0.00"), period_start=START)
        self.assertEqual(len(result["lines"]), 3)
        self.assertEqual(sorted(line["participant_class"] for line in result["lines"]), ["premium", "retail", "retail"])

    def test_missing_days_carry_the_last_known_balance_forward(self):
        DailyBalance.objects.filter(account=self.a1, value_date__in=[DAYS[2], DAYS[3]]).delete()
        result = calculate_allocation(self.pool, END, Decimal("600.00"), Decimal("0.00"), period_start=START)
        self.assertEqual(self.by_account(result)["ACC-A1"]["daily_funds"], Decimal("1000.00"))

    def test_closed_account_stops_earning(self):
        self.b1.closed_date = date(2026, 9, 5)
        self.b1.save()
        result = calculate_allocation(self.pool, END, Decimal("600.00"), Decimal("0.00"), period_start=START)
        self.assertEqual(self.by_account(result)["ACC-B1"]["daily_funds"], Decimal("1000.00"))  # 5 of 10 days

    def test_psr_change_inside_period_must_be_split(self):
        ProfitSharingRatio.objects.filter(pool=self.pool).update(effective_to=date(2026, 9, 5))
        ProfitSharingRatio.objects.create(
            tenant=self.tenant, pool=self.pool, depositor_share=Decimal("60.00"), mudarib_share=Decimal("40.00"),
            effective_from=date(2026, 9, 6), status=PSRStatus.APPROVED,
        )
        with self.assertRaises(ValueError):
            calculate_allocation(self.pool, END, Decimal("600.00"), Decimal("0.00"), period_start=START)

    def test_single_day_run_still_works(self):
        result = calculate_allocation(self.pool, END, Decimal("100.00"), Decimal("0.00"))
        lines = self.by_account(result)
        self.assertEqual(lines["ACC-A2"]["daily_funds"], Decimal("3000.00"))


class SignedRunLedgerTests(ParticipantLedgerTestBase):
    def test_signing_posts_class_level_journal_and_keeps_participant_sub_ledger(self):
        run_id = self.sign_run()
        run = AllocationRun.objects.get(pk=run_id)
        self.assertEqual(run.status, AllocationRunStatus.SIGNED)
        self.assertEqual(run.period_start, START)
        self.assertEqual(run.lines.count(), 3)
        self.assertTrue(all(line.account_id for line in run.lines.all()))

        batch = JournalBatch.objects.get(allocation_run=run)
        self.assertEqual(batch.total_debit, batch.total_credit)
        retail_total = sum(
            line.allocated_amount for line in run.lines.all() if line.participant_class == "retail"
        )
        retail_entries = batch.entries.filter(account_name="Depositor Payable - retail")
        self.assertEqual(retail_entries.count(), 1)  # one control account per class
        self.assertEqual(retail_entries.first().amount, retail_total)

    def test_tampering_with_an_account_line_breaks_the_seal(self):
        run_id = self.create_run()
        line = AllocationLine._base_manager.filter(allocation_run_id=run_id, account=self.a1).first()
        AllocationLine._base_manager.filter(pk=line.pk).update(account=self.b1)
        self.authenticate(self.maker)
        base = reverse("allocation-run-detail", args=[run_id])
        self.client.post(base + "submit-for-checking/")
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(base + "approve/").status_code, status.HTTP_400_BAD_REQUEST)

    def test_overlapping_signed_runs_are_blocked(self):
        self.sign_run()
        self.authenticate(self.maker)
        response = self.client.post(
            reverse("allocation-run-list"),
            {"pool": str(self.pool.id), "period_start": "2026-09-08", "value_date": "2026-09-10", "gross_income": "50.00"},
            format="json",
        )
        run_id = response.data["id"]
        base = reverse("allocation-run-detail", args=[run_id])
        self.client.post(base + "submit-for-checking/")
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(base + "approve/").status_code, status.HTTP_400_BAD_REQUEST)


class StatementTests(ParticipantLedgerTestBase):
    def generate(self, run_id):
        self.authenticate(self.maker)
        response = self.client.post(reverse("allocation-run-detail", args=[run_id]) + "generate-statements/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def test_statements_are_issued_per_participant_account(self):
        run_id = self.sign_run()
        statements = {s["account_number"]: s for s in self.generate(run_id)}
        self.assertEqual(set(statements), {"ACC-A1", "ACC-A2", "ACC-B1"})

        a2 = statements["ACC-A2"]
        self.assertEqual(Decimal(a2["opening_balance"]), Decimal("0.00"))  # not yet open on 1 Sep
        self.assertEqual(Decimal(a2["net_deposits"]), Decimal("3000.00"))
        self.assertEqual(a2["period_start"], str(START))
        self.assertEqual(a2["period_end"], str(END))
        self.assertEqual(
            Decimal(a2["closing_balance"]), Decimal("3000.00") + Decimal(a2["profit_allocated"])
        )
        self.assertEqual(a2["participant_name"], "Ali Khan")

    def test_investor_sees_only_their_own_statements(self):
        run_id = self.sign_run()
        self.generate(run_id)

        self.authenticate(self.investor_b)
        response = self.client.get(reverse("allocation-run-my-statements"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([s["account_number"] for s in response.data], ["ACC-B1"])

        self.authenticate(self.investor_a)
        response = self.client.get(reverse("allocation-run-my-statements"))
        self.assertEqual(sorted(s["account_number"] for s in response.data), ["ACC-A1", "ACC-A2"])

    def test_investor_cannot_read_runs_or_other_participants_data(self):
        run_id = self.sign_run()
        self.generate(run_id)
        self.authenticate(self.investor_b)
        self.assertEqual(self.client.get(reverse("allocation-run-list")).data, [])
        self.assertEqual(
            self.client.get(reverse("allocation-run-detail", args=[run_id])).status_code, status.HTTP_404_NOT_FOUND
        )
        self.assertEqual(
            self.client.get(reverse("allocation-run-detail", args=[run_id]) + "statements/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(self.client.get(reverse("participant-list")).status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_cannot_use_the_member_endpoint(self):
        self.authenticate(self.maker)
        self.assertEqual(
            self.client.get(reverse("allocation-run-my-statements")).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_statements_exist_in_db_per_account(self):
        run_id = self.sign_run()
        self.generate(run_id)
        self.assertEqual(DepositorStatement.objects.filter(allocation_run_id=run_id, account__isnull=False).count(), 3)


class BalanceImportTests(ParticipantLedgerTestBase):
    url_name = "balance-import-list"

    def post_import(self, records, value_date="2026-09-20"):
        self.authenticate(self.maker)
        return self.client.post(
            reverse(self.url_name), {"pool": str(self.pool.id), "value_date": value_date, "records": records},
            format="json",
        )

    def test_imports_balances_per_account(self):
        response = self.post_import(
            [
                {"account_number": "ACC-A1", "balance_amount": "1100.00"},
                {"account_number": "ACC-B1", "balance_amount": "2100.00"},
            ]
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["matched_records"], 2)
        self.assertEqual(response.data["status"], "balanced")
        row = DailyBalance.objects.get(account=self.a1, value_date=date(2026, 9, 20))
        self.assertEqual(row.participant_class, "retail")

    def test_unverified_kyc_unknown_and_class_level_records_are_rejected(self):
        self.bano.kyc_status = KYCStatus.PENDING
        self.bano.save()
        response = self.post_import(
            [
                {"account_number": "ACC-B1", "balance_amount": "5.00"},
                {"account_number": "ACC-NOPE", "balance_amount": "5.00"},
                {"participant_class": "retail", "balance_amount": "5.00"},
                {"account_number": "ACC-A1", "balance_amount": "1100.00"},
            ]
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["matched_records"], 1)
        self.assertEqual(response.data["exception_count"], 3)
        self.assertEqual(response.data["status"], "exception")

    def test_duplicate_account_balance_for_a_day_is_skipped(self):
        response = self.post_import([{"account_number": "ACC-A1", "balance_amount": "1.00"}], value_date="2026-09-05")
        self.assertEqual(response.data["matched_records"], 0)
        self.assertEqual(response.data["exception_count"], 1)

    def test_account_not_yet_open_is_rejected(self):
        response = self.post_import([{"account_number": "ACC-A2", "balance_amount": "1.00"}], value_date="2026-09-01")
        self.assertEqual(response.data["matched_records"], 0)


class ParticipantApiTests(ParticipantLedgerTestBase):
    def test_pool_manager_creates_participant_and_account_risk_verifies_kyc(self):
        self.authenticate(self.pool_manager)
        response = self.client.post(
            reverse("participant-list"),
            {"reference": "P-NEW", "full_name": "New Person", "participant_class": "retail"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["kyc_status"], "pending")
        participant_id = response.data["id"]

        account = self.client.post(
            reverse("participant-account-list"),
            {"participant": participant_id, "pool": str(self.pool.id), "account_number": "ACC-N1",
             "opened_date": "2026-09-01"},
            format="json",
        )
        self.assertEqual(account.status_code, status.HTTP_201_CREATED, account.data)

        # Only Risk & Compliance decides KYC.
        verify_url = reverse("participant-detail", args=[participant_id]) + "verify-kyc/"
        self.assertEqual(self.client.post(verify_url).status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(self.risk)
        verified = self.client.post(verify_url)
        self.assertEqual(verified.status_code, status.HTTP_200_OK)
        self.assertEqual(verified.data["kyc_status"], "verified")

    def test_kyc_status_cannot_be_set_through_create(self):
        self.authenticate(self.pool_manager)
        response = self.client.post(
            reverse("participant-list"),
            {"reference": "P-X", "full_name": "X", "participant_class": "retail", "kyc_status": "verified"},
            format="json",
        )
        self.assertEqual(response.data["kyc_status"], "pending")

    def test_duplicate_reference_and_account_number_rejected(self):
        self.authenticate(self.pool_manager)
        response = self.client.post(
            reverse("participant-list"),
            {"reference": "P-ALI", "full_name": "Dup", "participant_class": "retail"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(
            reverse("participant-account-list"),
            {"participant": str(self.ali.id), "pool": str(self.pool.id), "account_number": "ACC-A1",
             "opened_date": "2026-09-01"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_close_account(self):
        self.authenticate(self.pool_manager)
        response = self.client.post(reverse("participant-account-detail", args=[self.a1.id]) + "close/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "closed")
        self.assertIsNotNone(response.data["closed_date"])
