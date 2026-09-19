from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

from .models import AIModelRegistry, AIModelStatus


class AIModelRegistryApiTests(APITestCase):
	def setUp(self):
		self.tenant = Tenant.objects.create(
			name="AI Test Tenant", code="AI-TEST", data_residency="PK"
		)
		set_current_tenant(self.tenant)
		self.admin = User.objects.create_user(
			email="admin@example.com",
			password="password",
			full_name="Platform Admin",
			role=UserRole.PLATFORM_SUPER_ADMIN,
			tenant=self.tenant,
		)
		self.user = User.objects.create_user(
			email="user@example.com",
			password="password",
			full_name="Regular User",
			role=UserRole.RISK_COMPLIANCE,
			tenant=self.tenant,
		)
		self.shariah_user = User.objects.create_user(
			email="shariah@example.com",
			password="password",
			full_name="Shariah Reviewer",
			role=UserRole.SHARIAH_BOARD,
			tenant=self.tenant,
		)
		self.registry = AIModelRegistry.objects.get(model_name="shariah_copilot")
		self.url = reverse("ai-model-detail", args=[self.registry.id])

	def tearDown(self):
		set_current_tenant(None)

	def authenticate(self, user):
		self.client.force_authenticate(user=user)
		self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

	def test_authenticated_user_can_list_models(self):
		self.authenticate(self.user)
		response = self.client.get(reverse("ai-model-list"))
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("shariah_copilot", {item["model_name"] for item in response.data})

	def test_only_platform_super_admin_can_toggle_model(self):
		self.authenticate(self.user)
		forbidden = self.client.patch(self.url, {"status": "disabled"}, format="json")
		self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

		self.authenticate(self.admin)
		disabled = self.client.patch(
			self.url,
			{"status": "disabled", "disabled_reason": "Maintenance"},
			format="json",
		)
		self.assertEqual(disabled.status_code, status.HTTP_200_OK)
		self.registry.refresh_from_db()
		self.assertEqual(self.registry.status, AIModelStatus.DISABLED)
		self.assertEqual(self.registry.disabled_by_id, self.admin.id)

	@patch("apps.ai_agents.views.copilot.ask_question", return_value={"id": "pack-1"})
	def test_shariah_copilot_is_blocked_then_reenabled(self, ask_question):
		self.authenticate(self.admin)
		self.client.patch(self.url, {"status": "disabled"}, format="json")

		self.authenticate(self.shariah_user)
		blocked = self.client.post(
			reverse("shariah-copilot-ask"), {"question": "What is the policy?"}, format="json"
		)
		self.assertEqual(blocked.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
		self.assertIn("currently disabled", blocked.data["error"]["message"])
		ask_question.assert_not_called()

		self.authenticate(self.admin)
		self.client.patch(self.url, {"status": "active"}, format="json")
		self.authenticate(self.shariah_user)
		enabled = self.client.post(
			reverse("shariah-copilot-ask"), {"question": "What is the policy?"}, format="json"
		)
		self.assertEqual(enabled.status_code, status.HTTP_200_OK)
		ask_question.assert_called_once()
