from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant

from .models import CircleMember, CircleVote, Contribution
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

    # ---- voting, ledger and receipts (BRD 13: member dashboard) ----
    def proposal(self, **extra):
        from datetime import timedelta

        from django.utils import timezone

        from .models import CircleProposal

        return CircleProposal.objects.create(
            tenant=self.tenant, pool=self.pool, title="Change the cycle day", description="Move to the 10th",
            proposal_type="rule_change", voting_deadline=timezone.localdate() + timedelta(days=7), created_by=self.pool_manager,
            **extra,
        )

    def vote(self, user, proposal, decision="approve"):
        self.authenticate(user)
        return self.client.post(BASE + "cast-vote/", {"proposal": str(proposal.id), "decision": decision}, format="json")

    def test_member_sees_open_proposals_and_votes_once_for_themselves(self):
        proposal = self.proposal()
        self.authenticate(self.alice_user)
        listing = self.client.get(BASE + "my-proposals/")
        self.assertEqual(listing.status_code, 200, listing.content)
        self.assertTrue(listing.data[0]["can_vote"])
        self.assertIsNone(listing.data[0]["tally"])  # tallies stay hidden while voting is open
        self.assertEqual(self.vote(self.alice_user, proposal).status_code, 201)
        self.assertEqual(self.vote(self.alice_user, proposal).status_code, 400)  # once only
        vote = CircleVote._base_manager.get(proposal=proposal)
        self.assertEqual((vote.member, vote.method, vote.recorded_by), (self.alice, "portal", self.alice_user))
        self.authenticate(self.alice_user)
        self.assertFalse(self.client.get(BASE + "my-proposals/").data[0]["can_vote"])

    def test_a_member_cannot_vote_for_someone_else_or_in_another_circle(self):
        proposal = self.proposal()
        self.authenticate(self.alice_user)
        body = {"proposal": str(proposal.id), "decision": "approve", "member_id": str(self.bob.id)}
        self.assertEqual(self.client.post(BASE + "cast-vote/", body, format="json").status_code, 201)
        self.assertEqual(CircleVote._base_manager.get(proposal=proposal).member, self.alice)  # the chosen member_id is ignored
        stranger = User.objects.create_user(
            email="stranger@example.com", password="password", full_name="S", role=UserRole.INVESTOR_MEMBER, tenant=self.tenant
        )
        self.assertEqual(self.vote(stranger, proposal).status_code, 400)  # not a member of this circle

    def test_voting_closes_with_the_proposal_and_staff_cannot_use_the_member_endpoint(self):
        proposal = self.proposal()
        self.authenticate(self.pool_manager)
        staff = self.client.post(BASE + "cast-vote/", {"proposal": str(proposal.id), "decision": "approve"}, format="json")
        self.assertEqual(staff.status_code, 403)
        proposal.status = "closed_approved"
        proposal.save(update_fields=["status"])
        self.assertEqual(self.vote(self.alice_user, proposal).status_code, 400)
        self.authenticate(self.alice_user)
        self.assertIsNotNone(self.client.get(BASE + "my-proposals/").data[0]["tally"])  # shown once closed

    def test_staff_cannot_record_a_portal_method_vote(self):
        proposal = self.proposal()
        self.authenticate(self.pool_manager)
        response = self.client.post(
            f"/api/v1/circles/circle-proposals/{proposal.id}/vote/",
            {"member_id": str(self.alice.id), "decision": "approve", "method": "portal"}, format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_pool_ledger_and_receipt_references_are_visible_to_a_member(self):
        self.authenticate(self.alice_user)
        circle = self.client.get(BASE + "my-circles/").data[0]
        self.assertEqual(circle["contributions"][0]["payment_reference"], "REF-M-A")
        ledger = circle["ledger"]
        self.assertEqual((ledger[0]["cycle_number"], ledger[0]["contributions_received"], ledger[0]["collected"]), (1, 2, "2000.00"))
        self.assertNotIn("Bob", str(ledger))  # references and totals only, no personal details of other members
