"""Wakalah fee in the bank-pool allocation engine."""

from decimal import ROUND_HALF_UP, Decimal

from .engine import calculate_allocation
from .models import ProfitSharingRatio
from .test_participant_ledger import END, START, ParticipantLedgerTestBase


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class BankPoolWakalahTests(ParticipantLedgerTestBase):
    def setUp(self):
        super().setUp()
        template = self.pool.product.contract_template
        template.contract_type = "wakalah"
        template.save()
        ProfitSharingRatio.objects.filter(pool=self.pool).update(
            depositor_share=Decimal("100.00"), mudarib_share=Decimal("0.00"), wakalah_fee_pct=Decimal("2.00")
        )

    # average funds: ACC-A1 1000 + ACC-A2 1500 + ACC-B1 2000 = 4500 over 10 days
    FEE = Decimal("4500") * Decimal("2") / 100 * 10 / 365

    def test_the_agent_fee_is_deducted_before_the_depositors_share(self):
        result = calculate_allocation(self.pool, END, Decimal("600.00"), Decimal("0.00"), period_start=START)
        self.assertEqual(result["mudarib_share"], money(self.FEE))
        total = (
            result["mudarib_share"] + result["per_amount"] + result["irr_amount"] + result["rounding_residual"]
            + sum(l["allocated_amount"] for l in result["lines"])
        )
        self.assertEqual(total, result["distributable"])
        self.assertEqual(result["config_snapshot"]["wakalah"]["fee_amount"], str(money(self.FEE)))

    def test_a_loss_still_pays_the_agent_and_the_depositors_bear_the_loss(self):
        result = calculate_allocation(self.pool, END, Decimal("1.00"), Decimal("0.00"), period_start=START)
        self.assertTrue(result["is_loss"])
        self.assertEqual(result["mudarib_share"], money(self.FEE))
        self.assertLess(sum(l["allocated_amount"] for l in result["lines"]), 0)
        total = result["mudarib_share"] + result["rounding_residual"] + sum(l["allocated_amount"] for l in result["lines"])
        self.assertEqual(total, Decimal("1.00"))

    def test_a_mudarabah_pool_ignores_the_fee_field(self):
        template = self.pool.product.contract_template
        template.contract_type = "mudarabah_unrestricted"
        template.save()
        ProfitSharingRatio.objects.filter(pool=self.pool).update(depositor_share=Decimal("70.00"), mudarib_share=Decimal("30.00"))
        result = calculate_allocation(self.pool, END, Decimal("600.00"), Decimal("0.00"), period_start=START)
        self.assertEqual(result["mudarib_share"], Decimal("180.00"))  # plain 30% PSR, no fee
        self.assertIsNone(result["config_snapshot"]["wakalah"])
