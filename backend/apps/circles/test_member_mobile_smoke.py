from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.pools.models import Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .models import CircleMember, Contribution, ContributionStatus, Payout, PayoutStatus


class MemberMobileHomeDataTests(APITestCase):
    """Smoke test for the endpoints the member mobile page relies on."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Smoke Tenant", code="SMOKE-1", data_residency="PK")
        set_current_tenant(self.tenant)

        self.pool_manager = User.objects.create_user(
            email="smoke-pm@example.com",
            password="password",
            full_name="Smoke PM",
            role=UserRole.POOL_MANAGER,
            tenant=self.tenant,
        )

        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name="Contract", contract_type="mudarabah_unrestricted", version="1", clauses={}
        )
        product = Product.objects.create(
            tenant=self.tenant,
            name="Product",
            code="SMOKE-PRODUCT",
            operating_model="community_circle",
            contract_template=contract,
        )
        self.pool = Pool.objects.create(
            tenant=self.tenant,
            name="Smoke Pool",
            code="SMOKE-POOL",
            product=product,
            effective_date=date(2026, 1, 1),
        )

        self.member = CircleMember.objects.create(
            tenant=self.tenant,
            pool=self.pool,
            member_name="Member One",
            member_reference="MEM-1",
            joined_date=date(2026, 9, 1),
            payout_position=1,
        )
        self.other_member = CircleMember.objects.create(
            tenant=self.tenant,
            pool=self.pool,
            member_name="Member Two",
            member_reference="MEM-2",
            joined_date=date(2026, 9, 1),
            payout_position=2,
        )
        Contribution.objects.create(
            tenant=self.tenant, member=self.member, amount="100.00", contribution_date=date(2026, 9, 5),
            cycle_number=1, status=ContributionStatus.RECEIVED,
        )
        Contribution.objects.create(
            tenant=self.tenant, member=self.other_member, amount="100.00", contribution_date=date(2026, 9, 5),
            cycle_number=1, status=ContributionStatus.PENDING,
        )
        Payout.objects.create(
            tenant=self.tenant, member=self.member, pool=self.pool, cycle_number=1, amount="500.00",
            payout_date=date(2026, 9, 10), status=PayoutStatus.DISBURSED,
        )

        self.client.force_authenticate(user=self.pool_manager)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def tearDown(self):
        set_current_tenant(None)

    def test_member_detail_loads(self):
        response = self.client.get(reverse("circle-member-detail", args=[str(self.member.id)]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["member_reference"], "MEM-1")
        self.assertEqual(response.data["payout_position"], 1)

    def test_contributions_filtered_by_member(self):
        response = self.client.get(reverse("circle-contribution-list"), {"member": str(self.member.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(str(response.data[0]["member"]), str(self.member.id))

    def test_payouts_filtered_by_member(self):
        response = self.client.get(reverse("circle-payout-list"), {"member": str(self.member.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["status"], "disbursed")

    def test_members_by_pool_for_next_turn_computation(self):
        response = self.client.get(reverse("circle-member-list"), {"pool": str(self.pool.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_contributions_filtered_by_pool_for_calendar_view(self):
        response = self.client.get(reverse("circle-contribution-list"), {"pool": str(self.pool.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        dates = {row["contribution_date"] for row in response.data}
        self.assertEqual(dates, {"2026-09-05"})
        statuses = {row["status"] for row in response.data}
        self.assertEqual(statuses, {"received", "pending"})
