"""
Audit (Phase 11): physical deletion through the API (BRD 11: nothing posted may be physically deleted; use reversal/state transition).

Every staff role sends DELETE to each delete-enabled endpoint against a live/approved record of the seeded tenant.
The probe records whether the row (and rows that cascade from it) still exist. Output: audit_reports/evidence/delete_probe.tsv.
Throw-away test database only.
"""

from io import StringIO
from pathlib import Path

from django.apps import apps
from django.core.management import call_command
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence"
STAFF = ["platform_super_admin", "product_manager", "pool_manager", "finance_maker", "finance_checker",
         "shariah_secretariat", "shariah_board", "risk_compliance", "authorized_signatory", "auditor"]

TARGETS = [
    ("pools/pools", "pools.Pool", {"status": "open"}),
    ("allocation/reserve-policies", "allocation.ReservePolicy", {"is_active": True}),
    ("allocation/psr-schedules", "allocation.ProfitSharingRatio", {"status": "approved"}),
    ("allocation/weightage-bands", "allocation.WeightageBand", {"status": "approved"}),
    ("participants/accounts", "participants.ParticipantAccount", {}),
    ("participants/participants", "participants.Participant", {}),
    ("accounting/income-expense-events", "accounting.IncomeExpenseEvent", {"status": "posted"}),
    ("accounting/reconciliation-batches", "accounting.ReconciliationBatch", {}),
    ("governance/related-party-transactions", "governance.RelatedPartyTransaction", {}),
    ("governance/shariah-audit-findings", "governance.ShariahAuditFinding", {}),
    ("governance/shariah-audit-plans", "governance.ShariahAuditPlan", {"status": "approved"}),
    ("pools/assets", "pools.Asset", {}),
    ("pools/asset-assignments", "pools.AssetAssignment", {}),
    ("products/contract-templates", "products.ContractTemplate", {"status": "approved"}),
    ("products/jurisdiction-rule-packs", "products.JurisdictionRulePack", {}),
    ("products/products", "products.Product", {"status": "approved"}),
    ("products/shariah-decisions", "products.ShariahDecision", {"status": "approved"}),
]


class DeleteProbe(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_project_data", tenant_code="AUD-D", allow_non_debug=True, stdout=StringIO())
        cls.tenant = Tenant.objects.get(code="AUD-D")

    def tearDown(self):
        set_current_tenant(None)

    def test_delete_probe(self):
        rows, deleted = [], []
        for endpoint, label, flt in TARGETS:
            model = apps.get_model(label)
            obj = model._base_manager.filter(tenant=self.tenant, **flt).first()
            if obj is None:
                rows.append((endpoint, "-", "-", "no matching record in seed"))
                continue
            for role in STAFF:
                if not model._base_manager.filter(pk=obj.pk).exists():
                    break
                user = User.objects.filter(tenant=self.tenant, role=role).order_by("email").first()
                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
                r = self.client.delete(f"/api/v1/{endpoint}/{obj.pk}/", HTTP_X_TENANT_CODE="AUD-D")
                set_current_tenant(None)
                gone = not model._base_manager.filter(pk=obj.pk).exists()
                rows.append((endpoint, role, r.status_code, "DELETED" if gone else "kept"))
                if gone:
                    deleted.append(f"{role} physically deleted {label} {flt} via DELETE /{endpoint}/ (HTTP {r.status_code})")
        with open(EVIDENCE / "delete_probe.tsv", "w", encoding="utf-8") as fh:
            fh.write("endpoint\trole\tstatus\tresult\n" + "\n".join("\t".join(map(str, r)) for r in rows))
        with open(EVIDENCE / "delete_probe_deleted.txt", "w", encoding="utf-8") as fh:
            fh.write("\n".join(deleted) or "nothing was physically deleted")
        self.assertEqual(deleted, [], "\n".join(deleted))
