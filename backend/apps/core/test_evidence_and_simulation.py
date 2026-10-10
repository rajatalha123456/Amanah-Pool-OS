import io
import zipfile
from unittest import mock

from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import UserRole
from apps.allocation.models import AllocationLine
from apps.allocation.test_participant_ledger import END, ParticipantLedgerTestBase
from apps.ai_agents.services.contract_analyzer import analyze_contract_text
from apps.tenants.models import Tenant

from .banking_switch import execute_banking_settlement


class EvidenceBundleTests(ParticipantLedgerTestBase):
    def setUp(self):
        super().setUp()
        self.auditor = self._user("auditor", UserRole.AUDITOR)
        self.run_id = self.sign_run()

    def compile(self, user=None, **overrides):
        self.authenticate(user or self.auditor)
        payload = {"pool_id": str(self.pool.id), "period_date": str(END), "audit_type": "Inspection", **overrides}
        return self.client.post(reverse("evidence-bundle-compile"), payload, format="json")

    def artifact(self, bundle, artifact_id):
        return next(a for a in bundle["artifacts"] if a["meta"]["artifact_id"] == artifact_id)

    def test_bundle_contains_only_recorded_evidence(self):
        response = self.compile()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        bundle = response.data

        allocation = self.artifact(bundle, "ART-03-ALLOCATION")
        self.assertTrue(allocation["verified"])
        self.assertTrue(allocation["meta"]["hash_recomputes"])
        self.assertEqual(allocation["meta"]["run_id"], self.run_id)
        self.assertEqual(allocation["meta"]["line_count"], 3)
        self.assertEqual(allocation["meta"]["checker"], self.checker.email)

        # Evidence that does not exist is reported as such - never invented.
        for missing in ("ART-01-SHARIAH-DECISION", "ART-02-PERIOD-CLOSE", "ART-05-PAYOUT-CLEARING", "ART-07-RECONCILIATION"):
            artifact = self.artifact(bundle, missing)
            self.assertFalse(artifact["meta"]["available"], missing)
            self.assertFalse(artifact["verified"], missing)
        self.assertFalse(bundle["all_verified"])

        journals = self.artifact(bundle, "ART-04-GL-JOURNALS")
        self.assertTrue(journals["verified"])
        self.assertTrue(all(b["is_balanced"] for b in journals["meta"]["batches"]))

        chain = self.artifact(bundle, "ART-08-AUDIT-CHAIN")
        self.assertEqual(chain["meta"]["chain_status"], "VERIFIED")
        self.assertTrue(chain["verified"])

    def test_master_seal_covers_the_artifact_hashes(self):
        import hashlib

        bundle = self.compile().data
        expected = hashlib.sha256(":".join(a["hash"] for a in bundle["artifacts"]).encode()).hexdigest().upper()
        self.assertEqual(bundle["master_bundle_seal"], f"SEAL-SHA256:{expected}")

    def test_tampered_run_fails_verification(self):
        line = AllocationLine._base_manager.filter(allocation_run_id=self.run_id).first()
        AllocationLine._base_manager.filter(pk=line.pk).update(allocated_amount="999999.00")
        allocation = self.artifact(self.compile().data, "ART-03-ALLOCATION")
        self.assertFalse(allocation["meta"]["hash_recomputes"])
        self.assertFalse(allocation["verified"])

    def test_tampered_audit_trail_fails_verification(self):
        from .models import AuditLog

        entry = AuditLog.objects.filter(tenant=self.tenant, sequence__isnull=False).order_by("sequence").first()
        AuditLog.objects.filter(pk=entry.pk).update(reason="edited after the fact")
        chain = self.artifact(self.compile().data, "ART-08-AUDIT-CHAIN")
        self.assertEqual(chain["meta"]["chain_status"], "TAMPER_DETECTED")
        self.assertFalse(chain["verified"])

    def test_period_without_a_signed_run_has_no_allocation_evidence(self):
        bundle = self.compile(period_date="2025-01-15").data
        self.assertFalse(self.artifact(bundle, "ART-03-ALLOCATION")["meta"]["available"])

    def test_pool_of_another_tenant_is_not_accessible(self):
        other = Tenant.objects.create(name="Other", code="OTHER-EV", data_residency="PK")
        response = self.compile(pool_id="00000000-0000-0000-0000-000000000000")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(other.code, "OTHER-EV")

    def test_input_validation(self):
        self.authenticate(self.auditor)
        self.assertEqual(
            self.client.post(reverse("evidence-bundle-compile"), {}, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(self.compile(period_date="not-a-date").status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_oversight_roles_can_compile(self):
        for user in (self.maker, self.investor_b):
            self.assertEqual(self.compile(user=user).status_code, status.HTTP_403_FORBIDDEN)

    def test_zip_archive_is_built_from_the_same_evidence(self):
        self.authenticate(self.auditor)
        response = self.client.get(
            reverse("evidence-bundle-download"), {"pool_id": str(self.pool.id), "period_date": str(END)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        archive = zipfile.ZipFile(io.BytesIO(response.content))
        names = archive.namelist()
        self.assertIn("00_AUDIT_MANIFEST.json", names)
        self.assertIn("ART-03-ALLOCATION.json", names)
        self.assertNotIn("06_PAYOUT_ISO20022_PACS008_SIMULATION.xml", names)  # no batch was prepared
        self.assertIn("UNAVAILABLE", archive.read("01_DOSSIER.md").decode())


class SimulationLabelTests(SimpleTestCase):
    def test_banking_switch_results_are_labelled_simulated(self):
        ok = execute_banking_settlement(amount="100.00", source_title="A", source_iban="PK00TEST0000000000000000")
        failed = execute_banking_settlement(
            amount="100.00", source_title="A", source_iban="PK00TEST0000000000000000", simulate_failure_code="51"
        )
        for result in (ok, failed):
            self.assertTrue(result["simulated"])
            self.assertEqual(result["mode"], "SIMULATION")
        self.assertIn("SIMULATION", ok["regulatory_stamp"])

    def test_contract_analyzer_fallback_never_invents_terms_and_requires_review(self):
        with mock.patch("apps.ai_agents.services.contract_analyzer.requests.post", side_effect=RuntimeError("down")):
            result = analyze_contract_text(
                "This Mudarabah agreement guarantees the capital and a fixed profit.", "TENANT-X", "42"
            )
        self.assertEqual(result["source"], "keyword_screen_fallback")
        self.assertTrue(result["requires_human_review"])
        self.assertIsNone(result["depositor_psr"])
        self.assertIsNone(result["mudarib_psr"])
        self.assertEqual(result["clauses"], [])
        self.assertLess(result["confidence_score"], 0.5)
        self.assertEqual(result["shariah_verdict"], "CONTAINS_POTENTIAL_VIOLATIONS")

    def test_contract_analyzer_stays_in_the_callers_tenant_and_flags_low_confidence(self):
        response = mock.Mock(ok=True)
        response.json.return_value = {"research_summary": '{"contract_type": "qard", "confidence_score": 0.5}'}
        with mock.patch("apps.ai_agents.services.contract_analyzer.requests.post", return_value=response) as post:
            result = analyze_contract_text("text", "TENANT-X", "42")
        self.assertEqual(post.call_args.kwargs["headers"]["X-Tenant-Id"], "TENANT-X")
        self.assertEqual(result["source"], "shariah_copilot_llm")
        self.assertTrue(result["requires_human_review"])  # confidence below threshold
