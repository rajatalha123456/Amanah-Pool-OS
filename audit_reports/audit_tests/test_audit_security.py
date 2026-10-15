"""
Audit (Phase 4 / 8): runtime role matrix, investor and admin scope, cross-tenant isolation with two tenants.

Tenant A is fully seeded (`seed_project_data`, synthetic data); tenant B is built here with its own users and pool.
Every GET collection route is called by every role; POST {} is sent to every collection route by the read-only
roles (auditor, investor, super admin) - a 400 means the permission check passed and only validation stopped it.
Results are written to audit_reports/evidence/role_matrix.tsv. Runs on the throw-away test database.
"""

import json
import re
from datetime import date
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.urls import get_resolver
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence"
# Read-only-role POSTs reviewed in API_AUDIT.md and accepted (analysis, evidence, own notifications, administration).
REVIEWED = {
    ("auditor", "/api/v1/ai/audit-sampling/analyze/"), ("auditor", "/api/v1/ai/fraud-collusion/detect/"),
    ("auditor", "/api/v1/core/audit-log/simulate-tamper/"), ("auditor", "/api/v1/core/audit-log/verify-merkle/"),
    ("auditor", "/api/v1/core/evidence-bundle/compile/"), ("auditor", "/api/v1/core/evidence-bundle/download/"),
    ("auditor", "/api/v1/governance/shariah-audit-findings/"), ("auditor", "/api/v1/governance/support-requests/"),
    ("auditor", "/api/v1/notifications/mark-all-read/"),
    ("platform_super_admin", "/api/v1/core/audit-log/simulate-tamper/"), ("platform_super_admin", "/api/v1/core/audit-log/verify-merkle/"),
    ("platform_super_admin", "/api/v1/legal-entities/"), ("platform_super_admin", "/api/v1/notifications/mark-all-read/"),
    ("platform_super_admin", "/api/v1/products/jurisdiction-rule-packs/"), ("platform_super_admin", "/api/v1/tenants/"),
    # Administration: per-tenant feature flags and the encryption-key register (administrator only; tests in tenants.test_flags_and_keys).
    ("platform_super_admin", "/api/v1/tenants/feature-flags/"), ("platform_super_admin", "/api/v1/tenants/encryption-keys/"),
}
ROLES = [
    "platform_super_admin", "product_manager", "pool_manager", "finance_maker", "finance_checker",
    "shariah_secretariat", "shariah_board", "risk_compliance", "authorized_signatory", "auditor", "investor_member",
]


def collection_routes():
    out = []

    def walk(resolver, prefix=""):
        for entry in resolver.url_patterns:
            if hasattr(entry, "url_patterns"):
                walk(entry, prefix + str(entry.pattern))
                continue
            route = (prefix + str(entry.pattern)).replace("^", "").replace("$", "")
            if not route.startswith("api/v1/") or "(?P" in route or "<" in route or "format" in route:
                continue
            cb = entry.callback
            actions = getattr(cb, "actions", None)
            methods = {m.upper() for m in actions} if actions else {"GET", "POST"}
            out.append(("/" + route, methods))

    walk(get_resolver())
    return sorted(set((r, tuple(sorted(m))) for r, m in out))


class AuditSecurityTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_project_data", tenant_code="AUD-A", allow_non_debug=True, stdout=StringIO())
        cls.a = Tenant.objects.get(code="AUD-A")
        cls.b = Tenant.objects.create(name="Audit tenant B", code="AUD-B", data_residency="PK")
        cls.b_pm = User.objects.create_user(email="pm@tenant-b.test", password="Synthetic-Pass-1", role="pool_manager",
                                            tenant=cls.b, full_name="Tenant B manager")
        cls.b_investor = User.objects.create_user(email="inv@tenant-b.test", password="Synthetic-Pass-1",
                                                  role="investor_member", tenant=cls.b, full_name="Tenant B investor")
        from apps.products.models import ContractTemplate, Product
        from apps.pools.models import Pool

        set_current_tenant(cls.b)
        ct = ContractTemplate.objects.create(tenant=cls.b, name="B", contract_type="mudarabah_unrestricted", version="1", clauses={})
        pr = Product.objects.create(tenant=cls.b, name="B", code="B-P", operating_model="bank_pool", contract_template=ct)
        Pool.objects.create(tenant=cls.b, name="B pool", code="B-POOL", product=pr, effective_date=date(2026, 1, 1))
        set_current_tenant(None)

    def tearDown(self):
        set_current_tenant(None)

    def user(self, role, tenant=None):
        return User.objects.filter(tenant=tenant or self.a, role=role).order_by("email").first()

    def call(self, user, method, url, body=None, tenant_code="AUD-A", token=None):
        self.client.force_authenticate(user=None)
        if user is not None or token is not None:
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token or RefreshToken.for_user(user).access_token}")
        else:
            self.client.credentials()
        response = getattr(self.client, method)(url, body if body is not None else {}, format="json",
                                                HTTP_X_TENANT_CODE=tenant_code)
        set_current_tenant(None)
        return response

    def a_ids(self):
        """Primary keys of tenant A's financial records (pools, participants, accounts, runs, journals)."""
        from apps.accounting.models import JournalBatch
        from apps.allocation.models import AllocationRun
        from apps.participants.models import Participant, ParticipantAccount
        from apps.pools.models import Pool

        ids = {}
        for model in (Pool, Participant, ParticipantAccount, AllocationRun, JournalBatch):
            ids[model.__name__] = [str(x) for x in model._base_manager.filter(tenant=self.a).values_list("id", flat=True)[:50]]
        return ids

    # ------------------------------------------------------------------------------------------
    def test_role_matrix_and_scopes(self):
        routes = collection_routes()
        rows, violations = [], []
        users = {role: self.user(role) for role in ROLES}
        for route, methods in routes:
            for role, u in users.items():
                if u is None or "GET" not in methods:
                    continue
                code = self.call(u, "get", route).status_code
                rows.append((route, "GET", role, code))
            for role in ("auditor", "investor_member", "platform_super_admin"):
                if "POST" in methods and users[role] is not None:
                    code = self.call(users[role], "post", route, {}).status_code
                    rows.append((route, "POST{}", role, code))
                    if code not in (401, 403, 404, 405) and not (role == "investor_member" and re.search(r"support-requests|cast-vote|accept-rules|mark-all-read", route)) \
                            and not route.startswith("/api/v1/auth/") and not route.startswith("/api/v1/public/") \
                            and (role, route) not in REVIEWED:
                        violations.append(f"{role} POST {route} -> {code} (passed the permission check)")
        EVIDENCE.mkdir(exist_ok=True)
        with open(EVIDENCE / "role_matrix.tsv", "w", encoding="utf-8") as fh:
            fh.write("route\tmethod\trole\tstatus\n" + "\n".join("\t".join(map(str, r)) for r in rows))
        with open(EVIDENCE / "role_matrix_violations.txt", "w", encoding="utf-8") as fh:
            fh.write("\n".join(violations) or "none")
        self.assertEqual(violations, [], "\n".join(violations))

    def test_superadmin_reads_no_financial_data(self):
        admin = self.user("platform_super_admin")
        for url in ("/api/v1/pools/pools/", "/api/v1/participants/participants/", "/api/v1/allocation/allocation-runs/",
                    "/api/v1/accounting/journal-batches/", "/api/v1/circles/circle-members/"):
            self.assertIn(self.call(admin, "get", url).status_code, (403, 404), url)

    def test_investor_cannot_read_other_peoples_investment_records(self):
        """IDOR: an investor lists investment records; every row must belong to their own participant."""
        from apps.investments.models import CapitalAccount

        investor = User.objects.get(tenant=self.a, email__startswith="mudarabah.investor")
        own = {str(x) for x in CapitalAccount._base_manager.filter(tenant=self.a, participant__user=investor).values_list("id", flat=True)}
        others = [str(x) for x in CapitalAccount._base_manager.filter(tenant=self.a).exclude(participant__user=investor).values_list("id", flat=True)]
        leaks = []
        for url in ("/api/v1/investments/capital-accounts/", "/api/v1/investments/subscriptions/",
                    "/api/v1/investments/redemptions/", "/api/v1/investments/distribution-runs/",
                    "/api/v1/investments/nav-snapshots/"):
            r = self.call(investor, "get", url)
            body = json.dumps(r.data if hasattr(r, "data") else "", default=str)
            leaks += [f"{url} contains another investor's capital account {o}" for o in others if o in body]
        for other in others[:5]:
            code = self.call(investor, "get", f"/api/v1/investments/capital-accounts/{other}/").status_code
            if code == 200:
                leaks.append(f"capital account {other} of another investor opened directly (200)")
        with open(EVIDENCE / "investor_idor.txt", "w", encoding="utf-8") as fh:
            fh.write(f"own accounts: {len(own)}; other accounts in tenant: {len(others)}\n" + ("\n".join(leaks) or "no leak found"))
        self.assertEqual(leaks, [], "\n".join(leaks))

    def test_cross_tenant_reads_and_writes_are_denied(self):
        ids = self.a_ids()
        flat = [i for v in ids.values() for i in v]
        findings = []
        # 1. tenant B's user presents tenant A's code
        r = self.call(self.b_pm, "get", "/api/v1/pools/pools/", tenant_code="AUD-A")
        if r.status_code == 200:
            findings.append("tenant B user with X-Tenant-Code AUD-A was answered (200)")
        # 2. tenant B's user lists every collection in its own tenant: no tenant A id may appear
        for route, methods in collection_routes():
            if "GET" not in methods:
                continue
            r = self.call(self.b_pm, "get", route, tenant_code="AUD-B")
            if r.status_code != 200:
                continue
            body = json.dumps(getattr(r, "data", ""), default=str)
            hit = [i for i in flat if i in body]
            if hit:
                findings.append(f"{route}: {len(hit)} tenant A ids visible to tenant B")
        # 3. direct object access and mutation by id
        for url in ([f"/api/v1/pools/pools/{i}/" for i in ids["Pool"][:3]]
                    + [f"/api/v1/participants/participants/{i}/" for i in ids["Participant"][:3]]
                    + [f"/api/v1/allocation/allocation-runs/{i}/" for i in ids["AllocationRun"][:3]]
                    + [f"/api/v1/accounting/journal-batches/{i}/" for i in ids["JournalBatch"][:3]]):
            g = self.call(self.b_pm, "get", url, tenant_code="AUD-B").status_code
            p = self.call(self.b_pm, "patch", url, {"name": "x"}, tenant_code="AUD-B").status_code
            if g == 200 or p in (200, 202):
                findings.append(f"{url}: GET {g} PATCH {p}")
        with open(EVIDENCE / "cross_tenant.txt", "w", encoding="utf-8") as fh:
            fh.write(f"tenant A ids checked: { {k: len(v) for k, v in ids.items()} }\n" + ("\n".join(findings) or "no cross-tenant access found"))
        self.assertEqual(findings, [], "\n".join(findings))

    def test_authentication_failures(self):
        self.assertEqual(self.call(None, "get", "/api/v1/pools/pools/").status_code, 401)
        good = str(RefreshToken.for_user(self.user("pool_manager")).access_token)
        tampered = good[:-4] + ("AAAA" if not good.endswith("AAAA") else "BBBB")
        self.assertEqual(self.call(None, "get", "/api/v1/pools/pools/", token=tampered).status_code, 401)
        self.assertEqual(self.call(self.user("pool_manager"), "get", "/api/v1/pools/pools/", tenant_code="NOPE").status_code, 403)

    def test_mass_assignment_role_escalation(self):
        """A user changing their own role through the profile endpoint must not succeed."""
        pm = self.user("pool_manager")
        r = self.call(pm, "patch", "/api/v1/auth/me/", {"role": "authorized_signatory", "is_superuser": True})
        pm.refresh_from_db()
        self.assertEqual(pm.role, "pool_manager", f"role changed via /auth/me/ ({r.status_code})")
        self.assertFalse(pm.is_superuser)
