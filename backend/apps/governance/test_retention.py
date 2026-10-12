from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.notifications.models import Notification
from apps.tenants.models import Tenant

from .models import RetentionPolicy
from .retention import run_retention

BASE = "/api/v1/governance/retention-policies/"


class RetentionTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Ret T", code="RET-T", data_residency="PK")
        set_current_tenant(self.tenant)
        original = self.client.request

        def keep_tenant(**kwargs):
            try:
                return original(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = keep_tenant
        self.risk = self._user("risk", UserRole.RISK_COMPLIANCE)
        self.signatory = self._user("sig", UserRole.AUTHORIZED_SIGNATORY)
        self.maker = self._user("maker", UserRole.FINANCE_MAKER)

    def tearDown(self):
        set_current_tenant(None)

    def _user(self, name, role):
        return User.objects.create_user(
            email=f"{name}@example.com", password="password", full_name=name, role=role, tenant=self.tenant
        )

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def propose(self, days=90, category="notifications", basis="Internal policy"):
        return self.client.post(BASE, {"data_category": category, "retention_days": days, "basis": basis}, format="json")

    def approved(self, **kw):
        self.as_user(self.risk)
        pid = self.propose(**kw).data["id"]
        self.as_user(self.signatory)
        self.assertEqual(self.client.post(f"{BASE}{pid}/approve/").status_code, 200)

    def test_proposal_needs_a_sane_period_and_a_basis(self):
        self.as_user(self.risk)
        self.assertEqual(self.propose(days=5).status_code, 400)
        self.assertEqual(self.propose(basis="").status_code, 400)
        self.assertEqual(self.propose(category="ledger").status_code, 400)
        self.assertEqual(self.propose().status_code, 201)

    def test_only_risk_proposes_and_the_proposer_cannot_approve(self):
        self.as_user(self.maker)
        self.assertEqual(self.propose().status_code, 403)
        self.as_user(self.risk)
        pid = self.propose().data["id"]
        self.assertEqual(self.client.post(f"{BASE}{pid}/approve/").status_code, 403)  # risk may not approve at all
        RetentionPolicy.objects.filter(pk=pid).update(proposed_by=self.signatory)
        self.as_user(self.signatory)
        self.assertEqual(self.client.post(f"{BASE}{pid}/approve/").status_code, 400)  # not their own proposal

    def test_new_approval_supersedes_the_old_one(self):
        self.approved(days=90)
        self.approved(days=120)
        statuses = sorted(RetentionPolicy.objects.values_list("status", flat=True))
        self.assertEqual(statuses, ["approved", "superseded"])

    def test_only_old_read_notifications_are_deleted_and_only_when_applied(self):
        self.approved(days=90)
        old = Notification.objects.create(
            tenant=self.tenant, recipient_user=self.risk, category="system", title="old",
            read_at=timezone.now() - timedelta(days=200),
        )
        unread_old = Notification.objects.create(tenant=self.tenant, recipient_user=self.risk, category="system", title="unread")
        recent = Notification.objects.create(
            tenant=self.tenant, recipient_user=self.risk, category="system", title="recent", read_at=timezone.now()
        )
        dry = run_retention(self.tenant, apply=False)
        self.assertEqual(dry[0]["eligible"], 1)
        self.assertTrue(Notification.objects.filter(pk=old.pk).exists())
        run_retention(self.tenant, apply=True)
        self.assertFalse(Notification.objects.filter(pk=old.pk).exists())
        self.assertTrue(Notification.objects.filter(pk__in=[unread_old.pk, recent.pk]).count() == 2)

    def test_without_an_approved_policy_nothing_is_touched(self):
        Notification.objects.create(
            tenant=self.tenant, recipient_user=self.risk, category="system", title="x",
            read_at=timezone.now() - timedelta(days=900),
        )
        self.assertEqual(run_retention(self.tenant, apply=True), [])
        self.assertEqual(Notification.objects.count(), 1)
