from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant

from .models import CircleMember, Contribution
from .rules import publish_rules
from .tests import CircleRotationApiTests

BASE = "/api/v1/circles/circle-members/"


class MemberPortalTests(APITestCase):
    """A member signs in with their own login and sees/accepts only their own circle data."""

    authenticate = CircleRotationApiTests.authenticate
    _make_pool = CircleRotationApiTests._make_pool

    def setUp(self):
        CircleRotationApiTests.setUp(self)
        set_current_tenant(self.tenant)
        self.alice_user = User.objects.create_user(
            email="alice@example.com", password="password", full_name="Alice", role=UserRole.INVESTOR_MEMBER, tenant=self.tenant
        )
        self.bob_user = User.objects.create_user(
            email="bob@example.com", password="password", full_name="Bob", role=UserRole.INVESTOR_MEMBER, tenant=self.tenant
        )
        self.alice = CircleMember.objects.create(
            tenant=self.tenant, pool=self.pool, member_name="Alice", member_reference="M-A", joined_date=date(2026, 1, 1),
            user=self.alice_user,
        )
        self.bob = CircleMember.objects.create(
            tenant=self.tenant, pool=self.pool, member_name="Bob", member_reference="M-B", joined_date=date(2026, 1, 1),
            user=self.bob_user,
        )
        publish_rules(
            pool=self.pool, user=self.pool_manager, contribution_amount=Decimal("1000"), cycle_days=30,
            order_policy="Random draw", hardship_policy="Review",
        )
        for member in (self.alice, self.bob):
            Contribution.objects.create(
                tenant=self.tenant, member=member, cycle_number=1, amount=Decimal("1000"),
                contribution_date=date(2026, 2, 1), status="received", payment_reference=f"REF-{member.member_reference}",
            )

    def tearDown(self):
        set_current_tenant(None)

    def test_member_sees_only_their_own_membership(self):
        self.authenticate(self.alice_user)
        response = self.client.get(BASE + "my-circles/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([m["member_reference"] for m in response.data], ["M-A"])
        self.assertEqual(len(response.data[0]["contributions"]), 1)
        self.assertFalse(response.data[0]["rules"]["accepted"])

    def test_member_accepts_rules_with_own_login_and_only_for_self(self):
        self.authenticate(self.alice_user)
        body = {"pool": str(self.pool.id), "method": "e_sign", "evidence_reference": "ESIGN-1"}
        self.assertEqual(self.client.post(BASE + "accept-rules/", body, format="json").status_code, 201)
        self.assertEqual(self.client.post(BASE + "accept-rules/", body, format="json").status_code, 400)  # twice
        self.assertTrue(self.client.get(BASE + "my-circles/").data[0]["rules"]["accepted"])
        self.authenticate(self.bob_user)
        self.assertFalse(self.client.get(BASE + "my-circles/").data[0]["rules"]["accepted"])  # Bob unaffected

    def test_member_cannot_reach_staff_circle_endpoints(self):
        self.authenticate(self.alice_user)
        self.assertEqual(self.client.get(BASE).status_code, 403)
        # The deny-by-default list (JWT layer) for contributions/payouts is asserted in core.test_access_control.

    def test_staff_cannot_use_member_endpoints(self):
        self.authenticate(self.pool_manager)
        self.assertEqual(self.client.get(BASE + "my-circles/").status_code, 403)

    def test_pool_manager_links_a_login_but_not_one_already_used_in_the_circle(self):
        carol = CircleMember.objects.create(
            tenant=self.tenant, pool=self.pool, member_name="Carol", member_reference="M-C", joined_date=date(2026, 1, 1)
        )
        self.authenticate(self.pool_manager)
        taken = self.client.post(f"{BASE}{carol.id}/link-login/", {"email": "alice@example.com"}, format="json")
        self.assertEqual(taken.status_code, 400)
        carol_user = User.objects.create_user(
            email="carol@example.com", password="password", full_name="Carol", role=UserRole.INVESTOR_MEMBER, tenant=self.tenant
        )
        ok = self.client.post(f"{BASE}{carol.id}/link-login/", {"email": carol_user.email}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
