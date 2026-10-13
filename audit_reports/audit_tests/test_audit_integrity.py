"""
Audit (Phase 7 / 11): immutability of posted records through every interface, including the Django admin.
Runs on the throw-away test database with the seeded synthetic tenant.
"""

from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import User
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence"


class AdminBypassTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_project_data", tenant_code="AUD-I", allow_non_debug=True, stdout=StringIO())
        cls.tenant = Tenant.objects.get(code="AUD-I")

    def tearDown(self):
        set_current_tenant(None)

    def admin_user(self):
        """The seeded platform super admin, if it can sign in to /admin/; otherwise a Django superuser."""
        u = User.objects.filter(tenant=self.tenant, role="platform_super_admin").first()
        return u

    def test_signed_run_cannot_be_hard_deleted_through_django_admin(self):
        from apps.allocation.models import AllocationLine, AllocationRun, AllocationRunStatus

        signed = AllocationRun._base_manager.filter(tenant=self.tenant, status=AllocationRunStatus.SIGNED).first()
        self.assertIsNotNone(signed, "seed has no signed run")
        lines_before = AllocationLine._base_manager.filter(allocation_run=signed).count()
        admin = self.admin_user()
        note = [f"seeded super admin is_staff={admin.is_staff} is_superuser={admin.is_superuser}"]
        if not admin.is_staff:
            admin = User.objects.create_superuser(email="root@audit.test", password="Synthetic-Pass-1", tenant=self.tenant)
            note.append("used a Django superuser (created for the test) because the seeded admin is not staff")
        self.client.force_login(admin)
        r = self.client.post("/admin/allocation/allocationrun/", {
            "action": "delete_selected", "_selected_action": [str(signed.pk)], "post": "yes",
        })
        exists = AllocationRun._base_manager.filter(pk=signed.pk).exists()
        lines_after = AllocationLine._base_manager.filter(allocation_run_id=signed.pk).count()
        note.append(f"POST delete_selected -> {r.status_code}; run still exists: {exists}; lines {lines_before} -> {lines_after}")
        with open(EVIDENCE / "admin_bulk_delete.txt", "w", encoding="utf-8") as fh:
            fh.write("\n".join(note))
        self.assertTrue(exists, "\n".join(note))

    def test_reserve_policy_change_needs_an_independent_approval(self):
        """BRD 5 (Reserves: approval, release, disclosure) and BR-003: one person must not change reserve economics."""
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        from apps.allocation.models import ReservePolicy

        policy = ReservePolicy._base_manager.filter(tenant=self.tenant).first()
        self.assertIsNotNone(policy, "seed has no reserve policy")
        before = (policy.rate_percentage, policy.cap_percentage, policy.current_balance)
        pm = User.objects.filter(tenant=self.tenant, role="pool_manager").first()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(pm).access_token}")
        r = client.patch(f"/api/v1/allocation/reserve-policies/{policy.pk}/",
                         {"rate_percentage": "4.00", "current_balance": "1.00"}, format="json", HTTP_X_TENANT_CODE="AUD-I")
        set_current_tenant(None)
        policy.refresh_from_db()
        after = (policy.rate_percentage, policy.cap_percentage, policy.current_balance)
        with open(EVIDENCE / "reserve_policy_change.txt", "w", encoding="utf-8") as fh:
            fh.write(f"pool_manager PATCH rate 4.00, current_balance 1.00 -> HTTP {r.status_code}; before {before}; after {after}")
        self.assertEqual(before, after, f"reserve policy changed immediately by one person: {before} -> {after}")

    def test_approved_psr_cannot_be_edited_through_django_admin(self):
        from apps.allocation.models import PSRStatus, ProfitSharingRatio

        psr = ProfitSharingRatio._base_manager.filter(tenant=self.tenant, status=PSRStatus.APPROVED).first()
        admin = self.admin_user()
        if not admin.is_staff:
            admin = User.objects.create_superuser(email="root2@audit.test", password="Synthetic-Pass-1", tenant=self.tenant)
        self.client.force_login(admin)
        page = self.client.get(f"/admin/allocation/profitsharingratio/{psr.pk}/change/")
        editable = page.status_code == 200 and b'name="depositor_share"' in page.content and b"readonly" not in page.content[:0]
        with open(EVIDENCE / "admin_psr_edit.txt", "w", encoding="utf-8") as fh:
            fh.write(f"GET change form -> {page.status_code}; depositor_share input rendered: {editable}")
        self.assertFalse(editable, "an approved PSR is editable in the Django admin")
