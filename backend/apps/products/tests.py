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
        self.secretariat = User.objects.create_user(
            email="secretariat@example.com",
            password="password",
            full_name="Shariah Secretariat",
            role=UserRole.SHARIAH_SECRETARIAT,
            tenant=self.tenant,
        )
        self.board = User.objects.create_user(
            email="board@example.com",
            password="password",
            full_name="Shariah Board Member",
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
            "title": "Retail Mudarabah Pool Fatwa Approval",
            "decision_type": "product_approval",
            "meeting_reference": "SSB-M-2026-04",
            "scholars_signatories": "Mufti Muhammad Taqi, Dr. Imran Usmani",
            "fiqh_reference": "AAOIFI Shariah Standard No. 13 (Mudarabah), SBP IBD Circular 02",
            "description": "Comprehensive fatwa approving the Retail Mudarabah product structure.",
            "mandatory_caveats": "Quarterly Shariah audit required; reserve transfers capped at 10%.",
            "fatwa_arabic_text": "الحمد لله رب العالمين، والصلاة والسلام على رسوله الكريم...",
            "effective_date": "2026-09-19",
            "expiry_date": "2027-09-19",
            "document_url": "https://docs.bank.test/fatwas/FTW-2026-001.pdf",
        }

    def test_create_list_and_approve_decision(self):
        # Secretariat creates draft
        self.authenticate(self.secretariat)
        create_response = self.client.post(self.list_url, self.decision_payload(), format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data["status"], "draft")
        self.assertEqual(create_response.data["decision_type"], "product_approval")
        self.assertEqual(create_response.data["meeting_reference"], "SSB-M-2026-04")
        self.assertEqual(create_response.data["created_by_name"], "Shariah Secretariat")
        self.assertIsNone(create_response.data["approved_by"])

        # Secretariat cannot approve (forbidden)
        detail_url = reverse("shariah-decision-detail", args=[create_response.data["id"]])
        sec_approve_resp = self.client.post(f"{detail_url}approve/")
        self.assertEqual(sec_approve_resp.status_code, status.HTTP_403_FORBIDDEN)

        # List shows the decision
        list_response = self.client.get(self.list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        # Board member approves
        self.authenticate(self.board)
        approve_response = self.client.post(f"{detail_url}approve/")
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data["status"], "approved")
        self.assertEqual(approve_response.data["approved_by_name"], "Shariah Board Member")
        self.assertIsNotNone(approve_response.data["approved_at"])

    def test_board_creator_cannot_self_approve(self):
        # Board member creates draft
        self.authenticate(self.board)
        create_response = self.client.post(self.list_url, self.decision_payload(), format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        # Same board member tries to approve -> rejected by maker-checker check
        detail_url = reverse("shariah-decision-detail", args=[create_response.data["id"]])
        approve_response = self.client.post(f"{detail_url}approve/")
        self.assertEqual(approve_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Maker and checker cannot be the same user", str(approve_response.data))

    def test_wrong_role_cannot_create_decision(self):
        self.authenticate(self.other_user)
        response = self.client.post(self.list_url, self.decision_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_decision(self):
        self.authenticate(self.secretariat)
        create_resp = self.client.post(self.list_url, self.decision_payload(), format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)

        detail_url = reverse("shariah-decision-detail", args=[create_resp.data["id"]])
        update_resp = self.client.patch(
            detail_url,
            {"title": "Updated Mudarabah Fatwa", "mandatory_caveats": "Updated caveats text."},
            format="json",
        )
        self.assertEqual(update_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(update_resp.data["title"], "Updated Mudarabah Fatwa")
        self.assertEqual(update_resp.data["mandatory_caveats"], "Updated caveats text.")

    def test_delete_decision_success(self):
        self.authenticate(self.secretariat)
        create_resp = self.client.post(self.list_url, self.decision_payload(), format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)

        detail_url = reverse("shariah-decision-detail", args=[create_resp.data["id"]])
        delete_resp = self.client.delete(detail_url)
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)

        get_resp = self.client.get(detail_url)
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_decision_blocked_if_contract_linked(self):
        self.authenticate(self.secretariat)
        create_resp = self.client.post(self.list_url, self.decision_payload(), format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)

        # Link a contract template to this decision
        ContractTemplate.objects.create(
            tenant=self.tenant,
            name="Linked Template",
            contract_type="mudarabah_unrestricted",
            version="1.0",
            clauses={},
            shariah_decision_id=create_resp.data["id"],
        )

        detail_url = reverse("shariah-decision-detail", args=[create_resp.data["id"]])
        delete_resp = self.client.delete(detail_url)
        self.assertEqual(delete_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("actively linked to one or more Contract Templates", str(delete_resp.data))

    def test_secretariat_cannot_delete_approved_decision(self):
        # Secretariat creates draft
        self.authenticate(self.secretariat)
        create_resp = self.client.post(self.list_url, self.decision_payload(), format="json")
        detail_url = reverse("shariah-decision-detail", args=[create_resp.data["id"]])

        # Board approves it
        self.authenticate(self.board)
        approve_resp = self.client.post(f"{detail_url}approve/")
        self.assertEqual(approve_resp.status_code, status.HTTP_200_OK)

        # Secretariat tries to delete approved fatwa -> 403 Forbidden
        self.authenticate(self.secretariat)
        del_resp = self.client.delete(detail_url)
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Shariah Secretariat cannot delete an approved Shariah decision", str(del_resp.data))

    def test_board_can_delete_unlinked_approved_decision(self):
        # Secretariat creates draft
        self.authenticate(self.secretariat)
        create_resp = self.client.post(self.list_url, self.decision_payload(), format="json")
        detail_url = reverse("shariah-decision-detail", args=[create_resp.data["id"]])

        # Board approves it
        self.authenticate(self.board)
        approve_resp = self.client.post(f"{detail_url}approve/")
        self.assertEqual(approve_resp.status_code, status.HTTP_200_OK)

        # Board deletes unlinked approved decision -> 204 No Content
        del_resp = self.client.delete(detail_url)
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_wrong_role_cannot_edit_or_delete(self):
        self.authenticate(self.secretariat)
        create_resp = self.client.post(self.list_url, self.decision_payload(), format="json")
        detail_url = reverse("shariah-decision-detail", args=[create_resp.data["id"]])

        self.authenticate(self.other_user)
        patch_resp = self.client.patch(detail_url, {"title": "Hacked Title"}, format="json")
        self.assertEqual(patch_resp.status_code, status.HTTP_403_FORBIDDEN)

        del_resp = self.client.delete(detail_url)
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)


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
