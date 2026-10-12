from unittest.mock import patch

from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

from .models import AIModelRegistry, AIModelStatus, AIRecommendation

BASE = "/api/v1/ai/"
CONTRACT = "Murabahah sale with deferred payment. The bank may charge a late payment penalty to its own income."


class RecommendationRecordTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="AIR", code="AIR-T", data_residency="PK")
        set_current_tenant(self.tenant)
        original = self.client.request

        def keep(**kwargs):
            try:
                return original(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = keep
        self.board = self._user("board", UserRole.SHARIAH_BOARD)
        self.secretariat = self._user("sec", UserRole.SHARIAH_SECRETARIAT)
        self.investor = self._user("inv", UserRole.INVESTOR_MEMBER)

    def tearDown(self):
        set_current_tenant(None)

    def _user(self, name, role):
        return User.objects.create_user(
            email=f"{name}@air.example.com", password="password", full_name=name.title(), role=role, tenant=self.tenant
        )

    def call(self, user, method, path, body=None):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code
        return getattr(self.client, method)(f"{BASE}{path}", body, format="json")

    def analyse(self):
        with patch("apps.ai_agents.services.contract_analyzer.requests", create=True):
            return self.call(self.board, "post", "contract-analyzer/analyze/", {"contract_text": CONTRACT})

    def test_every_ai_output_is_recorded_with_prompt_source_confidence_and_pending_disposition(self):
        response = self.analyse()
        self.assertEqual(response.status_code, 200, response.data)
        rec = AIRecommendation._base_manager.get(pk=response.data["recommendation_id"])
        self.assertEqual((rec.feature, rec.disposition, rec.requested_by_id), ("contract_analyzer", "pending", self.board.id))
        self.assertEqual(len(rec.prompt_hash), 64)
        self.assertIn("Murabahah", rec.prompt_text)
        self.assertTrue(rec.sources)
        self.assertIsNotNone(rec.confidence)
        self.assertTrue(rec.requires_human_review)

    def test_human_disposition_is_required_once_and_a_reason_for_rejection(self):
        rec_id = self.analyse().data["recommendation_id"]
        url = f"recommendations/{rec_id}/dispose/"
        self.assertEqual(self.call(self.board, "post", url, {"disposition": "rejected"}).status_code, 400)
        self.assertEqual(self.call(self.board, "post", url, {"disposition": "maybe"}).status_code, 400)
        ok = self.call(self.board, "post", url, {"disposition": "rejected", "note": "Clause misread"})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual((ok.data["disposition"], ok.data["disposed_by_name"]), ("rejected", "Board"))
        self.assertEqual(self.call(self.secretariat, "post", url, {"disposition": "accepted"}).status_code, 400)

    def test_the_ai_output_itself_cannot_be_edited_after_recording(self):
        rec = AIRecommendation._base_manager.get(pk=self.analyse().data["recommendation_id"])
        rec.reason = "changed"
        with self.assertRaises(Exception):
            rec.save()

    def test_investors_cannot_read_or_dispose_recommendations(self):
        rec_id = self.analyse().data["recommendation_id"]
        self.assertEqual(self.call(self.investor, "get", "recommendations/").status_code, 403)
        self.assertEqual(self.call(self.investor, "post", f"recommendations/{rec_id}/dispose/", {"disposition": "accepted"}).status_code, 403)

    def test_metrics_report_acceptance_and_override_rates(self):
        ids = [self.analyse().data["recommendation_id"] for _ in range(3)]
        self.call(self.board, "post", f"recommendations/{ids[0]}/dispose/", {"disposition": "accepted"})
        self.call(self.board, "post", f"recommendations/{ids[1]}/dispose/", {"disposition": "overridden", "note": "Different view"})
        row = self.call(self.board, "get", "recommendations/metrics/").data[0]
        self.assertEqual((row["total"], row["pending"], row["decided"]), (3, 1, 2))
        self.assertEqual((row["acceptance_rate"], row["override_rate"]), (0.5, 0.5))
        self.assertEqual(row["fallback_rate"], 1.0)

    def test_an_explicit_kill_switch_blocks_a_registry_less_feature(self):
        AIModelRegistry.objects.create(model_name="contract_analyzer", version="1", status=AIModelStatus.DISABLED)
        self.assertEqual(self.analyse().status_code, 503)

    def test_copilot_answers_are_recorded_with_their_citations(self):
        AIModelRegistry.objects.update_or_create(model_name="shariah_copilot", defaults={"version": "1", "status": AIModelStatus.ACTIVE})
        answer = {"answer": "Permitted.", "citations": [{"document": "Fatwa 12"}], "confidence": 0.91}
        with patch("apps.ai_agents.services.shariah_copilot_client.ask_question", return_value=answer):
            response = self.call(self.board, "post", "shariah-copilot/ask/", {"question": "Is X permitted?"})
        rec = AIRecommendation._base_manager.get(pk=response.data["recommendation_id"])
        self.assertEqual((rec.feature, str(rec.confidence)), ("shariah_copilot_ask", "0.910"))
        self.assertEqual(rec.sources, [{"document": "Fatwa 12"}])
