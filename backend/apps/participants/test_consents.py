
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

from .models import Consent, Participant

BASE = "/api/v1/participants/consents/"


class ConsentTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Consent T", code="CONSENT-T", data_residency="PK")
        set_current_tenant(self.tenant)
        original = self.client.request

        def keep_tenant(**kwargs):
            try:
                return original(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = keep_tenant
        self.pm = self._user("pm", UserRole.POOL_MANAGER)
        self.maker = self._user("maker", UserRole.FINANCE_MAKER)
        self.alice_user = self._user("alice", UserRole.INVESTOR_MEMBER)
        self.bob_user = self._user("bob", UserRole.INVESTOR_MEMBER)
        self.alice = Participant.objects.create(
            tenant=self.tenant, reference="P-A", full_name="Alice", participant_class="Retail", user=self.alice_user
        )
        self.bob = Participant.objects.create(
            tenant=self.tenant, reference="P-B", full_name="Bob", participant_class="Retail", user=self.bob_user
        )

    def tearDown(self):
        set_current_tenant(None)

    def _user(self, name, role):
        return User.objects.create_user(
            email=f"{name}@example.com", password="password", full_name=name, role=role, tenant=self.tenant
        )

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def grant(self, participant, purpose="electronic_statements", **extra):
        body = {"participant": str(participant.id), "purpose": purpose, "method": "in_person", **extra}
        return self.client.post(BASE, body, format="json")

    def test_staff_record_a_consent_once_per_purpose(self):
        self.as_user(self.pm)
        self.assertEqual(self.grant(self.alice).status_code, 201)
        self.assertEqual(self.grant(self.alice).status_code, 400)  # already live
        self.assertEqual(self.grant(self.alice, purpose="marketing").status_code, 201)

    def test_remote_methods_need_evidence_and_unknown_purposes_are_refused(self):
        self.as_user(self.pm)
        self.assertEqual(self.grant(self.alice, method="e_sign").status_code, 400)
        self.assertEqual(self.grant(self.alice, method="e_sign", evidence_reference="ESIGN-9").status_code, 201)
        self.assertEqual(self.grant(self.alice, purpose="sell_my_data").status_code, 400)

    def test_withdrawal_keeps_history_and_allows_a_new_grant(self):
        self.as_user(self.pm)
        consent_id = self.grant(self.alice).data["id"]
        done = self.client.post(f"{BASE}{consent_id}/withdraw/", {"reason": "Asked in branch"}, format="json")
        self.assertEqual(done.status_code, 200)
        self.assertEqual(self.client.post(f"{BASE}{consent_id}/withdraw/", {}, format="json").status_code, 400)
        self.assertEqual(self.grant(self.alice).status_code, 201)
        self.assertEqual(Consent.objects.filter(participant=self.alice).count(), 2)

    def test_a_member_sees_and_withdraws_only_their_own_consents(self):
        self.as_user(self.pm)
        alice_consent = self.grant(self.alice).data["id"]
        self.grant(self.bob)
        self.as_user(self.alice_user)
        mine = self.client.get(BASE + "mine/")
        self.assertEqual(len(mine.data), 1)
        self.assertEqual(mine.data[0]["id"], alice_consent)
        self.as_user(self.bob_user)
        self.assertEqual(self.client.post(f"{BASE}{alice_consent}/withdraw/", {}, format="json").status_code, 400)
        self.as_user(self.alice_user)
        self.assertEqual(self.client.post(f"{BASE}{alice_consent}/withdraw/", {"reason": "No"}, format="json").status_code, 200)

    def test_data_subject_export_contains_only_the_callers_data(self):
        self.as_user(self.pm)
        self.grant(self.alice)
        self.as_user(self.alice_user)
        data = self.client.get(BASE + "my-data/").data
        self.assertEqual(data["participant"]["reference"], "P-A")
        self.assertEqual(len(data["consents"]), 1)
        self.assertNotIn("P-B", str(data))

    def test_roles_without_the_right_cannot_record_or_export(self):
        auditor = self._user("auditor", UserRole.AUDITOR)
        self.as_user(auditor)
        self.assertEqual(self.grant(self.alice).status_code, 403)
        self.assertEqual(self.client.get(BASE + "my-data/").status_code, 403)
        self.assertEqual(self.client.get(BASE).status_code, 200)  # read-only audit view
