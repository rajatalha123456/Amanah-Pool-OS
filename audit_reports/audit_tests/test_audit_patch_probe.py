"""
Audit (Phase 4 / 6 / 11): can approved, posted or live records be changed in place by a single person?

For each update endpoint, every staff role sends one PATCH that changes an economically or legally relevant field of a
record that is already approved / posted / active. A change that persists is recorded with the role that made it.
Results: audit_reports/evidence/patch_probe.tsv. Runs on the throw-away test database with the seeded tenant.
"""

from datetime import date
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

# (endpoint, model label, filter for a live/approved record, field, new value)
PROBES = [
    ("allocation/reserve-policies", "allocation.ReservePolicy", {"is_active": True}, "current_balance", "1.00"),
    ("allocation/psr-schedules", "allocation.ProfitSharingRatio", {"status": "approved"}, "mudarib_share", "45.00"),
    ("allocation/weightage-bands", "allocation.WeightageBand", {"status": "approved"}, "weightage", "3.00"),
    ("investments/capital-accounts", "investments.CapitalAccount", {}, "units_held", "999999.0000"),
    ("participants/accounts", "participants.ParticipantAccount", {}, "opened_date", "2020-01-01"),
    ("pools/assets", "pools.Asset", {}, "face_value", "1.00"),
    ("pools/asset-assignments", "pools.AssetAssignment", {"unassigned_date__isnull": True}, "assigned_date", "2020-01-01"),
    ("accounting/income-expense-events", "accounting.IncomeExpenseEvent", {"status": "posted"}, "amount", "1.00"),
    ("circles/circle-members", "circles.CircleMember", {"payout_position__isnull": False}, "payout_position", 99),
    ("products/products", "products.Product", {"status": "approved"}, "minimum_subscription", "1.00"),
    ("products/contract-templates", "products.ContractTemplate", {"status": "approved"}, "version", "tampered"),
    ("products/shariah-decisions", "products.ShariahDecision", {"status": "approved"}, "title", "tampered"),
    ("governance/related-party-transactions", "governance.RelatedPartyTransaction", {"disclosure_status": "approved"}, "amount", "1.00"),
    ("pools/pools", "pools.Pool", {"status": "open"}, "effective_date", "2020-01-01"),
    ("products/jurisdiction-rule-packs", "products.JurisdictionRulePack", {}, "version", "tampered"),
    ("products/jurisdiction-rule-packs", "products.JurisdictionRulePack", {}, "rules_config",
     {"wht_filer_pct": 0, "wht_non_filer_pct": 0, "max_mudarib_share_pct": 99}),
]


class PatchProbe(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_project_data", tenant_code="AUD-P", allow_non_debug=True, stdout=StringIO())
        cls.tenant = Tenant.objects.get(code="AUD-P")

    def tearDown(self):
        set_current_tenant(None)

    def test_patch_probe(self):
        rows, changed = [], []
        for endpoint, label, flt, field, value in PROBES:
            model = apps.get_model(label)
            obj = model._base_manager.filter(tenant=self.tenant, **flt).first()
            if obj is None:
                rows.append((endpoint, "-", "no live record in seed", "", ""))
                continue
            original = getattr(obj, field)
            for role in STAFF:
                user = User.objects.filter(tenant=self.tenant, role=role).order_by("email").first()
                if user is None:
                    continue
                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
                r = self.client.patch(f"/api/v1/{endpoint}/{obj.pk}/", {field: value}, format="json",
                                      HTTP_X_TENANT_CODE="AUD-P")
                set_current_tenant(None)
                obj.refresh_from_db()
                now = getattr(obj, field)
                persisted = str(now) != str(original)
                rows.append((endpoint, role, r.status_code, f"{field}: {original} -> {now}", "CHANGED" if persisted else ""))
                if persisted:
                    changed.append(f"{role} changed {label}.{field} ({flt}) {original} -> {now} via PATCH /{endpoint}/ (HTTP {r.status_code})")
                    model._base_manager.filter(pk=obj.pk).update(**{field: original})  # restore for the next role
                    obj.refresh_from_db()
        EVIDENCE.mkdir(exist_ok=True)
        with open(EVIDENCE / "patch_probe.tsv", "w", encoding="utf-8") as fh:
            fh.write("endpoint\trole\tstatus\tvalue\tresult\n" + "\n".join("\t".join(map(str, r)) for r in rows))
        with open(EVIDENCE / "patch_probe_changes.txt", "w", encoding="utf-8") as fh:
            fh.write("\n".join(changed) or "no in-place change persisted")
        self.assertEqual(changed, [], "\n".join(changed))
