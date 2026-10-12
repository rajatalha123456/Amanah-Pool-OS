from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounting.models import JournalBatch
from apps.accounts.models import User, UserRole
from apps.allocation.models import PSRStatus, ProfitSharingRatio
from apps.core.context import set_current_tenant
from apps.participants.models import KYCStatus as ParticipantKYC
from apps.participants.models import Participant
from apps.pools.models import PeriodCloseChecklist, Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .distribution import calculate_distribution
from .models import (
    CapitalAccount,
    DistributionRunStatus,
    InvestmentDistributionLine,
    InvestmentDistributionRun,
    InvestorProfile,
    KYCStatus,
    NAVSnapshot,
    NAVSnapshotStatus,
    UnitMovement,
)

START, END = date(2026, 9, 1), date(2026, 9, 10)


class MudarabahBase(APITestCase):
    """
    Pool with 80/20 investor/manager PSR and two investors:
      A: 1,000 units since 20 Aug            -> average 1,000 over 1-10 Sep
      B: 1,000 units from 6 Sep (5 of 10 days) -> average   500
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Mudarabah", code="MUD-T", data_residency="PK")
        set_current_tenant(self.tenant)
        original_request = self.client.request

        def request_keeping_tenant(**kwargs):
            try:
                return original_request(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = request_keeping_tenant

        self.pm = self._user("pm", UserRole.POOL_MANAGER)
        self.maker = self._user("maker", UserRole.FINANCE_MAKER)
        self.checker = self._user("checker", UserRole.FINANCE_CHECKER)
        self.shariah = self._user("board", UserRole.SHARIAH_BOARD)
        self.inv_a = self._user("inva", UserRole.INVESTOR_MEMBER)
        self.inv_b = self._user("invb", UserRole.INVESTOR_MEMBER)

        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name="C", contract_type="mudarabah_unrestricted", version="1", clauses={}
        )
        product = Product.objects.create(
            tenant=self.tenant, name="P", code="P-MUD", operating_model="investment_pool", contract_template=contract
        )
        self.pool = Pool.objects.create(
            tenant=self.tenant, name="Mudarabah Fund", code="MUD-1", product=product, effective_date=date(2026, 1, 1)
        )
        ProfitSharingRatio.objects.create(
            tenant=self.tenant, pool=self.pool, depositor_share=Decimal("80.00"), mudarib_share=Decimal("20.00"),
            effective_from=date(2026, 1, 1), status=PSRStatus.APPROVED,
        )
        NAVSnapshot.objects.create(
            tenant=self.tenant, pool=self.pool, valuation_date=date(2026, 8, 1),
            total_pool_value=Decimal("1000.00"), total_units_outstanding=Decimal("1000"),
            nav_per_unit=Decimal("1.000000"), status=NAVSnapshotStatus.PUBLISHED,
        )

        self.acc_a = self._account("INV-A", "Investor A", self.inv_a)
        self.acc_b = self._account("INV-B", "Investor B", self.inv_b)
        self.subscribe(self.acc_a, "1000.00", "2026-08-20")
        self.subscribe(self.acc_b, "1000.00", "2026-09-06")

    def tearDown(self):
        set_current_tenant(None)

    def _user(self, name, role):
        return User.objects.create_user(
            email=f"{name}@mud.example.com", password="password", full_name=name.title(), role=role, tenant=self.tenant
        )

    def _account(self, reference, name, user):
        participant = Participant.objects.create(
            tenant=self.tenant, reference=f"P-{reference}", full_name=name, participant_class="investor",
            kyc_status=ParticipantKYC.VERIFIED, user=user,
        )
        account = CapitalAccount.objects.create(
            tenant=self.tenant, pool=self.pool, investor_name=name, investor_reference=reference,
            participant=participant,
        )
        InvestorProfile.objects.create(
            tenant=self.tenant, capital_account=account, kyc_status=KYCStatus.VERIFIED,
            id_document_type="CNIC", id_document_number="42101-0000000-0", date_of_birth=date(1990, 1, 1),
            address="Karachi", risk_tolerance="moderate",
        )
        return account

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def subscribe(self, account, amount, on):
        from .disclosures import ensure_acknowledged

        set_current_tenant(self.tenant)
        ensure_acknowledged(account, self.pm)
        self.authenticate(self.maker)
        response = self.client.post(
            reverse("capital-account-subscribe", args=[account.id]),
            {"amount": amount, "transaction_date": on},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response

    def redeem(self, account, units, on):
        """Maker requests, an independent checker approves."""
        self.authenticate(self.maker)
        requested = self.client.post(
            reverse("capital-account-redeem", args=[account.id]),
            {"units_redeemed": units, "transaction_date": on}, format="json",
        )
        self.assertEqual(requested.status_code, status.HTTP_201_CREATED, requested.data)
        self.authenticate(self.checker)
        approved = self.client.post(reverse("redemption-detail", args=[requested.data["id"]]) + "approve/")
        self.assertEqual(approved.status_code, status.HTTP_200_OK, approved.data)
        return approved

    def create_run(self, gross="1500.00", expenses="0.00", user=None):
        self.authenticate(user or self.maker)
        return self.client.post(
            reverse("distribution-run-list"),
            {"pool": str(self.pool.id), "period_start": str(START), "period_end": str(END),
             "gross_income": gross, "direct_expenses": expenses},
            format="json",
        )

    def sign(self, **kwargs):
        run_id = self.create_run(**kwargs).data["id"]
        self.authenticate(self.maker)
        base = reverse("distribution-run-detail", args=[run_id])
        self.client.post(base + "submit-for-checking/")
        self.authenticate(self.checker)
        response = self.client.post(base + "approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return run_id


class DistributionEngineTests(MudarabahBase):
    def lines(self, result):
        return {line["investor_reference"]: line for line in result["lines"]}

    def test_profit_is_split_by_psr_then_by_time_weighted_units(self):
        result = calculate_distribution(self.pool, START, END, Decimal("1500.00"), Decimal("0.00"))
        lines = self.lines(result)
        self.assertEqual(lines["INV-A"]["average_units"], Decimal("1000.000000"))
        self.assertEqual(lines["INV-B"]["average_units"], Decimal("500.000000"))  # invested 5 of 10 days
        self.assertEqual(result["manager_share"], Decimal("300.00"))  # 20% of profit
        self.assertEqual(result["investor_share"], Decimal("1200.00"))
        self.assertEqual(lines["INV-A"]["allocated_amount"], Decimal("800.00"))
        self.assertEqual(lines["INV-B"]["allocated_amount"], Decimal("400.00"))
        self.assertEqual(result["rounding_residual"], Decimal("0.00"))

    def test_components_always_tie_out_even_with_awkward_amounts(self):
        for gross in ("1000.01", "7777.77", "0.05", "333.33"):
            result = calculate_distribution(self.pool, START, END, Decimal(gross), Decimal("0.00"))
            total = result["manager_share"] + result["rounding_residual"] + sum(
                line["allocated_amount"] for line in result["lines"]
            )
            self.assertEqual(total, result["distributable"], gross)

    def test_loss_is_borne_by_investors_only_pro_rata_to_units(self):
        result = calculate_distribution(self.pool, START, END, Decimal("100.00"), Decimal("400.00"))
        lines = self.lines(result)
        self.assertTrue(result["is_loss"])
        self.assertEqual(result["manager_share"], Decimal("0.00"))  # the Mudarib never shares a capital loss
        self.assertEqual(lines["INV-A"]["allocated_amount"], Decimal("-200.00"))
        self.assertEqual(lines["INV-B"]["allocated_amount"], Decimal("-100.00"))

    def test_account_without_movement_history_is_treated_as_held_throughout(self):
        legacy = CapitalAccount.objects.create(
            tenant=self.tenant, pool=self.pool, investor_name="Legacy", investor_reference="INV-L",
            units_held=Decimal("500"),
        )
        result = calculate_distribution(self.pool, START, END, Decimal("1500.00"), Decimal("0.00"))
        self.assertEqual(self.lines(result)["INV-L"]["average_units"], Decimal("500.000000"))
        self.assertEqual(legacy.movements.count(), 0)

    def test_redemption_stops_earning_from_its_date(self):
        self.redeem(self.acc_a, "400", "2026-09-06")
        result = calculate_distribution(self.pool, START, END, Decimal("1500.00"), Decimal("0.00"))
        # 1,000 units for 5 days then 600 units for 5 days = 800 average.
        self.assertEqual(self.lines(result)["INV-A"]["average_units"], Decimal("800.000000"))

    def test_only_investment_pools_and_a_single_psr_are_accepted(self):
        ProfitSharingRatio.objects.filter(pool=self.pool).update(effective_to=date(2026, 9, 5))
        ProfitSharingRatio.objects.create(
            tenant=self.tenant, pool=self.pool, depositor_share=Decimal("70.00"), mudarib_share=Decimal("30.00"),
            effective_from=date(2026, 9, 6), status=PSRStatus.APPROVED,
        )
        with self.assertRaises(ValueError):
            calculate_distribution(self.pool, START, END, Decimal("100.00"), Decimal("0.00"))

        self.pool.product.operating_model = "bank_pool"
        self.pool.product.save()
        with self.assertRaises(ValueError):
            calculate_distribution(self.pool, START, START, Decimal("100.00"), Decimal("0.00"))


class CapitalJournalTests(MudarabahBase):
    def test_subscription_and_redemption_post_balanced_journals_and_movements(self):
        self.assertEqual(UnitMovement.objects.filter(capital_account=self.acc_a).count(), 1)
        batch = JournalBatch.objects.filter(pool=self.pool, entries__account_name="Investor Capital - MUD-1").first()
        self.assertEqual(batch.total_debit, batch.total_credit)
        accounts = {(e.account_name, e.entry_type) for e in batch.entries.all()}
        self.assertEqual(accounts, {("Settlement Receivable", "debit"), ("Investor Capital - MUD-1", "credit")})

        self.redeem(self.acc_a, "100", "2026-09-02")
        redemption = JournalBatch.objects.filter(
            pool=self.pool, entries__account_name="Redemption Payable"
        ).first()
        self.assertEqual({(e.account_name, e.entry_type) for e in redemption.entries.all()},
                         {("Investor Capital - MUD-1", "debit"), ("Redemption Payable", "credit")})

    def test_capital_movements_are_blocked_in_a_closed_period(self):
        PeriodCloseChecklist.objects.create(
            tenant=self.tenant, pool=self.pool, period_start=date(2026, 9, 1), period_end=date(2026, 9, 30),
            status="locked",
        )
        from .disclosures import ensure_acknowledged

        set_current_tenant(self.tenant)
        ensure_acknowledged(self.acc_a, self.pm)
        self.authenticate(self.maker)
        response = self.client.post(
            reverse("capital-account-subscribe", args=[self.acc_a.id]),
            {"amount": "10.00", "transaction_date": "2026-09-15"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unit_movements_are_append_only(self):
        movement = UnitMovement.objects.first()
        movement.units_delta = Decimal("1")
        with self.assertRaises(DjangoValidationError):
            movement.save()
        with self.assertRaises(DjangoValidationError):
            movement.delete()


class DistributionWorkflowTests(MudarabahBase):
    def test_full_flow_posts_a_balanced_journal_and_seals_the_run(self):
        run_id = self.sign()
        run = InvestmentDistributionRun.objects.get(pk=run_id)
        self.assertEqual(run.status, DistributionRunStatus.SIGNED)
        self.assertEqual(run.manager_share, Decimal("300.00"))

        batch = JournalBatch.objects.get(investment_run=run)
        self.assertEqual(batch.total_debit, batch.total_credit)
        entries = {(e.account_name, e.entry_type): e.amount for e in batch.entries.all()}
        self.assertEqual(entries[("Mudarib Share Payable", "credit")], Decimal("300.00"))
        self.assertEqual(entries[("Investor Profit Payable - MUD-1", "credit")], Decimal("1200.00"))
        self.assertEqual(entries[("Pool Income", "debit")], Decimal("1500.00"))

    def test_loss_run_debits_investor_capital_and_has_no_manager_share(self):
        run_id = self.sign(gross="100.00", expenses="400.00")
        batch = JournalBatch.objects.get(investment_run_id=run_id)
        self.assertEqual(batch.total_debit, batch.total_credit)
        names = {(e.account_name, e.entry_type) for e in batch.entries.all()}
        self.assertIn(("Investor Profit Payable - MUD-1", "debit"), names)
        self.assertNotIn(("Mudarib Share Payable", "credit"), names)

    def test_role_separation_and_maker_checker(self):
        self.assertEqual(self.create_run(user=self.checker).status_code, status.HTTP_403_FORBIDDEN)
        run_id = self.create_run().data["id"]
        base = reverse("distribution-run-detail", args=[run_id])
        self.authenticate(self.maker)
        self.client.post(base + "submit-for-checking/")
        self.assertEqual(self.client.post(base + "approve/").status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(base + "reject/", {}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        rejected = self.client.post(base + "reject/", {"rejection_reason": "Income not final"}, format="json")
        self.assertEqual(rejected.data["status"], "rejected")

    def test_signed_run_is_immutable_and_tampering_blocks_approval(self):
        run_id = self.sign()
        run = InvestmentDistributionRun.objects.get(pk=run_id)
        run.manager_share = Decimal("1.00")
        with self.assertRaises(DjangoValidationError):
            run.save()
        line = run.lines.first()
        line.allocated_amount = Decimal("1.00")
        with self.assertRaises(DjangoValidationError):
            line.save()

        tampered_id = self.create_run(gross="10.00").data["id"]
        InvestmentDistributionLine._base_manager.filter(run_id=tampered_id).update(allocated_amount="999.00")
        base = reverse("distribution-run-detail", args=[tampered_id])
        self.authenticate(self.maker)
        self.client.post(base + "submit-for-checking/")
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(base + "approve/").status_code, status.HTTP_400_BAD_REQUEST)

    def test_overlapping_signed_distributions_are_blocked(self):
        self.sign()
        run_id = self.create_run(gross="50.00").data["id"]
        base = reverse("distribution-run-detail", args=[run_id])
        self.authenticate(self.maker)
        self.client.post(base + "submit-for-checking/")
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(base + "approve/").status_code, status.HTTP_400_BAD_REQUEST)

    def test_closed_period_blocks_new_distribution_but_restatement_still_works(self):
        run_id = self.sign()
        PeriodCloseChecklist.objects.create(
            tenant=self.tenant, pool=self.pool, period_start=date(2026, 9, 1), period_end=date(2026, 9, 30),
            status="locked",
        )
        self.assertEqual(self.create_run().status_code, status.HTTP_400_BAD_REQUEST)

        self.authenticate(self.maker)
        base = reverse("distribution-run-detail", args=[run_id])
        restated = self.client.post(base + "restate/", {"restatement_reason": "Late income", "gross_income": "2000.00"},
                                    format="json")
        self.assertEqual(restated.status_code, status.HTTP_201_CREATED, restated.data)
        self.assertEqual(InvestmentDistributionRun.objects.get(pk=run_id).status, DistributionRunStatus.SIGNED)

        new_base = reverse("distribution-run-detail", args=[restated.data["id"]])
        self.client.post(new_base + "submit-for-checking/")
        self.authenticate(self.checker)
        approved = self.client.post(new_base + "approve/")
        self.assertEqual(approved.status_code, status.HTTP_200_OK, approved.data)

        self.assertEqual(InvestmentDistributionRun.objects.get(pk=run_id).status, DistributionRunStatus.REVERSED)
        old_batch = JournalBatch.objects.get(investment_run_id=run_id)
        reversal = JournalBatch.objects.get(reverses_batch=old_batch)
        self.assertEqual(reversal.total_debit, old_batch.total_debit)
        self.assertEqual(
            InvestmentDistributionRun.objects.get(pk=restated.data["id"]).manager_share, Decimal("400.00")
        )


class InvestorSelfServiceTests(MudarabahBase):
    def test_investors_see_only_their_own_accounts_and_statements(self):
        self.authenticate(self.inv_b)
        listing = self.client.get(reverse("capital-account-list"))
        self.assertEqual([a["investor_reference"] for a in listing.data], ["INV-B"])
        other = self.client.get(reverse("capital-account-statement", args=[self.acc_a.id]))
        self.assertEqual(other.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual([str(s["capital_account"]) for s in self.client.get(reverse("subscription-list")).data],
                         [str(self.acc_b.id)])
        self.assertEqual(len(self.client.get(reverse("investor-profile-list")).data), 1)

    def test_investors_cannot_read_distribution_runs(self):
        run_id = self.sign()
        self.authenticate(self.inv_a)
        self.assertEqual(self.client.get(reverse("distribution-run-list")).data, [])
        self.assertEqual(
            self.client.get(reverse("distribution-run-detail", args=[run_id])).status_code, status.HTTP_404_NOT_FOUND
        )

    def test_statement_shows_units_nav_value_and_signed_distributions(self):
        self.sign()
        self.authenticate(self.inv_b)
        response = self.client.get(
            reverse("capital-account-statement", args=[self.acc_b.id]), {"from": "2026-09-01", "to": "2026-09-10"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data
        self.assertEqual(data["opening_units"], "0.000000")
        self.assertEqual(data["subscribed_units"], "1000.000000")
        self.assertEqual(data["closing_units"], "1000.000000")
        self.assertEqual(data["average_units"], "500.000000")
        self.assertEqual(data["market_value"], "1000.00")
        self.assertEqual(data["total_profit_distributed"], "400.00")
        self.assertEqual(len(data["profit_distributions"]), 1)

    def test_staff_can_open_any_statement(self):
        self.authenticate(self.maker)
        response = self.client.get(reverse("capital-account-statement", args=[self.acc_a.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
