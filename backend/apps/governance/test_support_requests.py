from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

from .models import SupportRequest, SupportRequestStatus


class SupportRequestApiTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Support Tenant", code="SUPPORT-1", data_residency="PK")
        self.other_tenant = Tenant.objects.create(name="Other Tenant", code="SUPPORT-2", data_residency="PK")
        set_current_tenant(self.tenant)

        self.finance_maker = User.objects.create_user(
            email="fm@example.com", password="password", full_name="Finance Maker",
            role=UserRole.FINANCE_MAKER, tenant=self.tenant,
        )
        self.risk_compliance = User.objects.create_user(
            email="risk@example.com", password="password", full_name="Risk User",
            role=UserRole.RISK_COMPLIANCE, tenant=self.tenant,
        )
        self.pool_manager = User.objects.create_user(
            email="pm@example.com", password="password", full_name="Pool Manager",
            role=UserRole.POOL_MANAGER, tenant=self.tenant,
        )
        self.other_finance_maker = User.objects.create_user(
            email="fm2@example.com", password="password", full_name="Other Finance Maker",
            role=UserRole.FINANCE_MAKER, tenant=self.tenant,
        )

        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def tearDown(self):
        set_current_tenant(None)

    def _create_request(self, user):
        self.client.force_authenticate(user=user)
        return self.client.post(
            reverse("support-request-list"),
            {
                "request_type": "payout_inquiry",
                "subject": "Missing payout",
                "description": "Member says payout never arrived.",
                "raised_by_name": "Jane Doe",
            },
        )

    def test_any_authenticated_user_can_create(self):
        response = self._create_request(self.finance_maker)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "open")

    def test_risk_compliance_can_assign(self):
        create_response = self._create_request(self.finance_maker)
        request_id = create_response.data["id"]

        self.client.force_authenticate(user=self.risk_compliance)
        response = self.client.post(
            reverse("support-request-assign", args=[request_id]),
            {"assigned_to_user_id": self.finance_maker.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["assigned_to"], self.finance_maker.id)
        self.assertEqual(response.data["status"], "in_progress")

    def test_non_risk_pool_manager_cannot_assign(self):
        create_response = self._create_request(self.finance_maker)
        request_id = create_response.data["id"]

        self.client.force_authenticate(user=self.finance_maker)
        response = self.client.post(
            reverse("support-request-assign", args=[request_id]),
            {"assigned_to_user_id": self.finance_maker.id},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assignee_can_resolve(self):
        create_response = self._create_request(self.finance_maker)
        request_id = create_response.data["id"]

        self.client.force_authenticate(user=self.risk_compliance)
        self.client.post(
            reverse("support-request-assign", args=[request_id]),
            {"assigned_to_user_id": self.finance_maker.id},
        )

        self.client.force_authenticate(user=self.finance_maker)
        response = self.client.post(
            reverse("support-request-resolve", args=[request_id]),
            {"resolution_notes": "Payout was reissued."},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "resolved")
        self.assertEqual(response.data["resolved_by"], self.finance_maker.id)

    def test_risk_compliance_can_resolve_without_being_assignee(self):
        create_response = self._create_request(self.finance_maker)
        request_id = create_response.data["id"]

        self.client.force_authenticate(user=self.risk_compliance)
        self.client.post(
            reverse("support-request-assign", args=[request_id]),
            {"assigned_to_user_id": self.finance_maker.id},
        )
        response = self.client.post(
            reverse("support-request-resolve", args=[request_id]),
            {"resolution_notes": "Resolved by risk compliance directly."},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "resolved")

    def test_wrong_user_cannot_resolve(self):
        create_response = self._create_request(self.finance_maker)
        request_id = create_response.data["id"]

        self.client.force_authenticate(user=self.risk_compliance)
        self.client.post(
            reverse("support-request-assign", args=[request_id]),
            {"assigned_to_user_id": self.finance_maker.id},
        )

        self.client.force_authenticate(user=self.other_finance_maker)
        response = self.client.post(
            reverse("support-request-resolve", args=[request_id]),
            {"resolution_notes": "I'll resolve this too."},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_resolve_requires_resolution_notes(self):
        create_response = self._create_request(self.risk_compliance)
        request_id = create_response.data["id"]

        response = self.client.post(reverse("support-request-resolve", args=[request_id]), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_by_status_and_priority(self):
        self._create_request(self.finance_maker)
        response = self.client.get(reverse("support-request-list"), {"status": "open", "priority": "medium"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_tenant_isolation(self):
        self._create_request(self.finance_maker)

        set_current_tenant(self.other_tenant)
        other_user = User.objects.create_user(
            email="other@example.com", password="password", full_name="Other Tenant User",
            role=UserRole.FINANCE_MAKER, tenant=self.other_tenant,
        )
        set_current_tenant(self.tenant)

        self.client.force_authenticate(user=other_user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.other_tenant.code
        response = self.client.get(reverse("support-request-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
