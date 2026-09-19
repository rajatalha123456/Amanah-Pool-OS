from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.pools.models import DailyBalance, Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .models import AllocationRunStatus, PSRStatus, ProfitSharingRatio, WeightageBand, WeightageBandStatus


class AllocationRunShariahReviewStageApiTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Shariah Review Test Tenant", code="SR-TEST", data_residency="PK"
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
        self.secretariat = User.objects.create_user(
            email="secretariat@example.com",
            password="password",
            full_name="Shariah Secretariat",
            role=UserRole.SHARIAH_SECRETARIAT,
            tenant=self.tenant,
        )

    def tearDown(self):
        set_current_tenant(None)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def _make_pool(self, operating_model, code_suffix):
        contract = ContractTemplate.objects.create(
            tenant=self.tenant,
            name=f"Contract {code_suffix}",
            contract_type="mudarabah_unrestricted",
            version="1",
            clauses={},
        )
        product = Product.objects.create(
            tenant=self.tenant,
            name=f"Product {code_suffix}",
            code=f"PRODUCT-{code_suffix}",
            operating_model=operating_model,
            contract_template=contract,
        )
        pool = Pool.objects.create(
            tenant=self.tenant,
            name=f"Pool {code_suffix}",
            code=f"POOL-{code_suffix}",
            product=product,
            effective_date=date(2026, 1, 1),
        )
        value_date = date(2026, 9, 15)
        DailyBalance.objects.create(
            tenant=self.tenant,
            pool=pool,
            participant_class="retail",
            value_date=value_date,
            balance_amount=Decimal("1000.00"),
        )
        WeightageBand.objects.create(
            tenant=self.tenant,
            pool=pool,
            participant_class="retail",
            weightage=Decimal("1.00"),
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
        return pool, value_date

    def _create_run(self, pool, value_date):
        self.authenticate(self.maker)
        response = self.client.post(
            reverse("allocation-run-list"),
            {"pool": str(pool.id), "value_date": str(value_date), "gross_income": "100.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["id"]

    def test_bank_pool_run_requires_shariah_sign_off_before_approve(self):
        pool, value_date = self._make_pool("bank_pool", "BANK")
        run_id = self._create_run(pool, value_date)
        detail_url = reverse("allocation-run-detail", args=[run_id])

        get_response = self.client.get(detail_url)
        self.assertTrue(get_response.data["shariah_review_required"])

        self.authenticate(self.maker)
        submit_response = self.client.post(f"{detail_url}submit-for-checking/")
        self.assertEqual(submit_response.status_code, status.HTTP_200_OK)
        self.assertEqual(submit_response.data["status"], "pending_approval")

        # Approve should be rejected before Shariah sign-off happens.
        self.authenticate(self.checker)
        premature_approve = self.client.post(f"{detail_url}approve/")
        self.assertEqual(premature_approve.status_code, status.HTTP_400_BAD_REQUEST)

        # Wrong role cannot sign off.
        self.authenticate(self.checker)
        forbidden_signoff = self.client.post(f"{detail_url}shariah-sign-off/", {"note": "x"}, format="json")
        self.assertEqual(forbidden_signoff.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate(self.secretariat)
        signoff_response = self.client.post(
            f"{detail_url}shariah-sign-off/", {"note": "Reviewed against approved PSR."}, format="json"
        )
        self.assertEqual(signoff_response.status_code, status.HTTP_200_OK)
        self.assertEqual(signoff_response.data["status"], "shariah_review")
        self.assertEqual(signoff_response.data["shariah_review_note"], "Reviewed against approved PSR.")
        self.assertIsNotNone(signoff_response.data["shariah_signed_off_by"])

        self.authenticate(self.checker)
        approve_response = self.client.post(f"{detail_url}approve/")
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data["status"], "signed")

    def test_non_bank_pool_run_skips_shariah_review(self):
        pool, value_date = self._make_pool("investment_pool", "INV")
        run_id = self._create_run(pool, value_date)
        detail_url = reverse("allocation-run-detail", args=[run_id])

        get_response = self.client.get(detail_url)
        self.assertFalse(get_response.data["shariah_review_required"])

        self.authenticate(self.maker)
        self.client.post(f"{detail_url}submit-for-checking/")

        # Sign-off is not applicable for this pool.
        self.authenticate(self.secretariat)
        signoff_response = self.client.post(f"{detail_url}shariah-sign-off/", {"note": "x"}, format="json")
        self.assertEqual(signoff_response.status_code, status.HTTP_400_BAD_REQUEST)

        self.authenticate(self.checker)
        approve_response = self.client.post(f"{detail_url}approve/")
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data["status"], "signed")
