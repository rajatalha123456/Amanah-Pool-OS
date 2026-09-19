from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.governance.models import ExceptionCase, ExceptionSeverity, ExceptionSourceModule
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .models import Pool, PoolStatus


class DailyOperationsCockpitAggregationApiTests(APITestCase):
    """
    Exercises the exact sequence of real HTTP requests the frontend's
    DailyOperationsCockpit.tsx makes to compute its StatCards (Total
    Managed Funds, Open Exceptions, Close Readiness) client-side, since
    there is no dedicated aggregation endpoint - only existing pools,
    balance-imports and governance/exceptions endpoints.
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Cockpit Test Tenant", code="COCKPIT-TEST", data_residency="PK"
        )
        set_current_tenant(self.tenant)
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password",
            full_name="Pool Manager",
            role=UserRole.POOL_MANAGER,
            tenant=self.tenant,
        )
        self.finance_maker = User.objects.create_user(
            email="maker@example.com",
            password="password",
            full_name="Finance Maker",
            role=UserRole.FINANCE_MAKER,
            tenant=self.tenant,
        )

        contract = ContractTemplate.objects.create(
            tenant=self.tenant,
            name="Cockpit Contract",
            contract_type="mudarabah_unrestricted",
            version="1",
            clauses={},
        )
        product = Product.objects.create(
            tenant=self.tenant,
            name="Cockpit Product",
            code="COCKPIT-PRODUCT",
            operating_model="bank_pool",
            contract_template=contract,
        )

        # One in-cycle pool with a balance import already on record...
        self.pool_with_import = Pool.objects.create(
            tenant=self.tenant,
            name="Pool With Import",
            code="COCKPIT-POOL-1",
            product=product,
            effective_date=date(2026, 1, 1),
            status=PoolStatus.ALLOCATION,
        )
        # ...and one in-cycle pool with none yet.
        self.pool_without_import = Pool.objects.create(
            tenant=self.tenant,
            name="Pool Without Import",
            code="COCKPIT-POOL-2",
            product=product,
            effective_date=date(2026, 1, 1),
            status=PoolStatus.OPEN,
        )
        # A draft pool should not count as "in cycle" at all.
        Pool.objects.create(
            tenant=self.tenant,
            name="Draft Pool",
            code="COCKPIT-POOL-3",
            product=product,
            effective_date=date(2026, 1, 1),
            status=PoolStatus.DRAFT,
        )

        ExceptionCase.objects.create(
            tenant=self.tenant,
            source_module=ExceptionSourceModule.OTHER,
            severity=ExceptionSeverity.MEDIUM,
            title="Cockpit test exception",
            description="An open exception for the cockpit to count.",
        )

    def tearDown(self):
        set_current_tenant(None)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def test_cockpit_aggregation_from_real_endpoints(self):
        self.authenticate(self.finance_maker)
        import_response = self.client.post(
            reverse("balance-import-list"),
            {
                "pool": str(self.pool_with_import.id),
                "value_date": "2026-09-19",
                "records": [{"participant_class": "retail", "balance_amount": "1000.00"}],
            },
            format="json",
        )
        self.assertEqual(import_response.status_code, status.HTTP_201_CREATED)

        self.authenticate(self.user)

        pools_response = self.client.get(reverse("pool-list"))
        self.assertEqual(pools_response.status_code, status.HTTP_200_OK)
        pools = pools_response.data
        self.assertEqual(len(pools), 3)

        in_cycle_pools = [p for p in pools if p["status"] in ("open", "allocation")]
        self.assertEqual(len(in_cycle_pools), 2)

        exceptions_response = self.client.get(reverse("exception-case-list"), {"status": "open"})
        self.assertEqual(exceptions_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(exceptions_response.data), 1)

        close_ready_count = 0
        total_managed_funds = Decimal("0")
        for pool in in_cycle_pools:
            history_response = self.client.get(
                reverse("balance-import-list"), {"pool": pool["id"]}
            )
            self.assertEqual(history_response.status_code, status.HTTP_200_OK)
            batches = history_response.data
            if batches:
                close_ready_count += 1
                latest_batch = sorted(batches, key=lambda b: b["value_date"])[-1]
                total_managed_funds += Decimal(latest_batch["control_total_actual"])

        self.assertEqual(close_ready_count, 1)
        self.assertEqual(total_managed_funds, Decimal("1000.00"))

        close_readiness_pct = round((close_ready_count / len(in_cycle_pools)) * 100)
        self.assertEqual(close_readiness_pct, 50)
