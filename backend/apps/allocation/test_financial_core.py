from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounting.models import JournalBatch, JournalEntry
from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.pools.models import DailyBalance, PeriodCloseChecklist, PeriodCloseStatus, Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .engine import calculate_allocation, compute_run_hash
from .models import (
    AllocationLine,
    AllocationRun,
    AllocationRunStatus,
    PSRStatus,
    ProfitSharingRatio,
    ReservePolicy,
    ReserveType,
    WeightageBand,
    WeightageBandStatus,
)

VALUE_DATE = date(2026, 9, 15)


class FinancialCoreTestBase(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Fin Core", code="FIN-CORE", data_residency="PK")
        set_current_tenant(self.tenant)

        # TenantMiddleware clears the tenant context after every request; restore
        # it so the test body can keep querying through the tenant-scoped manager.
        original_request = self.client.request

        def request_keeping_tenant(**kwargs):
            try:
                return original_request(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = request_keeping_tenant

        self.maker = self._user("maker", UserRole.FINANCE_MAKER)
        self.checker = self._user("checker", UserRole.FINANCE_CHECKER)
        self.pool = self._make_pool()

    def tearDown(self):
        set_current_tenant(None)

    def _user(self, name, role):
        return User.objects.create_user(
            email=f"{name}@fincore.example.com",
            password="password",
            full_name=name.title(),
            role=role,
            tenant=self.tenant,
        )

    def _make_pool(self, per_rate="2.00", irr_rate="10.00", cap="5.00"):
        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name="C", contract_type="mudarabah_unrestricted", version="1", clauses={}
        )
        product = Product.objects.create(
            tenant=self.tenant,
            name="P",
            code="P-FIN",
            operating_model="investment_pool",  # no Shariah stage: keeps the flow short
            contract_template=contract,
        )
        pool = Pool.objects.create(
            tenant=self.tenant, name="Pool", code="POOL-FIN", product=product, effective_date=date(2026, 1, 1)
        )
        for participant_class, balance, weightage in (("retail", "1000.00", "1.00"), ("premium", "2000.00", "1.50")):
            DailyBalance.objects.create(
                tenant=self.tenant,
                pool=pool,
                participant_class=participant_class,
                value_date=VALUE_DATE,
                balance_amount=Decimal(balance),
            )
            WeightageBand.objects.create(
                tenant=self.tenant,
                pool=pool,
                participant_class=participant_class,
                weightage=Decimal(weightage),
                effective_from=date(2026, 1, 1),
                status=WeightageBandStatus.APPROVED,
            )
        ProfitSharingRatio.objects.create(
            tenant=self.tenant,
            pool=pool,
            depositor_share=Decimal("70.00"),
            mudarib_share=Decimal("30.00"),
            effective_from=date(2026, 1, 1),
            status=PSRStatus.APPROVED,
        )
        self.per = ReservePolicy.objects.create(
            tenant=self.tenant, pool=pool, reserve_type=ReserveType.PER,
            rate_percentage=Decimal(per_rate), cap_percentage=Decimal(cap),
        )
        self.irr = ReservePolicy.objects.create(
            tenant=self.tenant, pool=pool, reserve_type=ReserveType.IRR,
            rate_percentage=Decimal(irr_rate), cap_percentage=Decimal(cap),
        )
        return pool

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def create_run(self, gross="100.03", expenses="0.00"):
        self.authenticate(self.maker)
        response = self.client.post(
            reverse("allocation-run-list"),
            {
                "pool": str(self.pool.id),
                "value_date": str(VALUE_DATE),
                "gross_income": gross,
                "direct_expenses": expenses,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data["id"]

    def detail(self, run_id, suffix=""):
        return reverse("allocation-run-detail", args=[run_id]) + suffix

    def submit(self, run_id):
        self.authenticate(self.maker)
        response = self.client.post(self.detail(run_id, "submit-for-checking/"))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def approve(self, run_id):
        self.authenticate(self.checker)
        return self.client.post(self.detail(run_id, "approve/"))

    def sign_run(self, **kwargs):
        run_id = self.create_run(**kwargs)
        self.submit(run_id)
        response = self.approve(run_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return run_id


class EngineTieOutTests(FinancialCoreTestBase):
    def test_components_always_tie_out_to_distributable(self):
        for gross in ("100.03", "999.97", "1.01", "12345.67"):
            result = calculate_allocation(self.pool, VALUE_DATE, Decimal(gross), Decimal("0.00"))
            total = (
                result["per_amount"]
                + result["irr_amount"]
                + result["mudarib_share"]
                + sum(line["allocated_amount"] for line in result["lines"])
                + result["rounding_residual"]
            )
            self.assertEqual(total, result["distributable"], gross)
            self.assertLessEqual(abs(result["rounding_residual"]), Decimal("0.05"))

    def test_reserve_cap_limits_appropriation(self):
        # Cap = 5% of 3,000 total funds = 150; PER already holds 149.50.
        self.per.current_balance = Decimal("149.50")
        self.per.save()
        result = calculate_allocation(self.pool, VALUE_DATE, Decimal("1000.00"), Decimal("0.00"))
        self.assertEqual(result["per_amount"], Decimal("0.50"))

    def test_loss_has_no_reserves_or_mudarib_share(self):
        result = calculate_allocation(self.pool, VALUE_DATE, Decimal("10.00"), Decimal("40.00"))
        self.assertTrue(result["is_loss"])
        self.assertEqual(result["per_amount"], Decimal("0.00"))
        self.assertEqual(result["irr_amount"], Decimal("0.00"))
        self.assertEqual(result["mudarib_share"], Decimal("0.00"))
        # Loss follows unweighted funds: 1000 : 2000
        by_class = {line["participant_class"]: line["allocated_amount"] for line in result["lines"]}
        self.assertEqual(by_class["retail"], Decimal("-10.00"))
        self.assertEqual(by_class["premium"], Decimal("-20.00"))


class ApprovalPostingTests(FinancialCoreTestBase):
    def test_signing_posts_balanced_journal_with_reserves_and_updates_balances(self):
        run_id = self.sign_run()
        run = AllocationRun.objects.get(pk=run_id)
        self.assertEqual(run.status, AllocationRunStatus.SIGNED)
        self.assertGreater(run.per_amount, 0)
        self.assertGreater(run.irr_amount, 0)

        batch = JournalBatch.objects.get(allocation_run=run)
        self.assertEqual(batch.total_debit, batch.total_credit)
        accounts = {e.account_name for e in batch.entries.all()}
        self.assertTrue({"Pool Income", "PER Reserve", "IRR Reserve", "Mudarib Share Payable"} <= accounts)

        self.per.refresh_from_db()
        self.irr.refresh_from_db()
        self.assertEqual(self.per.current_balance, run.per_amount)
        self.assertEqual(self.irr.current_balance, run.irr_amount)

    def test_loss_run_posts_balanced_journal_without_negative_amounts(self):
        run_id = self.sign_run(gross="10.00", expenses="40.00")
        batch = JournalBatch.objects.get(allocation_run_id=run_id)
        self.assertEqual(batch.total_debit, batch.total_credit)
        for entry in batch.entries.all():
            self.assertGreater(entry.amount, 0)
        self.assertTrue(
            batch.entries.filter(account_name="Depositor Payable - retail", entry_type="debit").exists()
        )

    def test_tampered_run_cannot_be_approved(self):
        run_id = self.create_run()
        AllocationLine._base_manager.filter(allocation_run_id=run_id, participant_class="retail").update(
            allocated_amount=Decimal("999.00")
        )
        self.submit(run_id)
        response = self.approve(run_id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AllocationRun.objects.get(pk=run_id).status, AllocationRunStatus.PENDING_APPROVAL)
        self.assertFalse(JournalBatch.objects.filter(allocation_run_id=run_id).exists())

    def test_second_signed_run_for_same_pool_and_date_is_blocked(self):
        self.sign_run()
        run_id = self.create_run(gross="50.00")
        self.submit(run_id)
        response = self.approve(run_id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ImmutabilityTests(FinancialCoreTestBase):
    def test_signed_run_cannot_be_edited_or_deleted(self):
        run_id = self.sign_run()
        run = AllocationRun.objects.get(pk=run_id)
        run.mudarib_share = Decimal("1.00")
        with self.assertRaises(DjangoValidationError):
            run.save()
        with self.assertRaises(DjangoValidationError):
            run.save(update_fields=["mudarib_share", "updated_at"])
        with self.assertRaises(DjangoValidationError):
            run.delete()

        line = run.lines.first()
        line.allocated_amount = Decimal("1.00")
        with self.assertRaises(DjangoValidationError):
            line.save()

    def test_posted_journal_cannot_be_edited_or_deleted(self):
        run_id = self.sign_run()
        batch = JournalBatch.objects.get(allocation_run_id=run_id)
        entry = batch.entries.first()
        entry.amount = Decimal("1.00")
        with self.assertRaises(DjangoValidationError):
            entry.save()
        with self.assertRaises(DjangoValidationError):
            entry.delete()
        with self.assertRaises(DjangoValidationError):
            batch.delete()

    def test_stored_hash_matches_recomputation(self):
        run_id = self.create_run()
        run = AllocationRun.objects.get(pk=run_id)
        self.assertEqual(run.calculation_hash, compute_run_hash(run))
        self.assertIn("psr", run.config_snapshot)


class RestatementTests(FinancialCoreTestBase):
    def restate(self, run_id, user=None, **payload):
        self.authenticate(user or self.maker)
        body = {"restatement_reason": "Late-booked income", **payload}
        return self.client.post(self.detail(run_id, "restate/"), body, format="json")

    def test_checker_cannot_initiate_restatement(self):
        run_id = self.sign_run()
        self.assertEqual(self.restate(run_id, user=self.checker).status_code, status.HTTP_403_FORBIDDEN)

    def test_original_stays_signed_until_rerun_is_approved(self):
        run_id = self.sign_run()
        response = self.restate(run_id, gross_income="200.00")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(AllocationRun.objects.get(pk=run_id).status, AllocationRunStatus.SIGNED)
        self.assertEqual(JournalBatch.objects.filter(reverses_batch__isnull=False).count(), 0)
        # Only one open rerun at a time.
        self.assertEqual(self.restate(run_id, gross_income="300.00").status_code, status.HTTP_400_BAD_REQUEST)

    def test_approving_rerun_reverses_original_journal_and_reserves(self):
        run_id = self.sign_run()
        old_batch = JournalBatch.objects.get(allocation_run_id=run_id)

        response = self.restate(run_id, gross_income="200.00")
        new_id = response.data["id"]
        self.submit(new_id)
        approve = self.approve(new_id)
        self.assertEqual(approve.status_code, status.HTTP_200_OK, approve.data)

        old = AllocationRun.objects.get(pk=run_id)
        new = AllocationRun.objects.get(pk=new_id)
        self.assertEqual(old.status, AllocationRunStatus.REVERSED)
        self.assertEqual(new.status, AllocationRunStatus.SIGNED)

        reversal = JournalBatch.objects.get(reverses_batch=old_batch)
        self.assertEqual(reversal.total_debit, old_batch.total_debit)
        self.assertEqual(
            JournalEntry.objects.filter(batch=reversal, entry_type="debit").count(),
            old_batch.entries.filter(entry_type="credit").count(),
        )

        self.per.refresh_from_db()
        self.assertEqual(self.per.current_balance, new.per_amount)  # old PER taken back out

    def test_zero_gross_income_is_honoured_not_replaced_by_old_value(self):
        run_id = self.sign_run()
        response = self.restate(run_id, gross_income="0.00", direct_expenses="0.00")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Decimal(response.data["gross_income"]), Decimal("0.00"))

    def test_restatement_needs_real_balances_no_silent_fallback(self):
        run_id = self.sign_run()
        DailyBalance._base_manager.filter(pool=self.pool).delete()
        response = self.restate(run_id, gross_income="200.00")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AllocationRun.objects.get(pk=run_id).status, AllocationRunStatus.SIGNED)


class PeriodLockTests(FinancialCoreTestBase):
    def lock_period(self, state=PeriodCloseStatus.LOCKED):
        PeriodCloseChecklist.objects.create(
            tenant=self.tenant,
            pool=self.pool,
            period_start=date(2026, 9, 1),
            period_end=date(2026, 9, 30),
            status=state,
        )

    def test_allocation_run_blocked_in_closed_period(self):
        self.lock_period()
        self.authenticate(self.maker)
        response = self.client.post(
            reverse("allocation-run-list"),
            {"pool": str(self.pool.id), "value_date": str(VALUE_DATE), "gross_income": "10.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_certified_period_also_blocks(self):
        self.lock_period(PeriodCloseStatus.CERTIFIED)
        self.authenticate(self.maker)
        response = self.client.post(
            reverse("allocation-run-list"),
            {"pool": str(self.pool.id), "value_date": str(VALUE_DATE), "gross_income": "10.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_balance_import_blocked_in_closed_period(self):
        self.lock_period()
        self.authenticate(self.maker)
        response = self.client.post(
            reverse("balance-import-list"),
            {
                "pool": str(self.pool.id),
                "value_date": "2026-09-20",
                "records": [{"participant_class": "retail", "balance_amount": "10.00"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_restatement_is_still_possible_after_period_lock(self):
        run_id = self.sign_run()
        self.lock_period()
        response = self.client.post(
            self.detail(run_id, "restate/"), {"restatement_reason": "Audit adjustment"}, format="json"
        )
        self.authenticate(self.maker)
        response = self.client.post(
            self.detail(run_id, "restate/"), {"restatement_reason": "Audit adjustment"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        new_id = response.data["id"]
        self.submit(new_id)
        self.assertEqual(self.approve(new_id).status_code, status.HTTP_200_OK)
