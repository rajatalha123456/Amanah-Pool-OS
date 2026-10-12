"""Wakalah fee, Musharakah capital-ratio loss (BR-006) and the negligence-case workflow."""

from decimal import ROUND_HALF_UP, Decimal

from django.urls import reverse
from rest_framework import status

from apps.accounting.models import JournalBatch
from apps.accounts.models import UserRole
from apps.allocation.models import PSRStatus, ProfitSharingRatio

from .distribution import calculate_distribution
from .models import (
    CapitalAccount,
    DistributionRunStatus,
    InvestmentDistributionRun,
    NAVSnapshot,
    NegligenceCase,
    NegligenceCaseStatus,
)
from .test_distribution import END, START, MudarabahBase


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ContractBase(MudarabahBase):
    def set_contract(self, contract_type):
        template = self.pool.product.contract_template
        template.contract_type = contract_type
        template.save()

    def set_psr(self, investor, manager, fee="0.00"):
        ProfitSharingRatio.objects.filter(pool=self.pool).update(
            depositor_share=Decimal(investor), mudarib_share=Decimal(manager), wakalah_fee_pct=Decimal(fee)
        )

    def by_ref(self, result):
        return {line["investor_reference"]: line for line in result["lines"]}


class WakalahTests(ContractBase):
    def setUp(self):
        super().setUp()
        self.set_contract("wakalah")

    def expected_fee(self, pct):
        # average units A 1000 + B 500 = 1500 at NAV 1.000000, 10 days of 365
        return Decimal("1500") * Decimal(pct) / 100 * 10 / 365

    def test_fee_is_taken_first_and_the_rest_goes_to_investors(self):
        self.set_psr("100.00", "0.00", fee="2.00")
        result = calculate_distribution(self.pool, START, END, Decimal("1500.00"), Decimal("0.00"))
        fee = money(self.expected_fee("2"))
        self.assertEqual(result["manager_share"], fee)
        self.assertEqual(result["distributable"], Decimal("1500.00"))
        total = result["manager_share"] + result["rounding_residual"] + sum(l["allocated_amount"] for l in result["lines"])
        self.assertEqual(total, result["distributable"])
        self.assertFalse(result["is_loss"])
        self.assertEqual(result["config_snapshot"]["wakalah"]["fee_amount"], str(fee))

    def test_the_psr_mudarib_share_is_an_incentive_on_profit_after_the_fee(self):
        self.set_psr("90.00", "10.00", fee="2.00")
        result = calculate_distribution(self.pool, START, END, Decimal("1500.00"), Decimal("0.00"))
        fee_raw = self.expected_fee("2")
        after_fee = Decimal("1500") - fee_raw
        self.assertEqual(result["manager_share"], money(fee_raw + after_fee * Decimal("0.10")))
        self.assertEqual(result["investor_share"], money(after_fee * Decimal("0.90")))

    def test_the_agent_is_paid_even_when_the_pool_loses_and_investors_bear_the_loss(self):
        self.set_psr("100.00", "0.00", fee="2.00")
        result = calculate_distribution(self.pool, START, END, Decimal("0.50"), Decimal("0.00"))  # profit < fee
        self.assertTrue(result["is_loss"])
        self.assertEqual(result["manager_share"], money(self.expected_fee("2")))
        self.assertLess(sum(l["allocated_amount"] for l in result["lines"]), 0)
        total = result["manager_share"] + result["rounding_residual"] + sum(l["allocated_amount"] for l in result["lines"])
        self.assertEqual(total, Decimal("0.50"))

    def test_fee_needs_a_published_nav_to_value_the_funds(self):
        self.set_psr("100.00", "0.00", fee="2.00")
        NAVSnapshot.objects.all().delete()
        with self.assertRaises(ValueError):
            calculate_distribution(self.pool, START, END, Decimal("100.00"), Decimal("0.00"))

    def test_zero_fee_behaves_like_a_plain_profit_split(self):
        self.set_psr("100.00", "0.00", fee="0.00")
        result = calculate_distribution(self.pool, START, END, Decimal("1500.00"), Decimal("0.00"))
        self.assertEqual(result["manager_share"], Decimal("0.00"))

    def test_signed_wakalah_run_posts_the_fee_to_the_agent_payable(self):
        self.set_psr("100.00", "0.00", fee="2.00")
        run_id = self.sign()
        batch = JournalBatch.objects.get(investment_run_id=run_id)
        self.assertEqual(batch.total_debit, batch.total_credit)
        fee = batch.entries.get(account_key="mudarib_payable")
        self.assertEqual(fee.amount, money(self.expected_fee("2")))

    def test_a_fee_can_only_be_set_on_a_wakalah_pool(self):
        self.set_contract("mudarabah_unrestricted")
        self.authenticate(self.pm)
        response = self.client.post(
            "/api/v1/allocation/psr-schedules/",
            {"pool": str(self.pool.id), "depositor_share": "70.00", "mudarib_share": "30.00",
             "wakalah_fee_pct": "1.50", "effective_from": "2027-01-01"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Wakalah", str(response.data))


class MusharakahBase(ContractBase):
    """Investors A (1000) and B (500) as in the Mudarabah fixture, plus the managing partner with 1000 units."""

    def setUp(self):
        super().setUp()
        self.set_contract("musharakah")
        self.partner = self._account("MP-1", "Managing Partner Bank", self._user("partner", UserRole.INVESTOR_MEMBER))
        self.partner.is_managing_partner = True
        self.partner.save()
        self.subscribe(self.partner, "1000.00", "2026-08-20")
        self.board = self.shariah
        self.risk = self._user("risk", UserRole.RISK_COMPLIANCE)

    def raise_case(self, user=None, **extra):
        self.authenticate(user or self.risk)
        return self.client.post(
            reverse("negligence-case-list"),
            {"pool": str(self.pool.id), "title": "Late impairment disclosure", "allegation": "Manager delayed disclosure.",
             "period_start": str(START), "period_end": str(END), **extra},
            format="json",
        )

    def determine(self, case_id, outcome, user=None, **extra):
        self.authenticate(user or self.board)
        return self.client.post(
            reverse("negligence-case-determine", args=[case_id]),
            {"outcome": outcome, "determination_note": "Board finding.", **extra}, format="json",
        )


class MusharakahDistributionTests(MusharakahBase):
    def test_profit_follows_the_psr_and_the_partner_is_not_an_investor_line(self):
        result = calculate_distribution(self.pool, START, END, Decimal("1500.00"), Decimal("0.00"))
        self.assertEqual(sorted(self.by_ref(result)), ["INV-A", "INV-B"])
        self.assertEqual(result["manager_share"], Decimal("300.00"))  # 20% of profit
        self.assertEqual(result["investor_share"], Decimal("1200.00"))
        self.assertEqual(self.by_ref(result)["INV-A"]["allocated_amount"], Decimal("800.00"))

    def test_loss_follows_capital_ratio_including_the_managing_partners_own_capital(self):
        result = calculate_distribution(self.pool, START, END, Decimal("0.00"), Decimal("300.00"))
        # capital: A 1000, B 500, partner 1000 -> partner 40%
        self.assertTrue(result["is_loss"])
        self.assertEqual(result["manager_share"], Decimal("-120.00"))
        lines = self.by_ref(result)
        self.assertEqual(lines["INV-A"]["allocated_amount"], Decimal("-120.00"))
        self.assertEqual(lines["INV-B"]["allocated_amount"], Decimal("-60.00"))
        self.assertEqual(result["config_snapshot"]["musharakah"]["manager_capital_ratio"], "0.400000000000")

    def test_the_mudarabah_manager_still_bears_no_capital_loss(self):
        self.set_contract("mudarabah_unrestricted")
        self.partner.is_managing_partner = False
        self.partner.save()
        result = calculate_distribution(self.pool, START, END, Decimal("0.00"), Decimal("300.00"))
        self.assertEqual(result["manager_share"], Decimal("0.00"))
        self.assertEqual(sum(l["allocated_amount"] for l in result["lines"]), Decimal("-300.00"))

    def test_a_signed_musharakah_loss_debits_both_the_partner_and_the_investors(self):
        run_id = self.sign(gross="0.00", expenses="300.00")
        batch = JournalBatch.objects.get(investment_run_id=run_id)
        self.assertEqual(batch.total_debit, batch.total_credit)
        debits = {e.account_key: e.amount for e in batch.entries.filter(entry_type="debit")}
        self.assertEqual(debits["mudarib_payable"], Decimal("120.00"))
        self.assertEqual(debits["investor_profit_payable"], Decimal("180.00"))

    def test_only_one_managing_partner_and_only_on_a_musharakah_pool(self):
        self.authenticate(self.pm)
        url = reverse("capital-account-list")
        body = {"pool": str(self.pool.id), "investor_name": "Second", "investor_reference": "MP-2", "is_managing_partner": True}
        self.assertEqual(self.client.post(url, body, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.set_contract("mudarabah_unrestricted")
        self.partner.is_managing_partner = False
        self.partner.save()
        self.assertEqual(self.client.post(url, {**body, "investor_reference": "MP-3"}, format="json").status_code,
                         status.HTTP_400_BAD_REQUEST)


class NegligenceWorkflowTests(MusharakahBase):
    def test_an_open_case_freezes_loss_allocation_but_not_profit(self):
        self.assertEqual(self.raise_case().status_code, status.HTTP_201_CREATED)
        frozen = self.create_run(gross="0.00", expenses="300.00")
        self.assertEqual(frozen.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("frozen", str(frozen.data).lower())
        self.assertEqual(self.create_run(gross="1500.00").status_code, status.HTTP_201_CREATED)

    def test_a_liable_determination_makes_the_manager_bear_that_part_of_the_loss(self):
        case_id = self.raise_case().data["id"]
        determined = self.determine(case_id, "liable", liability_amount="100.00")
        self.assertEqual(determined.status_code, status.HTTP_200_OK, determined.data)

        result = calculate_distribution(self.pool, START, END, Decimal("0.00"), Decimal("300.00"))
        # manager bears 100 outright, then 40% of the remaining 200 by capital ratio = 80 -> 180 in all
        self.assertEqual(result["manager_share"], Decimal("-180.00"))
        lines = self.by_ref(result)
        self.assertEqual(lines["INV-A"]["allocated_amount"], Decimal("-80.00"))
        self.assertEqual(lines["INV-B"]["allocated_amount"], Decimal("-40.00"))
        self.assertEqual(result["config_snapshot"]["musharakah"]["liability_cases"][0]["id"], case_id)

    def test_liability_is_applied_once_and_never_exceeds_the_loss(self):
        case_id = self.raise_case().data["id"]
        self.determine(case_id, "liable", liability_amount="5000.00")  # more than the loss
        result = calculate_distribution(self.pool, START, END, Decimal("0.00"), Decimal("300.00"))
        self.assertEqual(result["manager_share"], Decimal("-300.00"))
        self.assertTrue(all(l["allocated_amount"] == 0 for l in result["lines"]))

        run_id = self.sign(gross="0.00", expenses="300.00")
        self.assertEqual(str(NegligenceCase.objects.get(pk=case_id).applied_run_id), str(run_id))
        # Used up: a later calculation for the period no longer applies it.
        again = calculate_distribution(self.pool, START, END, Decimal("0.00"), Decimal("300.00"))
        self.assertEqual(again["manager_share"], Decimal("-120.00"))

    def test_restating_a_signed_loss_keeps_the_liability_it_already_applied(self):
        case_id = self.raise_case().data["id"]
        self.determine(case_id, "liable", liability_amount="100.00")
        run_id = self.sign(gross="0.00", expenses="300.00")
        self.authenticate(self.maker)
        restated = self.client.post(
            reverse("distribution-run-detail", args=[run_id]) + "restate/",
            {"restatement_reason": "Expenses corrected", "direct_expenses": "400.00"}, format="json",
        )
        self.assertEqual(restated.status_code, status.HTTP_201_CREATED, restated.data)
        # 400 loss: 100 liability + 40% of 300 = 120 -> 220
        self.assertEqual(Decimal(restated.data["manager_share"]), Decimal("-220.00"))
        new_base = reverse("distribution-run-detail", args=[restated.data["id"]])
        self.client.post(new_base + "submit-for-checking/")
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(new_base + "approve/").status_code, status.HTTP_200_OK)
        self.assertEqual(str(NegligenceCase.objects.get(pk=case_id).applied_run_id), str(restated.data["id"]))
        self.assertEqual(InvestmentDistributionRun.objects.get(pk=run_id).status, DistributionRunStatus.REVERSED)

    def test_clearing_the_manager_lifts_the_freeze_and_uses_capital_ratio_only(self):
        case_id = self.raise_case().data["id"]
        self.assertEqual(self.determine(case_id, "cleared").status_code, status.HTTP_200_OK)
        result = calculate_distribution(self.pool, START, END, Decimal("0.00"), Decimal("300.00"))
        self.assertEqual(result["manager_share"], Decimal("-120.00"))

    def test_a_case_opened_after_a_loss_run_was_calculated_blocks_its_approval(self):
        run_id = self.create_run(gross="0.00", expenses="300.00").data["id"]
        base = reverse("distribution-run-detail", args=[run_id])
        self.authenticate(self.maker)
        self.client.post(base + "submit-for-checking/")
        self.raise_case()
        self.authenticate(self.checker)
        response = self.client.post(base + "approve/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("frozen", str(response.data).lower())

    def test_a_determination_after_calculation_also_blocks_a_stale_run(self):
        case_id = self.raise_case().data["id"]
        self.determine(case_id, "cleared")
        run_id = self.create_run(gross="0.00", expenses="300.00").data["id"]  # cleared: no liability
        other = self.raise_case(title="Second allegation")
        self.determine(other.data["id"], "liable", liability_amount="50.00")  # determined after the run
        base = reverse("distribution-run-detail", args=[run_id])
        self.authenticate(self.maker)
        self.client.post(base + "submit-for-checking/")
        self.authenticate(self.checker)
        response = self.client.post(base + "approve/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("negligence determinations", str(response.data).lower())

    def test_only_the_shariah_board_determines_and_it_needs_reasons_and_an_amount(self):
        case_id = self.raise_case().data["id"]
        self.assertEqual(self.determine(case_id, "liable", user=self.risk, liability_amount="10").status_code,
                         status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.determine(case_id, "liable").status_code, status.HTTP_400_BAD_REQUEST)  # no amount
        self.assertEqual(self.determine(case_id, "liable", liability_amount="-5").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.determine(case_id, "maybe").status_code, status.HTTP_400_BAD_REQUEST)
        self.authenticate(self.board)
        blank = self.client.post(
            reverse("negligence-case-determine", args=[case_id]), {"outcome": "cleared"}, format="json"
        )
        self.assertEqual(blank.status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_determined_case_is_final_and_notes_are_append_only(self):
        case_id = self.raise_case().data["id"]
        self.authenticate(self.risk)
        note = self.client.post(reverse("negligence-case-add-note", args=[case_id]), {"note": "Interviewed CFO"}, format="json")
        self.assertEqual(note.status_code, status.HTTP_200_OK)
        self.assertEqual(len(note.data["notes"]), 1)
        self.determine(case_id, "cleared")
        self.assertEqual(self.determine(case_id, "liable", liability_amount="1").status_code, status.HTTP_400_BAD_REQUEST)
        self.authenticate(self.risk)
        self.assertEqual(
            self.client.post(reverse("negligence-case-add-note", args=[case_id]), {"note": "late"}, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        from django.core.exceptions import ValidationError as DjangoValidationError

        case = NegligenceCase.objects.get(pk=case_id)
        case.status = NegligenceCaseStatus.LIABLE
        with self.assertRaises(DjangoValidationError):
            case.save()
        with self.assertRaises(DjangoValidationError):
            case.delete()

    def test_investors_cannot_see_or_raise_cases_and_the_board_is_told(self):
        self.authenticate(self.inv_a)
        self.assertEqual(self.client.get(reverse("negligence-case-list")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.raise_case(user=self.inv_a).status_code, status.HTTP_403_FORBIDDEN)
        self.raise_case()
        from apps.notifications.models import Notification

        self.assertTrue(Notification.objects.filter(recipient_user=self.board, title__contains="investigation").exists())

    def test_cases_only_apply_to_investment_pools_and_valid_periods(self):
        self.authenticate(self.risk)
        bad_period = self.raise_case(period_start="2026-09-10", period_end="2026-09-01")
        self.assertEqual(bad_period.status_code, status.HTTP_400_BAD_REQUEST)
