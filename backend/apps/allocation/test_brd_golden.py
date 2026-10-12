"""
Golden dataset: the worked allocation example printed in the BRD (Section 7.2)
and on UI Catalogue screens 12/13 (Allocation Simulator / Profit Allocation Run).

    Gross income PKR 12,000,000 - direct expenses 1,000,000 = distributable 11,000,000
    Savings Tier A   60.0M x 1.00  = 60.0M weighted -> 6.60M
    Term Tier B      25.0M x 1.20  = 30.0M weighted -> 3.30M
    Institutional     8.0M x 1.25  = 10.0M weighted -> 1.10M
    Total            93.0M          100.0M          -> 11.00M

The example distributes the whole distributable amount to the participants (no
Mudarib share and no reserves), i.e. a 100/0 profit-sharing ratio with reserves
disabled. The engine must reproduce it exactly, and the two-class example in
BRD 7.2 (A: 60M, B: 40M, weights 1.0 -> 6.6M / 4.4M) as well.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.core.context import set_current_tenant
from apps.pools.models import DailyBalance, Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .engine import calculate_allocation
from .models import PSRStatus, ProfitSharingRatio, WeightageBand, WeightageBandStatus

DAY = date(2026, 8, 29)


class BrdGoldenAllocationTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Golden", code="GOLDEN", data_residency="PK")
        set_current_tenant(self.tenant)
        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name="C", contract_type="mudarabah_unrestricted", version="1", clauses={}
        )
        product = Product.objects.create(
            tenant=self.tenant, name="P", code="P-G", operating_model="bank_pool", contract_template=contract
        )
        self.pool = Pool.objects.create(
            tenant=self.tenant, name="Golden Pool", code="GOLD", product=product, effective_date=date(2026, 1, 1)
        )
        ProfitSharingRatio.objects.create(
            tenant=self.tenant, pool=self.pool, depositor_share=Decimal("100.00"), mudarib_share=Decimal("0.00"),
            effective_from=date(2026, 1, 1), status=PSRStatus.APPROVED,
        )

    def tearDown(self):
        set_current_tenant(None)

    def _class(self, name, balance, weightage):
        DailyBalance.objects.create(
            tenant=self.tenant, pool=self.pool, participant_class=name, value_date=DAY,
            balance_amount=Decimal(balance), status="validated",
        )
        WeightageBand.objects.create(
            tenant=self.tenant, pool=self.pool, participant_class=name, weightage=Decimal(weightage),
            effective_from=date(2026, 1, 1), status=WeightageBandStatus.APPROVED,
        )

    def test_ui_catalogue_three_class_example(self):
        self._class("Savings Tier A", "60000000", "1.00")
        self._class("Term Tier B", "25000000", "1.20")
        self._class("Institutional", "8000000", "1.25")

        result = calculate_allocation(self.pool, DAY, Decimal("12000000"), Decimal("1000000"))
        lines = {l["participant_class"]: l for l in result["lines"]}

        self.assertEqual(result["distributable"], Decimal("11000000.00"))
        self.assertEqual(result["total_weighted_funds"], Decimal("100000000.00"))
        self.assertEqual(lines["Savings Tier A"]["weighted_funds"], Decimal("60000000.00"))
        self.assertEqual(lines["Term Tier B"]["weighted_funds"], Decimal("30000000.00"))
        self.assertEqual(lines["Institutional"]["weighted_funds"], Decimal("10000000.00"))
        self.assertEqual(lines["Savings Tier A"]["allocated_amount"], Decimal("6600000.00"))
        self.assertEqual(lines["Term Tier B"]["allocated_amount"], Decimal("3300000.00"))
        self.assertEqual(lines["Institutional"]["allocated_amount"], Decimal("1100000.00"))
        self.assertEqual(sum(l["allocated_amount"] for l in result["lines"]), Decimal("11000000.00"))
        self.assertEqual(result["mudarib_share"], Decimal("0.00"))
        self.assertEqual(result["rounding_residual"], Decimal("0.00"))

    def test_brd_section_7_2_two_customer_example(self):
        self._class("Customer A", "60000000", "1.00")
        self._class("Customer B", "40000000", "1.00")

        result = calculate_allocation(self.pool, DAY, Decimal("12000000"), Decimal("1000000"))
        lines = {l["participant_class"]: l for l in result["lines"]}

        self.assertEqual(result["distributable"], Decimal("11000000.00"))
        self.assertEqual(lines["Customer A"]["allocated_amount"], Decimal("6600000.00"))
        self.assertEqual(lines["Customer B"]["allocated_amount"], Decimal("4400000.00"))
