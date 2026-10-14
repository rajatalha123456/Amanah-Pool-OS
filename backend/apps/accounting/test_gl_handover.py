"""GL hand-over (BRD 10 / 12): stored file, no batch sent twice, the GL's answer recorded by a different person, trial balance."""

import hashlib
from decimal import Decimal
from io import StringIO

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management import call_command
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

from .models import GLExport, JournalBatch

BASE = "/api/v1/accounting/gl-exports/"


class GLHandoverTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_project_data", tenant_code="GL-T", allow_non_debug=True, stdout=StringIO())
        cls.tenant = Tenant.objects.get(code="GL-T")
        cls.pool = JournalBatch._base_manager.filter(tenant=cls.tenant).first().pool

    def setUp(self):
        set_current_tenant(self.tenant)

    def tearDown(self):
        set_current_tenant(None)

    def user(self, role):
        return User.objects.filter(tenant=self.tenant, role=role).order_by("email").first()

    def call(self, user, method, url, body=None):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        response = getattr(self.client, method)(url, body, format="json", HTTP_X_TENANT_CODE="GL-T")
        set_current_tenant(self.tenant)
        return response

    def export(self):
        return self.call(self.user("finance_maker"), "post", BASE, {"pool": str(self.pool.id)})

    def test_a_batch_is_never_sent_twice_and_the_file_is_stored_with_its_hash(self):
        posted = JournalBatch._base_manager.filter(pool=self.pool, status="posted").count()
        first = self.export()
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["batch_count"], posted)
        self.assertEqual(first.data["status"], "generated")

        again = self.export()
        self.assertEqual(again.status_code, 400)
        self.assertIn("already sent", str(again.data))

        download = self.call(self.user("auditor"), "get", f"{BASE}{first.data['id']}/download/")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(hashlib.sha256(download.content).hexdigest(), first.data["content_hash"])

        pending = self.call(self.user("finance_checker"), "get", f"{BASE}pending-batches/?pool={self.pool.id}")
        self.assertEqual(pending.data["pending_batches"], 0)

    def test_the_gl_answer_is_recorded_by_a_different_finance_checker(self):
        export_id = self.export().data["id"]
        url = f"{BASE}{export_id}/"
        self.assertEqual(self.call(self.user("finance_maker"), "post", url + "confirm/", {"gl_reference": "GL-1"}).status_code, 403)
        self.assertEqual(self.call(self.user("finance_checker"), "post", url + "confirm/", {}).status_code, 400)
        done = self.call(self.user("finance_checker"), "post", url + "confirm/", {"gl_reference": "ERP-JV-2026-0912"})
        self.assertEqual(done.status_code, 200, done.data)
        self.assertEqual(done.data["status"], "confirmed")
        self.assertEqual(done.data["gl_reference"], "ERP-JV-2026-0912")
        self.assertEqual(self.call(self.user("finance_checker"), "post", url + "reject/", {"reason": "late"}).status_code, 400)

    def test_a_rejected_export_frees_its_batches_for_a_new_one(self):
        export_id = self.export().data["id"]
        self.assertEqual(self.call(self.user("finance_checker"), "post", f"{BASE}{export_id}/reject/", {}).status_code, 400)
        rejected = self.call(self.user("finance_checker"), "post", f"{BASE}{export_id}/reject/", {"reason": "Unknown GL code 4101-020"})
        self.assertEqual(rejected.data["status"], "rejected")
        second = self.export()
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(second.data["batch_count"], rejected.data["batch_count"])

    def test_the_file_is_immutable_and_cannot_be_deleted(self):
        export = GLExport._base_manager.get(pk=self.export().data["id"])
        export.content = "tampered"
        with self.assertRaises(DjangoValidationError):
            export.save()
        with self.assertRaises(DjangoValidationError):
            export.delete()

    def test_the_trial_balance_balances_and_matches_the_journals(self):
        tb = self.call(self.user("auditor"), "get", f"/api/v1/accounting/trial-balance/?pool={self.pool.id}").data
        self.assertTrue(tb["balanced"])
        expected = sum(
            (b.total_debit for b in JournalBatch._base_manager.filter(pool=self.pool, status="posted")), Decimal("0")
        )
        self.assertEqual(Decimal(tb["total_debit"]), expected)
        self.assertEqual(Decimal(tb["total_credit"]), expected)

    def test_investors_and_the_platform_admin_cannot_reach_the_gl(self):
        for role in ("investor_member", "platform_super_admin"):
            self.assertEqual(self.call(self.user(role), "get", BASE).status_code, 403, role)
