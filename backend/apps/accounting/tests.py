from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.governance.models import ExceptionCase
from apps.pools.models import DailyBalance, Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .models import JournalBatch, JournalEntry, JournalEntryType
from .reconciliation import check_reconciliation
from .services import create_journal_from_allocation
from apps.allocation.models import AllocationLine, AllocationRun


class ReconciliationTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant", code="TEST", data_residency="PK"
        )
        set_current_tenant(self.tenant)
        contract = ContractTemplate.objects.create(
            tenant=self.tenant,
            name="Test Contract",
            contract_type="mudarabah_unrestricted",
            version="1",
            clauses={},
        )
        product = Product.objects.create(
            tenant=self.tenant,
            name="Test Product",
            code="TEST-PRODUCT",
            operating_model="bank_pool",
            contract_template=contract,
        )
        self.pool = Pool.objects.create(
            tenant=self.tenant,
            name="Test Pool",
            code="TEST-POOL",
            product=product,
            effective_date=date(2026, 1, 1),
        )

    def tearDown(self):
        set_current_tenant(None)

    def _batch(self, total):
        run = AllocationRun.objects.create(
            tenant=self.tenant,
            pool=self.pool,
            value_date=date(2026, 1, 10),
            gross_income=total,
            distributable_amount=total,
            total_weighted_funds=total,
            depositor_pool_share=total,
            mudarib_share=Decimal("0"),
        )
        batch = JournalBatch.objects.create(
            tenant=self.tenant,
            allocation_run=run,
            pool=self.pool,
            batch_date=date(2026, 1, 10),
            total_debit=total,
            total_credit=total,
        )
        JournalEntry.objects.create(
            tenant=self.tenant,
            batch=batch,
            account_name="Depositor Payable - retail",
            entry_type=JournalEntryType.CREDIT,
            amount=total,
        )
        return batch

    def test_matching_latest_snapshot_creates_no_exception(self):
        DailyBalance.objects.create(
            tenant=self.tenant,
            pool=self.pool,
            participant_class="retail",
            value_date=date(2026, 1, 9),
            balance_amount=Decimal("999.00"),
        )
        DailyBalance.objects.create(
            tenant=self.tenant,
            pool=self.pool,
            participant_class="retail",
            value_date=date(2026, 1, 10),
            balance_amount=Decimal("60.00"),
        )
        DailyBalance.objects.create(
            tenant=self.tenant,
            pool=self.pool,
            participant_class="corporate",
            value_date=date(2026, 1, 10),
            balance_amount=Decimal("40.00"),
        )

        self._batch(Decimal("60.00"))
        self.assertFalse(check_reconciliation(self._batch(Decimal("40.00"))))
        self.assertFalse(ExceptionCase.objects.exists())

    def test_large_mismatch_creates_high_exception_with_exact_totals(self):
        DailyBalance.objects.create(
            tenant=self.tenant,
            pool=self.pool,
            participant_class="retail",
            value_date=date(2026, 1, 10),
            balance_amount=Decimal("50.00"),
        )

        batch = self._batch(Decimal("100.00"))
        self.assertTrue(check_reconciliation(batch))

        exception = ExceptionCase.objects.get()
        self.assertEqual(exception.source_module, "accounting")
        self.assertEqual(exception.source_object_id, str(batch.id))
        self.assertEqual(exception.severity, "high")
        self.assertIn("100.00", exception.description)
        self.assertIn("50.00", exception.description)
        self.assertIn("100.00%", exception.description)

    @patch("apps.accounting.services.check_reconciliation", side_effect=RuntimeError("test"))
    def test_reconciliation_failure_does_not_block_journal_posting(self, check):
        run = AllocationRun.objects.create(
            tenant=self.tenant,
            pool=self.pool,
            value_date=date(2026, 1, 10),
            gross_income=Decimal("100.00"),
            distributable_amount=Decimal("100.00"),
            total_weighted_funds=Decimal("100.00"),
            depositor_pool_share=Decimal("100.00"),
            mudarib_share=Decimal("0.00"),
        )
        AllocationLine.objects.create(
            tenant=self.tenant,
            allocation_run=run,
            participant_class="retail",
            daily_funds=Decimal("100.00"),
            weightage=Decimal("100.00"),
            weighted_funds=Decimal("100.00"),
            allocated_amount=Decimal("100.00"),
        )

        batch = create_journal_from_allocation(run)

        self.assertIsNotNone(batch.pk)
        check.assert_called_once_with(batch)


class IncomeExpenseEventApiTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="IE Event Test Tenant", code="IE-TEST", data_residency="PK"
        )
        set_current_tenant(self.tenant)
        self.maker = User.objects.create_user(
            email="maker@example.com",
            password="password",
            full_name="Finance Maker",
            role=UserRole.FINANCE_MAKER,
            tenant=self.tenant,
        )
        self.checker = User.objects.create_user(
            email="checker@example.com",
            password="password",
            full_name="Finance Checker",
            role=UserRole.FINANCE_CHECKER,
            tenant=self.tenant,
        )
        self.pool_manager = User.objects.create_user(
            email="manager@example.com",
            password="password",
            full_name="Pool Manager",
            role=UserRole.POOL_MANAGER,
            tenant=self.tenant,
        )
        contract = ContractTemplate.objects.create(
            tenant=self.tenant,
            name="IE Contract",
            contract_type="mudarabah_unrestricted",
            version="1",
            clauses={},
        )
        product = Product.objects.create(
            tenant=self.tenant,
            name="IE Product",
            code="IE-PRODUCT",
            operating_model="bank_pool",
            contract_template=contract,
        )
        self.pool = Pool.objects.create(
            tenant=self.tenant,
            name="IE Pool",
            code="IE-POOL",
            product=product,
            effective_date=date(2026, 1, 1),
        )
        self.list_url = reverse("income-expense-event-list")

    def tearDown(self):
        set_current_tenant(None)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def event_payload(self):
        return {
            "pool": str(self.pool.id),
            "event_type": "income",
            "category": "profit_income",
            "amount": "5000.00",
            "event_date": "2026-09-19",
            "description": "Incidental profit income for the period.",
        }

    def test_create_and_post_event(self):
        self.authenticate(self.maker)
        create_response = self.client.post(self.list_url, self.event_payload(), format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data["status"], "pending")

        detail_url = reverse("income-expense-event-detail", args=[create_response.data["id"]])

        self.authenticate(self.maker)
        forbidden_post = self.client.post(f"{detail_url}post/")
        self.assertEqual(forbidden_post.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate(self.checker)
        post_response = self.client.post(f"{detail_url}post/")
        self.assertEqual(post_response.status_code, status.HTTP_200_OK)
        self.assertEqual(post_response.data["status"], "posted")
        self.assertIsNotNone(post_response.data["posted_by"])

        second_post = self.client.post(f"{detail_url}post/")
        self.assertEqual(second_post.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_role_cannot_create_event(self):
        self.authenticate(self.pool_manager)
        response = self.client.post(self.list_url, self.event_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_filters_by_pool(self):
        self.authenticate(self.maker)
        self.client.post(self.list_url, self.event_payload(), format="json")

        list_response = self.client.get(self.list_url, {"pool": str(self.pool.id)})
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
