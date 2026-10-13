"""
Audit (Phase 5): independent reference calculations for the allocation engine.

Expected values are computed in this file with `fractions.Fraction` from the BRD 7.1 formulas, never with the
engine's own helpers. Runs on Django's throw-away test database.

    cd backend
    set PYTHONPATH=..\\audit_reports   (or PYTHONPATH=../audit_reports)
    python manage.py test audit_tests --noinput -v 2
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.allocation.engine import calculate_allocation
from apps.allocation.models import (
    PSRStatus, ProfitSharingRatio, ReservePolicy, ReserveType, WeightageBand, WeightageBandStatus,
)
from apps.core.context import set_current_tenant
from apps.participants.models import Participant, ParticipantAccount
from apps.pools.models import DailyBalance, Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

D1 = date(2026, 3, 1)


def money(fr):
    """Half-up to 2 places from an exact Fraction (independent of the engine's _round)."""
    return (Decimal(fr.numerator) / Decimal(fr.denominator)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class EngineReferenceTests(TestCase):
    contract_type = "mudarabah_unrestricted"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Audit fin", code="AUD-FIN", data_residency="PK")
        set_current_tenant(self.tenant)
        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name="C", contract_type=self.contract_type, version="1", clauses={}
        )
        product = Product.objects.create(
            tenant=self.tenant, name="P", code="P-AUD", operating_model="bank_pool", contract_template=contract
        )
        self.pool = Pool.objects.create(tenant=self.tenant, name="Audit pool", code="AUDP", product=product,
                                        effective_date=date(2026, 1, 1))
        self.n = 0

    def tearDown(self):
        set_current_tenant(None)

    # helpers ---------------------------------------------------------------------------------
    def psr(self, dep, mud, fee="0"):
        ProfitSharingRatio.objects.create(
            tenant=self.tenant, pool=self.pool, depositor_share=Decimal(dep), mudarib_share=Decimal(mud),
            wakalah_fee_pct=Decimal(fee), effective_from=date(2026, 1, 1), status=PSRStatus.APPROVED,
        )

    def band(self, cls, w, start=date(2026, 1, 1), end=None):
        WeightageBand.objects.create(tenant=self.tenant, pool=self.pool, participant_class=cls, weightage=Decimal(w),
                                     effective_from=start, effective_to=end, status=WeightageBandStatus.APPROVED)

    def account(self, cls, opened=date(2026, 1, 1), closed=None):
        self.n += 1
        p = Participant.objects.create(tenant=self.tenant, reference=f"R{self.n}", full_name=f"Synthetic {self.n}",
                                       participant_class=cls)
        return ParticipantAccount.objects.create(tenant=self.tenant, participant=p, pool=self.pool,
                                                 account_number=f"AUD-{self.n}", opened_date=opened, closed_date=closed)

    def bal(self, acct, day, amount, status="validated"):
        DailyBalance.objects.create(tenant=self.tenant, pool=self.pool, account=acct, participant_class=acct.participant.participant_class,
                                    value_date=day, balance_amount=Decimal(amount), status=status)

    def amounts(self, result):
        return {l["account_number"]: l["allocated_amount"] for l in result["lines"]}

    def assert_identity(self, r):
        total = r["per_amount"] + r["irr_amount"] + r["mudarib_share"] + sum(l["allocated_amount"] for l in r["lines"]) + r["rounding_residual"]
        self.assertEqual(total, r["distributable"])

    # 1. BRD 7.2 worked example ----------------------------------------------------------------
    def test_01_brd_7_2_worked_example(self):
        """Gross 12M - expenses 1M = 11M; A 60M, B 40M weighted (weight 1.0); 100/0 PSR, no reserves."""
        self.psr("100", "0")
        self.band("retail", "1.00")
        a, b = self.account("retail"), self.account("retail")
        self.bal(a, D1, "60000000")
        self.bal(b, D1, "40000000")
        r = calculate_allocation(self.pool, D1, Decimal("12000000"), Decimal("1000000"))
        self.assertEqual(r["distributable"], Decimal("11000000.00"))
        self.assertEqual(self.amounts(r), {a.account_number: Decimal("6600000.00"), b.account_number: Decimal("4400000.00")})
        self.assert_identity(r)

    # 2. PSR applied ------------------------------------------------------------------------------
    def test_02_psr_70_30_and_class_weights(self):
        self.psr("70", "30")
        self.band("savings", "1.00")
        self.band("term", "1.50")
        a, b = self.account("savings"), self.account("term")
        self.bal(a, D1, "60000000")
        self.bal(b, D1, "40000000")
        r = calculate_allocation(self.pool, D1, Decimal("12000000"), Decimal("1000000"))
        dist = Fraction(11000000)
        wa, wb = Fraction(60000000), Fraction(40000000) * Fraction(3, 2)
        dep = dist * Fraction(70, 100)
        self.assertEqual(r["mudarib_share"], money(dist * Fraction(30, 100)))
        self.assertEqual(self.amounts(r)[a.account_number], money(dep * wa / (wa + wb)))
        self.assertEqual(self.amounts(r)[b.account_number], money(dep * wb / (wa + wb)))
        self.assert_identity(r)

    # 3/4. zero and negative income -------------------------------------------------------------
    def test_03_zero_income(self):
        self.psr("70", "30")
        self.band("retail", "1.00")
        a = self.account("retail")
        self.bal(a, D1, "1000")
        r = calculate_allocation(self.pool, D1, Decimal("0"), Decimal("0"))
        self.assertFalse(r["is_loss"])
        self.assertEqual(r["mudarib_share"], Decimal("0.00"))
        self.assertEqual(self.amounts(r)[a.account_number], Decimal("0.00"))

    def test_04_negative_result_loss_by_unweighted_capital_and_no_mudarib_share(self):
        """BRD 7.1: Mudarib share is never a share of capital; loss falls on capital providers by funds."""
        self.psr("70", "30")
        self.band("savings", "1.00")
        self.band("term", "2.00")
        a, b = self.account("savings"), self.account("term")
        self.bal(a, D1, "600")
        self.bal(b, D1, "400")
        r = calculate_allocation(self.pool, D1, Decimal("1000"), Decimal("2000"))
        self.assertTrue(r["is_loss"])
        self.assertEqual(r["mudarib_share"], Decimal("0.00"))
        self.assertEqual(r["per_amount"] + r["irr_amount"], Decimal("0.00"))
        self.assertEqual(self.amounts(r), {a.account_number: Decimal("-600.00"), b.account_number: Decimal("-400.00")})

    # 5. zero weighted funds ----------------------------------------------------------------------
    def test_05_zero_funds_refused(self):
        self.psr("70", "30")
        self.band("retail", "1.00")
        a = self.account("retail")
        self.bal(a, D1, "0")
        with self.assertRaises(ValueError):
            calculate_allocation(self.pool, D1, Decimal("100"), Decimal("0"))

    # 6. single participant ----------------------------------------------------------------------
    def test_06_single_participant_takes_whole_investor_share(self):
        self.psr("80", "20")
        self.band("retail", "1.00")
        a = self.account("retail")
        self.bal(a, D1, "5000")
        r = calculate_allocation(self.pool, D1, Decimal("1000"), Decimal("0"))
        self.assertEqual(self.amounts(r)[a.account_number], Decimal("800.00"))
        self.assertEqual(r["mudarib_share"], Decimal("200.00"))

    # 7/8. mid-period deposit and withdrawal -------------------------------------------------------
    def test_07_mid_period_deposit_and_withdrawal_daily_average(self):
        """10-day period. A holds 100 all period; B opens on day 6 with 100; C withdraws to 0 from day 6."""
        self.psr("100", "0")
        self.band("retail", "1.00")
        start, end = D1, D1 + timedelta(days=9)
        a = self.account("retail")
        b = self.account("retail", opened=D1 + timedelta(days=5))
        c = self.account("retail")
        for i in range(10):
            d = D1 + timedelta(days=i)
            self.bal(a, d, "100")
            if i >= 5:
                self.bal(b, d, "100")
            self.bal(c, d, "100" if i < 5 else "0")
        r = calculate_allocation(self.pool, end, Decimal("1000"), Decimal("0"), period_start=start)
        # independent: average funds A 100, B 50, C 50 -> shares 1/2, 1/4, 1/4
        self.assertEqual(self.amounts(r), {a.account_number: Decimal("500.00"), b.account_number: Decimal("250.00"),
                                           c.account_number: Decimal("250.00")})

    # 9. weightage change -------------------------------------------------------------------------
    def test_09_weightage_change_mid_period_is_day_weighted(self):
        self.psr("100", "0")
        self.band("x", "1.00", start=date(2026, 1, 1), end=D1 + timedelta(days=4))
        self.band("x", "2.00", start=D1 + timedelta(days=5))
        self.band("y", "1.00")
        a, b = self.account("x"), self.account("y")
        for i in range(10):
            d = D1 + timedelta(days=i)
            self.bal(a, d, "100")
            self.bal(b, d, "100")
        r = calculate_allocation(self.pool, D1 + timedelta(days=9), Decimal("1000"), Decimal("0"), period_start=D1)
        wa = Fraction(100 * 5 * 1 + 100 * 5 * 2, 10)  # 150
        wb = Fraction(100)
        self.assertEqual(self.amounts(r)[a.account_number], money(Fraction(1000) * wa / (wa + wb)))
        self.assertEqual(self.amounts(r)[b.account_number], money(Fraction(1000) * wb / (wa + wb)))

    # 10. rounding residual -----------------------------------------------------------------------
    def test_10_rounding_residual_goes_to_rounding_account_not_a_participant(self):
        self.psr("100", "0")
        self.band("retail", "1.00")
        accts = [self.account("retail") for _ in range(3)]
        for x in accts:
            self.bal(x, D1, "100")
        r = calculate_allocation(self.pool, D1, Decimal("100"), Decimal("0"))
        self.assertEqual(sorted(self.amounts(r).values()), [Decimal("33.33")] * 3)
        self.assertEqual(r["rounding_residual"], Decimal("0.01"))
        self.assert_identity(r)

    # 11/12. very large and very small balances ------------------------------------------------------
    def test_11_very_large_balances_exact(self):
        self.psr("65", "35")
        self.band("retail", "1.00")
        a, b = self.account("retail"), self.account("retail")
        self.bal(a, D1, "123456789012.34")
        self.bal(b, D1, "987654321098.76")
        gross = Decimal("98765432101.23")
        r = calculate_allocation(self.pool, D1, gross, Decimal("0"))
        fa, fb = Fraction("123456789012.34"), Fraction("987654321098.76")
        dep = Fraction(str(gross)) * Fraction(65, 100)
        self.assertEqual(self.amounts(r)[a.account_number], money(dep * fa / (fa + fb)))
        self.assertEqual(self.amounts(r)[b.account_number], money(dep * fb / (fa + fb)))
        self.assert_identity(r)

    def test_12_very_small_balance(self):
        self.psr("100", "0")
        self.band("retail", "1.00")
        a, b = self.account("retail"), self.account("retail")
        self.bal(a, D1, "0.01")
        self.bal(b, D1, "999999.99")
        r = calculate_allocation(self.pool, D1, Decimal("1000"), Decimal("0"))
        self.assertEqual(self.amounts(r)[a.account_number], money(Fraction(1000) * Fraction(1, 100000000)))
        self.assert_identity(r)

    # 13. reserve cap ------------------------------------------------------------------------------
    def test_13_per_limited_to_cap_headroom(self):
        """PER 10% of profit, capped at 1% of funds (1,000,000 funds -> cap 10,000; 9,500 already held)."""
        self.psr("100", "0")
        self.band("retail", "1.00")
        a = self.account("retail")
        self.bal(a, D1, "1000000")
        ReservePolicy.objects.create(tenant=self.tenant, pool=self.pool, reserve_type=ReserveType.PER,
                                     rate_percentage=Decimal("10"), cap_percentage=Decimal("1"),
                                     current_balance=Decimal("9500"))
        r = calculate_allocation(self.pool, D1, Decimal("20000"), Decimal("0"))
        self.assertEqual(r["per_amount"], Decimal("500.00"))  # min(2,000, 10,000 - 9,500)
        self.assertEqual(self.amounts(r)[a.account_number], Decimal("19500.00"))

    # 14. unvalidated balances ----------------------------------------------------------------------
    def test_14_pending_unvalidated_balance_is_not_allocated(self):
        """BRD 6.2: balances are validated before they feed a distribution. A run must refuse, not silently skip or include."""
        self.psr("100", "0")
        self.band("retail", "1.00")
        a, b = self.account("retail"), self.account("retail")
        self.bal(a, D1, "100")
        self.bal(b, D1, "100", status="pending")
        with self.assertRaisesMessage(ValueError, "pending validation"):
            calculate_allocation(self.pool, D1, Decimal("1000"), Decimal("0"))

    # 15. invalid PSR totals ------------------------------------------------------------------------
    def test_15_psr_must_total_100(self):
        with self.assertRaises(ValidationError):
            self.psr("60", "30")

    # 16. negative weightage ------------------------------------------------------------------------
    def test_16_negative_weightage_rejected_by_api_serializer(self):
        from apps.allocation.serializers import WeightageBandSerializer

        s = WeightageBandSerializer(data={"pool": str(self.pool.id), "participant_class": "z", "weightage": "-1.00",
                                          "effective_from": "2026-05-01"})
        self.assertFalse(s.is_valid(), "a negative weightage was accepted")


class WakalahReferenceTests(EngineReferenceTests):
    contract_type = "wakalah"

    def test_17_wakalah_fee_on_average_funds(self):
        """Fee 1% p.a. on 100M average funds over 30 days = 100M x 1% x 30/365; then 100/0 sharing."""
        self.psr("100", "0", fee="1.00")
        self.band("retail", "1.00")
        a = self.account("retail")
        for i in range(30):
            self.bal(a, D1 + timedelta(days=i), "100000000")
        r = calculate_allocation(self.pool, D1 + timedelta(days=29), Decimal("500000"), Decimal("0"), period_start=D1)
        fee = Fraction(100000000) * Fraction(1, 100) * Fraction(30, 365)
        self.assertEqual(r["mudarib_share"], money(fee))
        self.assertEqual(self.amounts(r)[a.account_number], money(Fraction(500000) - fee))
