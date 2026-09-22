from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.audit import log_action
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

from .models import AuditLog


class AuditLogApiTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Audit Tenant", code="AUDIT-1", data_residency="PK")
        self.other_tenant = Tenant.objects.create(name="Other Tenant", code="AUDIT-2", data_residency="PK")
        set_current_tenant(self.tenant)

        self.auditor = User.objects.create_user(
            email="auditor@example.com", password="password", full_name="Auditor User",
            role=UserRole.AUDITOR, tenant=self.tenant,
        )
        self.pool_manager = User.objects.create_user(
            email="pm@example.com", password="password", full_name="Pool Manager",
            role=UserRole.POOL_MANAGER, tenant=self.tenant,
        )
        self.super_admin = User.objects.create_user(
            email="super@example.com", password="password", full_name="Super Admin",
            role=UserRole.PLATFORM_SUPER_ADMIN, tenant=None,
        )

        log_action(
            tenant=self.tenant, actor=self.pool_manager, action="create",
            model_name="Pool", object_id="pool-1", changes={"name": "Pool A"},
        )
        log_action(
            tenant=self.tenant, actor=self.pool_manager, action="create",
            model_name="CircleMember", object_id="member-1", changes={"member_reference": "MEM-1"},
        )
        log_action(
            tenant=self.other_tenant, actor=None, action="create",
            model_name="Pool", object_id="pool-2", changes={"name": "Other Pool"},
        )

        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def tearDown(self):
        set_current_tenant(None)

    def test_auditor_can_list_audit_log(self):
        self.client.force_authenticate(user=self.auditor)
        response = self.client.get(reverse("audit-log-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_auditor_list_is_tenant_scoped(self):
        self.client.force_authenticate(user=self.auditor)
        response = self.client.get(reverse("audit-log-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        object_ids = {row["object_id"] for row in response.data}
        self.assertEqual(object_ids, {"pool-1", "member-1"})

    def test_non_auditor_forbidden(self):
        self.client.force_authenticate(user=self.pool_manager)
        response = self.client.get(reverse("audit-log-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_model_name(self):
        self.client.force_authenticate(user=self.auditor)
        response = self.client.get(reverse("audit-log-list"), {"model_name": "Pool"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["model_name"], "Pool")

    def test_super_admin_can_filter_by_tenant_across_tenants(self):
        self.client.force_authenticate(user=self.super_admin)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.other_tenant.code
        response = self.client.get(reverse("audit-log-list"), {"tenant": str(self.other_tenant.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["object_id"], "pool-2")

    def test_export_returns_csv(self):
        self.client.force_authenticate(user=self.auditor)
        response = self.client.get(reverse("audit-log-export"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        self.assertIn("pool-1", content)
        self.assertIn("member-1", content)
        self.assertIn("pm@example.com", content)
        self.assertNotIn("pool-2", content)

    def test_export_filtered_by_model_name(self):
        self.client.force_authenticate(user=self.auditor)
        response = self.client.get(reverse("audit-log-export"), {"model_name": "CircleMember"})
        content = response.content.decode("utf-8")
        self.assertIn("member-1", content)
        self.assertNotIn("pool-1", content)

    def test_non_auditor_export_forbidden(self):
        self.client.force_authenticate(user=self.pool_manager)
        response = self.client.get(reverse("audit-log-export"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_export_does_not_create_new_audit_log_entries(self):
        self.client.force_authenticate(user=self.auditor)
        set_current_tenant(self.tenant)
        before_count = AuditLog.objects.filter(tenant=self.tenant).count()
        self.client.get(reverse("audit-log-export"))
        after_count = AuditLog.objects.filter(tenant=self.tenant).count()
        self.assertEqual(before_count, after_count)
