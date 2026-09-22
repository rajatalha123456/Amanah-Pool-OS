from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.pools.models import Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .models import ArrearsRecord, ArrearsStatus, CircleMember


class ArrearsRecordTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Arrears Tenant", code="ARREARS-1", data_residency="PK")
        set_current_tenant(self.tenant)

        self.risk_compliance = User.objects.create_user(
            email="risk@example.com", password="password", full_name="Risk User",
            role=UserRole.RISK_COMPLIANCE, tenant=self.tenant,
        )
        self.shariah_secretariat = User.objects.create_user(
            email="shariah-sec@example.com", password="password", full_name="Shariah Sec",
            role=UserRole.SHARIAH_SECRETARIAT, tenant=self.tenant,
        )
        self.pool_manager = User.objects.create_user(
            email="pm@example.com", password="password", full_name="Pool Manager",
            role=UserRole.POOL_MANAGER, tenant=self.tenant,
        )

        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name="Contract", contract_type="mudarabah_unrestricted", version="1", clauses={}
        )
        product = Product.objects.create(
            tenant=self.tenant, name="Product", code="ARREARS-PRODUCT",
            operating_model="community_circle", contract_template=contract,
        )
        self.pool = Pool.objects.create(
            tenant=self.tenant, name="Arrears Pool", code="ARREARS-POOL",
            product=product, effective_date=date(2026, 1, 1),
        )
        self.member = CircleMember.objects.create(
            tenant=self.tenant, pool=self.pool, member_name="Member One",
            member_reference="MEM-1", joined_date=date(2026, 9, 1), payout_position=1,
        )

        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def tearDown(self):
        set_current_tenant(None)

    def test_risk_compliance_can_flag_arrears(self):
        self.client.force_authenticate(user=self.risk_compliance)
        response = self.client.post(
            reverse("circle-member-flag-arrears", args=[str(self.member.id)]),
            {"cycle_number": 1, "expected_amount": "100.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "overdue")
        set_current_tenant(self.tenant)
        self.assertEqual(ArrearsRecord.objects.count(), 1)

    def test_pool_manager_cannot_flag_arrears(self):
        self.client.force_authenticate(user=self.pool_manager)
        response = self.client.post(
            reverse("circle-member-flag-arrears", args=[str(self.member.id)]),
            {"cycle_number": 1, "expected_amount": "100.00"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_flag_arrears_requires_cycle_and_amount(self):
        self.client.force_authenticate(user=self.risk_compliance)
        response = self.client.post(
            reverse("circle-member-flag-arrears", args=[str(self.member.id)]), {},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        details = response.data["error"]["details"]
        self.assertIn("cycle_number", details)
        self.assertIn("expected_amount", details)

    def test_shariah_secretariat_can_grant_hardship(self):
        arrears = ArrearsRecord.objects.create(
            tenant=self.tenant, member=self.member, cycle_number=1,
            expected_amount="100.00", status=ArrearsStatus.OVERDUE,
        )
        self.client.force_authenticate(user=self.shariah_secretariat)
        response = self.client.post(
            reverse("circle-arrears-record-grant-hardship", args=[str(arrears.id)]),
            {"hardship_reason": "Member lost their income source; waiver aligns with hardship principle."},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "hardship_granted")
        arrears.refresh_from_db()
        self.assertEqual(arrears.status, ArrearsStatus.HARDSHIP_GRANTED)
        self.assertEqual(arrears.reviewed_by, self.shariah_secretariat)
        self.assertIsNotNone(arrears.reviewed_at)

    def test_risk_compliance_cannot_grant_hardship(self):
        arrears = ArrearsRecord.objects.create(
            tenant=self.tenant, member=self.member, cycle_number=1,
            expected_amount="100.00", status=ArrearsStatus.OVERDUE,
        )
        self.client.force_authenticate(user=self.risk_compliance)
        response = self.client.post(
            reverse("circle-arrears-record-grant-hardship", args=[str(arrears.id)]),
            {"hardship_reason": "Attempted waiver without Shariah oversight."},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_grant_hardship_requires_reason(self):
        arrears = ArrearsRecord.objects.create(
            tenant=self.tenant, member=self.member, cycle_number=1,
            expected_amount="100.00", status=ArrearsStatus.OVERDUE,
        )
        self.client.force_authenticate(user=self.shariah_secretariat)
        response = self.client.post(
            reverse("circle-arrears-record-grant-hardship", args=[str(arrears.id)]), {},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("hardship_reason", response.data["error"]["details"])

    def test_arrears_records_filtered_by_pool(self):
        ArrearsRecord.objects.create(
            tenant=self.tenant, member=self.member, cycle_number=1,
            expected_amount="100.00", status=ArrearsStatus.OVERDUE,
        )
        self.client.force_authenticate(user=self.risk_compliance)
        response = self.client.get(reverse("circle-arrears-record-list"), {"pool": str(self.pool.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
