from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

from .models import ShariahDecision


class ShariahQuorumTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Q", code="Q-T", data_residency="PK")
        set_current_tenant(self.tenant)
        original = self.client.request

        def keep(**kwargs):
            try:
                return original(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = keep
        self.secretariat = self._user("sec", UserRole.SHARIAH_SECRETARIAT)
        self.boards = [self._user(f"board{i}", UserRole.SHARIAH_BOARD) for i in range(3)]
        self.authenticate(self.secretariat)
        created = self.client.post(
            reverse("shariah-decision-list"),
            {"decision_code": "SD-Q1", "title": "Ruling", "decision_type": "policy_ruling", "description": "d",
             "effective_date": "2026-01-01"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.url = reverse("shariah-decision-detail", args=[created.data["id"]]) + "cast-quorum-vote/"
        self.decision_id = created.data["id"]

    def tearDown(self):
        set_current_tenant(None)

    def _user(self, name, role):
        return User.objects.create_user(
            email=f"{name}@q.example.com", password="password", full_name=name.title(), role=role, tenant=self.tenant
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def vote(self, user, **body):
        self.authenticate(user)
        return self.client.post(self.url, {"vote": "approve", "fiqh_opinion_notes": "Reviewed.", **body}, format="json")

    def test_one_member_cannot_vote_twice_or_under_another_name(self):
        first = self.vote(self.boards[0], scholar_name="Somebody Else")
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data["quorum_votes"][0]["scholar_name"], "Board0")  # the logged-in member, not the payload
        self.assertEqual(self.vote(self.boards[0], scholar_name="A Third Name").status_code, 400)
        self.assertEqual(ShariahDecision._base_manager.get(pk=self.decision_id).status, "draft")

    def test_two_thirds_of_the_board_approves_and_then_votes_close(self):
        self.vote(self.boards[0])
        summary = self.vote(self.boards[1]).data
        self.assertEqual(summary["status"], "approved")
        self.assertEqual(summary["quorum_summary"]["required_votes"], 2)
        self.assertEqual(self.vote(self.boards[2]).status_code, 400)  # ruling no longer a draft

    def test_reasons_are_required_and_the_drafter_cannot_vote(self):
        self.assertEqual(self.vote(self.boards[0], fiqh_opinion_notes="").status_code, 400)
        board_drafted = ShariahDecision._base_manager.get(pk=self.decision_id)
        board_drafted.created_by = self.boards[1]
        board_drafted.save(update_fields=["created_by"])
        self.assertEqual(self.vote(self.boards[1]).status_code, 400)

    def test_a_single_board_member_can_never_reach_quorum(self):
        for member in self.boards[1:]:
            member.is_active = False
            member.save(update_fields=["is_active"])
        self.assertEqual(self.vote(self.boards[0]).status_code, 400)
