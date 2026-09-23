from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.pools.models import Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .models import CircleMember, CircleProposal, CircleVote, ProposalStatus


class CircleProposalTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Proposal Tenant", code="PROPOSAL-1", data_residency="PK")
        set_current_tenant(self.tenant)

        self.pool_manager = User.objects.create_user(
            email="pm@example.com", password="password", full_name="Pool Manager",
            role=UserRole.POOL_MANAGER, tenant=self.tenant,
        )
        self.staff = User.objects.create_user(
            email="staff@example.com", password="password", full_name="Staff User",
            role=UserRole.RISK_COMPLIANCE, tenant=self.tenant,
        )

        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name="Contract", contract_type="mudarabah_unrestricted", version="1", clauses={}
        )
        product = Product.objects.create(
            tenant=self.tenant, name="Product", code="PROPOSAL-PRODUCT",
            operating_model="community_circle", contract_template=contract,
        )
        self.pool = Pool.objects.create(
            tenant=self.tenant, name="Proposal Pool", code="PROPOSAL-POOL",
            product=product, effective_date=date(2026, 1, 1),
        )
        self.member1 = CircleMember.objects.create(
            tenant=self.tenant, pool=self.pool, member_name="Member One",
            member_reference="MEM-1", joined_date=date(2026, 1, 1),
        )
        self.member2 = CircleMember.objects.create(
            tenant=self.tenant, pool=self.pool, member_name="Member Two",
            member_reference="MEM-2", joined_date=date(2026, 1, 1),
        )
        self.member3 = CircleMember.objects.create(
            tenant=self.tenant, pool=self.pool, member_name="Member Three",
            member_reference="MEM-3", joined_date=date(2026, 1, 1),
        )

        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def tearDown(self):
        set_current_tenant(None)

    def _create_proposal(self):
        self.client.force_authenticate(user=self.pool_manager)
        response = self.client.post(
            reverse("circle-proposal-list"),
            {
                "pool": str(self.pool.id),
                "title": "Increase contribution amount",
                "description": "Raise monthly contribution from 100 to 150.",
                "proposal_type": "amount_change",
                "voting_deadline": (date.today() + timedelta(days=7)).isoformat(),
            },
        )
        return response

    def test_pool_manager_can_create_proposal(self):
        response = self._create_proposal()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "open")
        set_current_tenant(self.tenant)
        self.assertEqual(CircleProposal.objects.count(), 1)

    def test_staff_cannot_create_proposal(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            reverse("circle-proposal-list"),
            {
                "pool": str(self.pool.id),
                "title": "Add a new member",
                "description": "Add member four.",
                "proposal_type": "member_addition",
                "voting_deadline": (date.today() + timedelta(days=7)).isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_vote_once(self):
        create_response = self._create_proposal()
        proposal_id = create_response.data["id"]

        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            reverse("circle-proposal-vote", args=[proposal_id]),
            {"member_id": str(self.member1.id), "decision": "approve"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["decision"], "approve")

        # Same member voting again should fail.
        response = self.client.post(
            reverse("circle-proposal-vote", args=[proposal_id]),
            {"member_id": str(self.member1.id), "decision": "reject"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        set_current_tenant(self.tenant)
        self.assertEqual(CircleVote.objects.count(), 1)

    def test_close_with_majority_approve(self):
        create_response = self._create_proposal()
        proposal_id = create_response.data["id"]

        self.client.force_authenticate(user=self.staff)
        self.client.post(
            reverse("circle-proposal-vote", args=[proposal_id]),
            {"member_id": str(self.member1.id), "decision": "approve"},
        )
        self.client.post(
            reverse("circle-proposal-vote", args=[proposal_id]),
            {"member_id": str(self.member2.id), "decision": "approve"},
        )
        self.client.post(
            reverse("circle-proposal-vote", args=[proposal_id]),
            {"member_id": str(self.member3.id), "decision": "reject"},
        )

        self.client.force_authenticate(user=self.pool_manager)
        response = self.client.post(reverse("circle-proposal-close", args=[proposal_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "approved")
        self.assertEqual(response.data["vote_counts"], {"approve": 2, "reject": 1, "abstain": 0})

    def test_close_with_majority_reject(self):
        create_response = self._create_proposal()
        proposal_id = create_response.data["id"]

        self.client.force_authenticate(user=self.staff)
        self.client.post(
            reverse("circle-proposal-vote", args=[proposal_id]),
            {"member_id": str(self.member1.id), "decision": "reject"},
        )
        self.client.post(
            reverse("circle-proposal-vote", args=[proposal_id]),
            {"member_id": str(self.member2.id), "decision": "reject"},
        )
        self.client.post(
            reverse("circle-proposal-vote", args=[proposal_id]),
            {"member_id": str(self.member3.id), "decision": "approve"},
        )

        self.client.force_authenticate(user=self.pool_manager)
        response = self.client.post(reverse("circle-proposal-close", args=[proposal_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "rejected")

    def test_staff_cannot_close_proposal(self):
        create_response = self._create_proposal()
        proposal_id = create_response.data["id"]

        self.client.force_authenticate(user=self.staff)
        response = self.client.post(reverse("circle-proposal-close", args=[proposal_id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_vote_on_closed_proposal(self):
        create_response = self._create_proposal()
        proposal_id = create_response.data["id"]

        self.client.force_authenticate(user=self.pool_manager)
        self.client.post(reverse("circle-proposal-close", args=[proposal_id]))

        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            reverse("circle-proposal-vote", args=[proposal_id]),
            {"member_id": str(self.member1.id), "decision": "approve"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_close_already_closed_proposal(self):
        create_response = self._create_proposal()
        proposal_id = create_response.data["id"]

        self.client.force_authenticate(user=self.pool_manager)
        self.client.post(reverse("circle-proposal-close", args=[proposal_id]))
        response = self.client.post(reverse("circle-proposal-close", args=[proposal_id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
