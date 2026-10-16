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
        # BRD 9: a rejected flag is a false positive; drift needs history on both sides, so it is None here.
        self.assertEqual(row["false_positive_rate"], 0.0)
        self.assertIsNone(row["confidence_drift"])

    def test_model_inventory_is_kept_by_the_platform_administrator_only(self):
        admin = User.objects.create_user(email="root@air.example.com", password="password", full_name="Root",
                                         role=UserRole.PLATFORM_SUPER_ADMIN, tenant=self.tenant)
        reg = AIModelRegistry.objects.create(model_name="contract_analyzer", version="1")
        body = {"owner": "Head of Shariah Compliance", "purpose": "Screens contract text", "provenance": "Vendor LLM + rules",
                "validation_status": "validated", "validated_on": "2026-09-01", "validation_reference": "VAL-001",
                "retirement_date": "2027-09-01"}
        self.assertEqual(self.call(self.board, "patch", f"models/{reg.id}/", body).status_code, 403)
        done = self.call(admin, "patch", f"models/{reg.id}/", body)
        self.assertEqual(done.status_code, 200)
        self.assertEqual(done.data["owner"], "Head of Shariah Compliance")
        self.assertEqual(done.data["validation_status"], "validated")

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


class DetectorRecordingTests(APITestCase):
    """BR-009 for the allocation anomaly detector and the reconciliation copilot: each finding is recorded."""

    def test_an_anomaly_and_a_reconciliation_finding_are_recorded_with_reason_and_pending_disposition(self):
        from datetime import date, timedelta
        from decimal import Decimal
        from io import StringIO

        from django.core.management import call_command

        from apps.accounting.models import JournalBatch
        from apps.accounting.reconciliation import check_reconciliation
        from apps.accounts.models import User
        from apps.allocation.anomaly_detector import check_for_anomalies
        from apps.allocation.models import AllocationRun
        from apps.core.context import set_current_tenant
        from apps.tenants.models import Tenant

        call_command("seed_project_data", tenant_code="DET-T", allow_non_debug=True, stdout=StringIO())
        tenant = Tenant.objects.get(code="DET-T")
        set_current_tenant(tenant)
        try:
            signatory = User.objects.filter(tenant=tenant, role="authorized_signatory").first()
            template = AllocationRun._base_manager.filter(tenant=tenant, status="signed").order_by("-value_date").first()
            pool = template.pool
            # five signed runs with a steady margin of 0.9, then one whose margin is 0.09
            for i in range(5):
                AllocationRun._base_manager.create(
                    tenant=tenant, pool=pool, value_date=date(2025, 1, 1) + timedelta(days=i), gross_income=Decimal("100.00"),
                    distributable_amount=Decimal("90.00"), total_weighted_funds=Decimal("90.00"),
                    depositor_pool_share=Decimal("90.00"), mudarib_share=Decimal("0.00"), status="signed",
                )
            latest = AllocationRun._base_manager.create(
                tenant=tenant, pool=pool, value_date=date(2025, 2, 1), gross_income=Decimal("1000.00"),
                distributable_amount=Decimal("90.00"), total_weighted_funds=Decimal("90.00"),
                depositor_pool_share=Decimal("90.00"), mudarib_share=Decimal("0.00"), status="signed",
            )
            AIRecommendation.objects.all().delete()
            self.assertTrue(check_for_anomalies(latest, signatory))
            rec = AIRecommendation.objects.get(model_name="allocation_anomaly_detector")
            self.assertEqual(rec.output["reason_code"], "DEVIATION_FROM_BASELINE")
            self.assertEqual(rec.output["metric"], "Profit margin")
            self.assertEqual(rec.disposition, "pending")
            self.assertTrue(rec.requires_human_review)
            self.assertIn("exception_case_id", rec.output)
            self.assertEqual(rec.requested_by_id, signatory.id)
            self.assertTrue(check_for_anomalies(latest, signatory))  # already flagged: no second case for the same run
            from apps.governance.models import ExceptionCase

            self.assertEqual(ExceptionCase._base_manager.filter(source_object_id=str(latest.id)).count(), 1)

            # BRD 6.2 step 12: a run is screened when the maker submits it, before anyone checks or approves it.
            maker = User.objects.filter(tenant=tenant, role="finance_maker").first()
            submitted = AllocationRun._base_manager.create(
                tenant=tenant, pool=pool, value_date=date(2025, 3, 1), gross_income=Decimal("1000.00"),
                distributable_amount=Decimal("90.00"), total_weighted_funds=Decimal("90.00"),
                depositor_pool_share=Decimal("90.00"), mudarib_share=Decimal("0.00"), status="simulated", created_by=maker,
            )
            self.client.force_authenticate(user=maker)
            self.client.defaults["HTTP_X_TENANT_CODE"] = tenant.code
            response = self.client.post(f"/api/v1/allocation/allocation-runs/{submitted.id}/submit-for-checking/")
            set_current_tenant(tenant)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertTrue(ExceptionCase._base_manager.filter(source_object_id=str(submitted.id)).exists())

            # a GL / sub-ledger mismatch is recorded by the reconciliation copilot
            batch = JournalBatch._base_manager.filter(tenant=tenant, allocation_run__isnull=False).first()
            line = batch.allocation_run.lines.first()
            from apps.allocation.models import AllocationLine

            AllocationLine._base_manager.filter(pk=line.pk).update(allocated_amount=line.allocated_amount + Decimal("5.00"))
            AIRecommendation.objects.filter(model_name="reconciliation_copilot").delete()
            self.assertTrue(check_reconciliation(batch))
            rec = AIRecommendation.objects.get(model_name="reconciliation_copilot")
            self.assertEqual(rec.output["reason_code"], "GL_SUBLEDGER_MISMATCH")
            self.assertEqual(Decimal(rec.output["difference"]), Decimal("-5.00"))
            self.assertEqual(rec.disposition, "pending")
            self.assertIn("nothing was posted", rec.output["proposed_action"].lower())
        finally:
            set_current_tenant(None)
