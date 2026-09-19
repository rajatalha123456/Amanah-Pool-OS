from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

from .models import ContractTemplate


class ShariahDecisionApiTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Shariah Governance Test Tenant", code="SG-TEST", data_residency="PK"
        )
        set_current_tenant(self.tenant)
        self.board = User.objects.create_user(
            email="board@example.com",
            password="password",
            full_name="Shariah Board",
            role=UserRole.SHARIAH_BOARD,
            tenant=self.tenant,
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="password",
            full_name="Pool Manager",
            role=UserRole.POOL_MANAGER,
            tenant=self.tenant,
        )
        self.list_url = reverse("shariah-decision-list")

    def tearDown(self):
        set_current_tenant(None)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def decision_payload(self):
        return {
            "decision_code": "FTW-2026-001",
            "title": "Test Decision",
            "description": "A test Shariah decision.",
            "effective_date": "2026-09-19",
        }

    def test_create_list_and_approve_decision(self):
        self.authenticate(self.board)
        create_response = self.client.post(self.list_url, self.decision_payload(), format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data["status"], "draft")

        list_response = self.client.get(self.list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        detail_url = reverse("shariah-decision-detail", args=[create_response.data["id"]])
        approve_response = self.client.post(f"{detail_url}approve/")
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data["status"], "approved")

    def test_wrong_role_cannot_create_decision(self):
        self.authenticate(self.other_user)
        response = self.client.post(self.list_url, self.decision_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_shariah_dashboard_reflects_pending_decision(self):
        self.authenticate(self.board)
        self.client.post(self.list_url, self.decision_payload(), format="json")

        dashboard_response = self.client.get(reverse("shariah-dashboard"))
        self.assertEqual(dashboard_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(dashboard_response.data["pending_shariah_decisions"]), 1)
        self.assertGreaterEqual(dashboard_response.data["summary_counts"]["total_pending_items"], 1)


class ContractTemplateClausesSchemaApiTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Contract Template Test Tenant", code="CT-TEST", data_residency="PK"
        )
        set_current_tenant(self.tenant)
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="password",
            full_name="Product Manager",
            role=UserRole.PRODUCT_MANAGER,
            tenant=self.tenant,
        )
        self.template = ContractTemplate.objects.create(
            tenant=self.tenant,
            name="Test Contract",
            contract_type="mudarabah_unrestricted",
            version="1.0",
            clauses={},
        )

    def tearDown(self):
        set_current_tenant(None)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def test_clauses_schema_returns_standard_clause_fields(self):
        self.authenticate(self.manager)
        detail_url = reverse("contract-template-detail", args=[self.template.id])
        response = self.client.get(f"{detail_url}clauses-schema/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        keys = {item["key"] for item in response.data}
        self.assertIn("profit_ratio", keys)
        self.assertIn("late_payment_policy", keys)
        self.assertIn("notice_period", keys)

    def test_clauses_schema_404_for_unknown_template(self):
        self.authenticate(self.manager)
        response = self.client.get(
            "/api/v1/products/contract-templates/00000000-0000-0000-0000-000000000000/clauses-schema/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_template_with_dynamic_clauses_and_shariah_decision(self):
        self.authenticate(self.manager)

        create_response = self.client.post(
            reverse("contract-template-list"),
            {
                "name": "New Mudarabah Contract",
                "contract_type": "mudarabah_unrestricted",
                "version": "2.0",
                "clauses": {"profit_ratio": "70/30", "notice_period": "30 days"},
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data["clauses"], {"profit_ratio": "70/30", "notice_period": "30 days"})
        self.assertEqual(create_response.data["status"], "draft")

        list_response = self.client.get(reverse("contract-template-list"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 2)
