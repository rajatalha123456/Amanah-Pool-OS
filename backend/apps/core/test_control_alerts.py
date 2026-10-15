from datetime import date, timedelta

from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.core.control_alerts import build_alerts
from apps.tenants.models import EncryptionKeyRecord, Tenant


class ControlAlertTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="CA", code="CA-T", data_residency="PK")
        set_current_tenant(self.tenant)
        self.auditor = User.objects.create_user(email="a@ca.test", password="x", full_name="A", role=UserRole.AUDITOR, tenant=self.tenant)
        self.investor = User.objects.create_user(email="i@ca.test", password="x", full_name="I", role=UserRole.INVESTOR_MEMBER, tenant=self.tenant)

    def tearDown(self):
        set_current_tenant(None)

    def get(self, user):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}", HTTP_X_TENANT_CODE=self.tenant.code)
        r = c.get("/api/v1/core/control-alerts/")
        set_current_tenant(self.tenant)
        return r

    def test_a_quiet_tenant_has_no_alerts(self):
        self.assertEqual(build_alerts(self.tenant), [])
        self.assertEqual(self.get(self.auditor).data, {"alerts": []})

    def test_an_overdue_key_rotation_is_a_critical_alert_for_staff_only(self):
        EncryptionKeyRecord.objects.create(tenant=self.tenant, purpose="Database", provider="HSM", key_reference="k1",
                                           rotation_interval_days=30, last_rotated_on=date.today() - timedelta(days=90))
        alerts = self.get(self.auditor).data["alerts"]
        self.assertEqual([(a["code"], a["severity"], a["count"]) for a in alerts], [("key_rotation_overdue", "critical", 1)])
        self.assertEqual(self.get(self.investor).status_code, 403)
