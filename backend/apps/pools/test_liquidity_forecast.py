from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.investments.models import CapitalAccount, Redemption, RedemptionStatus
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .models import DailyBalance, DailyBalanceStatus, Pool


class LiquidityForecastApiTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Liquidity Tenant", code="LIQ-1", data_residency="PK")
        set_current_tenant(self.tenant)

        self.user = User.objects.create_user(
            email="user@example.com", password="password", full_name="Any User",
            role=UserRole.RISK_COMPLIANCE, tenant=self.tenant,
        )

        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name="Contract", contract_type="mudarabah_unrestricted", version="1", clauses={}
        )
        self.investment_product = Product.objects.create(
            tenant=self.tenant, name="Investment Product", code="LIQ-INV",
            operating_model="investment_pool", contract_template=contract,
        )
        self.investment_pool = Pool.objects.create(
            tenant=self.tenant, name="Investment Pool", code="LIQ-INV-POOL",
            product=self.investment_product, effective_date=date(2026, 1, 1),
        )

        self.thin_pool = Pool.objects.create(
            tenant=self.tenant, name="Thin History Pool", code="LIQ-THIN-POOL",
            product=self.investment_product, effective_date=date(2026, 1, 1),
        )

        self.client.force_authenticate(user=self.user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def tearDown(self):
        set_current_tenant(None)

    def _seed_daily_balances(self, pool, start_date, count, starting_amount, daily_increment):
        amount = starting_amount
        for i in range(count):
            DailyBalance.objects.create(
                tenant=self.tenant, pool=pool, participant_class="depositors",
                value_date=start_date + timedelta(days=i), balance_amount=amount,
                status=DailyBalanceStatus.VALIDATED,
            )
            amount += daily_increment

    def test_insufficient_data_flag_when_few_records(self):
        self._seed_daily_balances(self.thin_pool, date(2026, 9, 1), count=3, starting_amount=Decimal("1000"), daily_increment=Decimal("10"))
        response = self.client.get(
            reverse("pool-liquidity-forecast", args=[str(self.thin_pool.id)]),
            {"as_of_date": "2026-09-03"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["insufficient_data"])
        self.assertIsNone(response.data["projected_balance"])

    def test_forecast_calculation_with_sufficient_history_no_outflows(self):
        # 10 days, balance increases by 100/day: 1000, 1100, ..., 1900
        self._seed_daily_balances(self.investment_pool, date(2026, 9, 1), count=10, starting_amount=Decimal("1000"), daily_increment=Decimal("100"))
        as_of = date(2026, 9, 10)
        response = self.client.get(
            reverse("pool-liquidity-forecast", args=[str(self.investment_pool.id)]),
            {"as_of_date": as_of.isoformat(), "horizon_days": 30},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertFalse(data["insufficient_data"])
        self.assertEqual(Decimal(data["current_balance"]), Decimal("1900"))
        self.assertEqual(Decimal(data["trend_per_day"]), Decimal("100"))
        self.assertEqual(Decimal(data["known_outflows"]), Decimal("0"))
        expected_projected = Decimal("1900") + Decimal("100") * 30 - Decimal("0")
        self.assertEqual(Decimal(data["projected_balance"]), expected_projected)

    def test_forecast_counts_pending_redemptions_as_outflows(self):
        self._seed_daily_balances(self.investment_pool, date(2026, 9, 1), count=10, starting_amount=Decimal("1000"), daily_increment=Decimal("0"))
        capital_account = CapitalAccount.objects.create(
            tenant=self.tenant, pool=self.investment_pool, investor_name="Investor A",
            investor_reference="INV-A", units_held=Decimal("100"),
        )
        as_of = date(2026, 9, 10)
        Redemption.objects.create(
            tenant=self.tenant, capital_account=capital_account, units_redeemed=Decimal("10"),
            nav_per_unit=Decimal("10"), amount=Decimal("100"),
            transaction_date=as_of + timedelta(days=5), status=RedemptionStatus.PENDING,
        )
        # Outside the horizon window - should not count
        Redemption.objects.create(
            tenant=self.tenant, capital_account=capital_account, units_redeemed=Decimal("5"),
            nav_per_unit=Decimal("10"), amount=Decimal("50"),
            transaction_date=as_of + timedelta(days=60), status=RedemptionStatus.PENDING,
        )
        # Already processed - should not count
        Redemption.objects.create(
            tenant=self.tenant, capital_account=capital_account, units_redeemed=Decimal("2"),
            nav_per_unit=Decimal("10"), amount=Decimal("20"),
            transaction_date=as_of + timedelta(days=2), status=RedemptionStatus.PROCESSED,
        )

        response = self.client.get(
            reverse("pool-liquidity-forecast", args=[str(self.investment_pool.id)]),
            {"as_of_date": as_of.isoformat(), "horizon_days": 30},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["known_outflows"]), Decimal("100"))
