"""The Shariah Policy Copilot, in-process: library approval, tenant isolation, grounded answers, fallback and review."""

import json
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, UserRole
from apps.ai_agents.models import AIModelRegistry
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

from .. import agent
from ..models import CopilotDocument, EvidencePack

BASE = "/api/v1/ai/shariah-copilot/"
LATE_FEE = (
    "Clause 4.1 Late payment. The bank shall not charge any late payment fee or penalty to the customer. "
    "Any amount received from a delayed payment is non-permissible income and shall be given to charity.\n"
    "Clause 4.2 Hardship. A customer in genuine hardship may be given more time without any charge."
)
URDU = "تاخیر سے ادائیگی پر جرمانہ لینا جائز نہیں ہے۔ ایسی رقم صدقہ کی جائے گی۔"


@override_settings(COPILOT_EMBEDDING_BACKEND="hash", COPILOT_MIN_SEMANTIC_SCORE=0.2)
class CopilotTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Cop", code="COP-T", data_residency="PK")
        self.other = Tenant.objects.create(name="Other", code="COP-O", data_residency="PK")
        set_current_tenant(self.tenant)
        mk = lambda n, r, t=None: User.objects.create_user(email=f"{n}@cop.test", password="p", full_name=n, role=r, tenant=t or self.tenant)
        self.secretariat = mk("sec", UserRole.SHARIAH_SECRETARIAT)
        self.board = mk("board", UserRole.SHARIAH_BOARD)
        self.board2 = mk("board2", UserRole.SHARIAH_BOARD)
        self.pm = mk("pm", UserRole.PRODUCT_MANAGER)
        self.investor = mk("inv", UserRole.INVESTOR_MEMBER)
        self.outsider = mk("out", UserRole.SHARIAH_BOARD, self.other)
        for name in ("shariah_copilot",):
            AIModelRegistry.objects.get_or_create(model_name=name, defaults={"version": "1", "status": "active"})

    def tearDown(self):
        set_current_tenant(None)

    def api(self, user):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}", HTTP_X_TENANT_CODE=user.tenant.code)
        return c

    def call(self, user, method, path, body=None, **kw):
        r = getattr(self.api(user), method)(BASE + path, body, **kw)
        set_current_tenant(user.tenant if user.tenant == self.tenant else self.tenant)
        return r

    def upload(self, user, text=LATE_FEE, name="Late payment policy", status="under_review", **extra):
        f = SimpleUploadedFile("policy.txt", text.encode("utf-8"), content_type="text/plain")
        return self.call(user, "post", "documents/upload/", {"file": f, "document_name": name, "document_type": "policy",
                                                           "approval_status": status, **extra}, format="multipart")

    def approved_document(self, **kw):
        doc = self.upload(self.secretariat, **kw).data
        self.assertEqual(self.call(self.board, "post", f"documents/{doc['id']}/approve/", {}, format="json").status_code, 200)
        return doc["id"]

    # --- the library: who may make a source authoritative -----------------------------------------------------------
    def test_a_document_cannot_be_uploaded_as_approved_and_the_uploader_cannot_approve_it(self):
        self.assertEqual(self.upload(self.secretariat, status="approved").status_code, 400)
        self.assertEqual(self.upload(self.pm).status_code, 403)
        doc = self.upload(self.secretariat).data
        self.assertEqual(doc["approval_status"], "under_review")
        self.assertEqual(self.call(self.secretariat, "post", f"documents/{doc['id']}/approve/", {}, format="json").status_code, 403)
        board_upload = self.upload(self.board, name="Board upload").data
        refused = self.call(self.board, "post", f"documents/{board_upload['id']}/approve/", {}, format="json")
        self.assertEqual(refused.status_code, 400, "four eyes: the uploading Board member cannot approve it")
        self.assertEqual(self.call(self.board2, "post", f"documents/{board_upload['id']}/approve/", {}, format="json").data["approval_status"], "approved")

    def test_an_unapproved_document_is_never_used_to_answer(self):
        self.upload(self.secretariat)  # under review only
        with mock.patch("apps.shariah_copilot.llm.generate") as gen:
            result = self.call(self.pm, "post", "ask/", {"question": "Is a late payment fee allowed?"}, format="json").data
        gen.assert_not_called()
        self.assertTrue(result["is_fallback"])
        self.assertEqual(result["research_summary"], agent.NO_EVIDENCE_FALLBACK)

    # --- answers -----------------------------------------------------------------------------------------------------
    def llm_answer(self, doc_id, extra_excerpt=True):
        excerpts = [{"document_id": doc_id, "document_name": "Late payment policy", "excerpt": "no late payment fee"}]
        if extra_excerpt:  # an invented source: cites a document that was never retrieved
            excerpts.append({"document_id": "00000000-0000-0000-0000-000000000000", "document_name": "Invented", "excerpt": "x"})
        return json.dumps({"research_summary": "Per [Late payment policy v1.0, Clause 4.1] no late fee may be charged.",
                           "relevant_rulings": [], "relevant_standards": ["Late payment policy"], "key_evidence_excerpts": excerpts,
                           "comparison_table": [], "open_issues": [], "conflict_flagged": False})

    def test_an_answer_is_cited_to_retrieved_documents_only_and_waits_for_a_reviewer(self):
        doc_id = self.approved_document()
        with mock.patch("apps.shariah_copilot.llm.generate", return_value=self.llm_answer(doc_id)) as gen:
            result = self.call(self.pm, "post", "ask/", {"question": "Is a late payment fee allowed?"}, format="json").data
        self.assertFalse(result["is_fallback"])
        self.assertEqual(result["review_status"], "human_review_required")
        self.assertEqual([c["document_id"] for c in result["citations"]], [doc_id])
        self.assertEqual(len(result["key_evidence_excerpts"]), 1, "the invented source was dropped")
        self.assertTrue(result["recommendation_id"], "recorded for BR-009")
        prompt = gen.call_args.args[1]
        self.assertIn("<question>", prompt)
        self.assertIn("Clause 4.1", prompt)
        review = self.call(self.board, "post", f"review/{result['id']}/", {"approve": True}, format="json")
        self.assertEqual(review.data["review_status"], "approved")
        self.assertEqual(self.call(self.pm, "post", f"review/{result['id']}/", {"approve": True}, format="json").status_code, 403)

    def test_a_question_the_evidence_does_not_address_takes_the_fixed_fallback(self):
        self.approved_document()
        with mock.patch("apps.shariah_copilot.llm.generate") as gen:
            result = self.call(self.pm, "post", "ask/", {"question": "capital of Atlantis football results"}, format="json").data
        gen.assert_not_called()  # nothing retrieved, so the model is not even asked
        self.assertTrue(result["is_fallback"])

    def test_a_model_that_says_no_evidence_or_returns_junk_takes_the_fallback(self):
        self.approved_document()
        for reply in ('{"research_summary": "NO_EVIDENCE_FOUND"}', "I cannot comply, here is a story", ""):
            with mock.patch("apps.shariah_copilot.llm.generate", return_value=reply):
                result = self.call(self.pm, "post", "ask/", {"question": "late payment fee?"}, format="json").data
            self.assertTrue(result["is_fallback"], reply)

    def test_a_reply_cut_off_mid_json_is_retried_once_before_giving_up(self):
        doc_id = self.approved_document()
        good = self.llm_answer(doc_id, extra_excerpt=False)
        with mock.patch("apps.shariah_copilot.llm.generate", side_effect=['{"research_summary": "Per [Late', good]) as gen:
            result = self.call(self.pm, "post", "ask/", {"question": "late payment fee?"}, format="json").data
        self.assertFalse(result["is_fallback"])
        self.assertEqual(gen.call_count, 2)

    def test_an_urdu_question_finds_urdu_text_and_the_search_cannot_be_widened(self):
        doc_id = self.approved_document(text=URDU, name="اردو پالیسی")
        with mock.patch("apps.shariah_copilot.llm.generate", return_value=self.llm_answer(doc_id, extra_excerpt=False)):
            result = self.call(self.pm, "post", "ask/", {"question": "تاخیر سے ادائیگی پر جرمانہ", "filters": {"approved_only": False}}, format="json").data
        self.assertFalse(result["is_fallback"])
        draft = self.upload(self.secretariat, text=LATE_FEE, name="Draft only", status="draft").data
        with mock.patch("apps.shariah_copilot.llm.generate") as gen:
            self.call(self.pm, "post", "ask/", {"question": "any late payment fee penalty charity", "filters": {"approved_only": False}}, format="json")
        sent = gen.call_args.args[1] if gen.called else ""
        self.assertNotIn(draft["id"], sent, "a caller cannot switch off the approved-only scope")

    # --- isolation and kill switch -----------------------------------------------------------------------------------
    def test_another_tenants_library_is_invisible(self):
        self.approved_document()
        listing = self.call(self.outsider, "get", "documents/").data
        self.assertEqual(listing, [])
        with mock.patch("apps.shariah_copilot.llm.generate") as gen:
            result = self.call(self.outsider, "post", "ask/", {"question": "late payment fee"}, format="json").data
        gen.assert_not_called()
        self.assertTrue(result["is_fallback"])
        self.assertEqual(CopilotDocument._base_manager.filter(tenant=self.other).count(), 0)

    def test_an_investor_cannot_use_the_copilot_and_a_disabled_model_answers_503(self):
        self.assertEqual(self.call(self.investor, "post", "ask/", {"question": "x"}, format="json").status_code, 403)
        AIModelRegistry.objects.filter(model_name="shariah_copilot").update(status="disabled")
        self.assertEqual(self.call(self.pm, "post", "ask/", {"question": "late fee"}, format="json").status_code, 503)

    def test_with_semantic_search_off_the_answer_says_it_used_keywords_only(self):
        doc_id = self.approved_document()
        with override_settings(COPILOT_EMBEDDING_BACKEND="none"):
            with mock.patch("apps.shariah_copilot.llm.generate", return_value=self.llm_answer(doc_id, extra_excerpt=False)):
                result = self.call(self.pm, "post", "ask/", {"question": "late payment fee penalty"}, format="json").data
        self.assertEqual(result["retrieval_mode"], "keyword_only")
        self.assertEqual(EvidencePack._base_manager.filter(tenant=self.tenant).count(), 1)

    def test_a_model_that_cannot_be_reached_is_a_503_not_an_invented_answer(self):
        from ..llm import LLMUnavailable

        self.approved_document()
        with mock.patch("apps.shariah_copilot.llm.generate", side_effect=LLMUnavailable("down")):
            r = self.call(self.pm, "post", "ask/", {"question": "late payment fee"}, format="json")
        self.assertEqual(r.status_code, 503)
