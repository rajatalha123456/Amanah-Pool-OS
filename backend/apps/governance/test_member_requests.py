from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.governance.models import SupportRequest
from apps.tenants.models import Tenant

BASE = "/api/v1/governance/support-requests/"


class MemberRequestTests(APITestCase):
    """BRD 13: investors and members can raise disputes and requests, and see only their own."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MR", code="MR-T", data_residency="PK")
        set_current_tenant(self.tenant)
        original = self.client.request

        def keep(**kwargs):
            try:
                return original(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = keep
        self.alice = self._user("alice", UserRole.INVESTOR_MEMBER)
        self.bob = self._user("bob", UserRole.INVESTOR_MEMBER)
        self.risk = self._user("risk", UserRole.RISK_COMPLIANCE)

    def tearDown(self):
        set_current_tenant(None)

    def _user(self, name, role):
        return User.objects.create_user(
            email=f"{name}@example.com", password="password", full_name=name.title(), role=role, tenant=self.tenant
        )

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def raise_request(self, user, **extra):
        self.as_user(user)
        body = {"request_type": "dispute", "subject": "Wrong profit", "description": "My statement looks wrong.", **extra}
        return self.client.post(BASE, body, format="json")

    def test_a_member_raises_a_request_and_the_name_and_priority_come_from_the_login(self):
        response = self.raise_request(self.alice, raised_by_name="Someone Else", priority="high")
        self.assertEqual(response.status_code, 201, response.content)
        stored = SupportRequest.objects.get()
        self.assertEqual((stored.raised_by, stored.raised_by_name, stored.priority, stored.status), (self.alice, "Alice", "medium", "open"))

    def test_members_see_only_their_own_requests(self):
        self.raise_request(self.alice)
        self.raise_request(self.bob, subject="Second member request")
        self.as_user(self.alice)
        listing = self.client.get(BASE)
        self.assertEqual([r["subject"] for r in listing.data], ["Wrong profit"])
        self.as_user(self.risk)
        self.assertEqual(len(self.client.get(BASE).data), 2)  # staff see everything

    def test_a_member_cannot_attach_a_pool_that_is_not_theirs(self):
        self.as_user(self.alice)
        body = {"request_type": "other", "subject": "x", "description": "y", "pool": "00000000-0000-0000-0000-000000000000"}
        self.assertEqual(self.client.post(BASE, body, format="json").status_code, 400)

    def test_staff_are_told_when_a_member_raises_a_request(self):
        from apps.notifications.models import Notification

        self.raise_request(self.alice)
        self.assertTrue(Notification._base_manager.filter(recipient_user=self.risk, related_model="SupportRequest").exists())

    def test_hardship_and_dispute_are_request_types(self):
        for kind in ("hardship_request", "dispute"):
            with self.subTest(kind=kind):
                self.assertEqual(self.raise_request(self.alice, request_type=kind).status_code, 201)
