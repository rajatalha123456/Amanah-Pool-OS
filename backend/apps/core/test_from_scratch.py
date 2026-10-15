"""
The whole business from an EMPTY system, through the API, role by role, in the order a real installation works.

It is the executable version of docs/FROM_SCRATCH_WORKFLOW.md: every step names the role that does it, and a step a role is
not allowed to do is checked to be refused. If this test passes, the written workflow can be followed on screen.

Run: cd backend && python manage.py test apps.core.test_from_scratch --noinput -v 2
"""

from io import StringIO

from django.core.management import call_command
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

CODE = "SCRATCH"
DOMAIN = "scratch.test"


class FromScratch(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command(
            "bootstrap_clean_tenant", tenant_code=CODE, tenant_name="Scratch Co", domain=DOMAIN, with_users=True,
            allow_non_debug=True, stdout=StringIO(),
        )
        cls.tenant = Tenant.objects.get(code=CODE)

    def setUp(self):
        set_current_tenant(self.tenant)
        self.clients = {}

    def tearDown(self):
        set_current_tenant(None)

    # helpers ---------------------------------------------------------------------------------------------------
    def as_(self, login):
        if login not in self.clients:
            user = User.objects.get(email=f"{login}@{DOMAIN}")
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}", HTTP_X_TENANT_CODE=CODE)
            self.clients[login] = client
        return self.clients[login]

    def call(self, login, method, url, body=None, expect=None):
        response = getattr(self.as_(login), method)(url, body, format="json") if body is not None else getattr(self.as_(login), method)(url, format="json")
        set_current_tenant(self.tenant)
        if expect is not None:
            ok = response.status_code in (expect if isinstance(expect, (list, tuple)) else [expect])
            self.assertTrue(ok, f"{login} {method.upper()} {url} -> {response.status_code} {getattr(response, 'data', '')}")
        return response

    def refused(self, login, method, url, body=None):
        r = self.call(login, method, url, body)
        self.assertIn(r.status_code, (400, 403, 409), f"{login} {method.upper()} {url} should have been refused, got {r.status_code} {r.data}")
        return r

    # the system starts empty -------------------------------------------------------------------------------------
    def test_00_a_clean_system_is_really_empty(self):
        from apps.pools.models import Pool
        from apps.products.models import Product, ShariahDecision
        from apps.participants.models import Participant

        self.assertEqual(Pool._base_manager.count() + Product._base_manager.count() + ShariahDecision._base_manager.count(), 0)
        self.assertEqual(Participant._base_manager.count(), 0)
        self.assertEqual(User.objects.filter(tenant=self.tenant).count(), 12)  # superadmin + 11 role logins

    # ----------------------------------------------------------------------------------------------------------------
    def phase_a_foundation(self):
        """Who sets up what BEFORE any product exists: rule pack, approval matrix, accounting map."""
        # A1. The administrator can create more users; the password is generated and shown once.
        made = self.call("superadmin", "post", "/api/v1/auth/users/", {
            "email": f"extra@{DOMAIN}", "full_name": "Extra User", "role": "auditor", "tenant": str(self.tenant.id),
        }, expect=201)
        self.assertTrue(made.data["generated_password"])

        # A2. Jurisdiction rule pack: Risk (or the administrator) proposes, a finance checker / signatory approves.
        pack = {
            "code": "PK-RULES", "name": "Pakistan rule pack", "version": "2026.01", "effective_date": "2026-01-01",
            "is_active": True, "is_default": True, "description": "Training pack",
            "rules_config": {
                "per_ceiling_pct": 5.0, "irr_ceiling_pct": 10.0, "notice_period_days": 30, "mudarib_share_cap_pct": 40.0,
                "wht_filer_pct": 15.0, "wht_non_filer_pct": 30.0, "zakat_deduction_pct": 0, "purification_interval": "monthly",
            },
            "change_reason": "First rule pack of the tenant",
        }
        self.refused("maker", "post", "/api/v1/products/jurisdiction-rule-packs/", pack)
        proposal = self.call("risk", "post", "/api/v1/products/jurisdiction-rule-packs/", pack, expect=202)
        self.refused("risk", "post", f"/api/v1/governance/config-changes/{proposal.data['id']}/approve/")
        self.call("checker", "post", f"/api/v1/governance/config-changes/{proposal.data['id']}/approve/", expect=200)
        packs = self.call("risk", "get", "/api/v1/products/jurisdiction-rule-packs/", expect=200).data
        self.assertEqual(len(packs), 1)
        self.assertTrue(packs[0]["is_default"])

        # A3. Approval matrix: who may give the final release of each kind. Risk proposes, a finance checker approves.
        for action, role, limit in (
            ("allocation_release", "authorized_signatory", "500000000.00"),
            ("distribution_approve", "authorized_signatory", "500000000.00"),
            ("payout_approve", "finance_checker", "50000000.00"),
        ):
            body = {"action": action, "role": role, "max_amount": limit, "change_reason": f"Authority for {action}"}
            self.refused("maker", "post", "/api/v1/accounting/approval-matrix/", body)
            p = self.call("risk", "post", "/api/v1/accounting/approval-matrix/", body, expect=202)
            self.call("checker", "post", f"/api/v1/governance/config-changes/{p.data['id']}/approve/", expect=200)
        self.assertEqual(len(self.call("risk", "get", "/api/v1/accounting/approval-matrix/", expect=200).data), 3)

        # A4. Accounting map: each logical pool account to the bank's GL code. Finance maker proposes; a checker approves.
        catalog = self.call("maker", "get", "/api/v1/accounting/account-mappings/catalog/", expect=200).data
        self.assertTrue(any(row["required_for"] for row in catalog))
        for row in catalog:
            body = {"account_key": row["key"], "gl_code": f"{1000 + len(row['key'])}-{abs(hash(row['key'])) % 900 + 100}",
                    "gl_name": row["default_name"], "change_reason": "Initial chart mapping"}
            p = self.call("maker", "post", "/api/v1/accounting/account-mappings/", body, expect=202)
            self.call("checker", "post", f"/api/v1/governance/config-changes/{p.data['id']}/approve/", expect=200)
        self.assertEqual(len(self.call("maker", "get", "/api/v1/accounting/account-mappings/", expect=200).data), len(catalog))

    def phase_b_product_and_pool(self):
        """Shariah approval, then product, pool and its economics; the pool opens only when every gate passes."""
        from apps.tenants.models import LegalEntity

        # B1. The Shariah Secretariat drafts the ruling; the Board approves it by quorum (two thirds of the Board).
        ruling = {
            "decision_code": "FATWA-T-001", "title": "Unrestricted Mudarabah deposit pool", "decision_type": "product_approval",
            "description": "Approval of an unrestricted Mudarabah pool with daily-balance profit sharing.",
            "fiqh_reference": "AAOIFI Shariah Standard No. 13", "mandatory_caveats": "Loss is borne by the capital providers.",
            "effective_date": "2026-01-01",
        }
        self.refused("maker", "post", "/api/v1/products/shariah-decisions/", ruling)
        decision = self.call("secretariat", "post", "/api/v1/products/shariah-decisions/", ruling, expect=201).data
        d = f"/api/v1/products/shariah-decisions/{decision['id']}/"
        vote = {"vote": "approve", "fiqh_opinion_notes": "Compliant with the cited standard"}
        self.refused("secretariat", "post", d + "cast-quorum-vote/", vote)  # not a Board member
        self.call("board", "post", d + "cast-quorum-vote/", vote, expect=200)
        self.assertEqual(self.call("board", "get", d, expect=200).data["status"], "draft", "one member is not a quorum")
        self.refused("board", "post", d + "cast-quorum-vote/", vote)  # no second vote by the same member
        done = self.call("board2", "post", d + "cast-quorum-vote/", vote, expect=200)
        self.assertEqual(done.data["status"], "approved")
        decision_id = decision["id"]

        # B2. The Product Manager drafts the contract template and the product; the Board approves both.
        template = {"name": "Unrestricted Mudarabah Charter", "contract_type": "mudarabah_unrestricted", "version": "1.0",
                    "clauses": {}, "shariah_decision": decision_id}
        self.refused("poolmanager", "post", "/api/v1/products/contract-templates/", template)
        ct = self.call("pm", "post", "/api/v1/products/contract-templates/", template, expect=201).data
        self.refused("pm", "post", f"/api/v1/products/contract-templates/{ct['id']}/approve/")  # cannot approve own work
        self.call("board", "post", f"/api/v1/products/contract-templates/{ct['id']}/approve/", expect=200)

        product = {"name": "General Depositor Pool", "code": "GEN-DEP", "operating_model": "bank_pool", "contract_template": ct["id"],
                   "base_currency": "PKR", "eligible_asset_types": ["murabahah", "ijarah"], "minimum_subscription": "1000.00"}
        prod = self.call("pm", "post", "/api/v1/products/products/", product, expect=201).data
        self.call("pm", "post", f"/api/v1/products/products/{prod['id']}/submit-for-review/", expect=200)
        self.refused("pm", "post", f"/api/v1/products/products/{prod['id']}/approve/")
        self.call("board", "post", f"/api/v1/products/products/{prod['id']}/approve/", expect=200)

        # B3. The Pool Manager creates the pool, proposes its economics; the Board approves them.
        entity = LegalEntity.objects.filter(tenant=self.tenant).first()
        pool_body = {"name": "General Depositor Pool 2026", "code": "GEN-2026", "product": prod["id"], "effective_date": "2026-01-01",
                     "legal_entity": str(entity.id), "branch": "Main Branch", "timezone": "Asia/Karachi", "calendar": "mon_fri"}
        self.refused("maker", "post", "/api/v1/pools/pools/", pool_body)
        pool = self.call("poolmanager", "post", "/api/v1/pools/pools/", pool_body, expect=201).data
        pid = pool["id"]

        # activation readiness lists every missing piece, in plain words
        ready = self.call("poolmanager", "get", f"/api/v1/pools/pools/{pid}/activation-readiness/", expect=200).data
        missing = {c["key"] for c in ready["checks"] if not c["passed"]} if "checks" in ready else set()
        self.assertIn("psr_approved", missing)
        self.assertIn("weightages_approved", missing)

        psr = self.call("poolmanager", "post", "/api/v1/allocation/psr-schedules/", {
            "pool": pid, "depositor_share": "70.00", "mudarib_share": "30.00", "effective_from": "2026-01-01"}, expect=201).data
        self.refused("poolmanager", "post", f"/api/v1/allocation/psr-schedules/{psr['id']}/approve/")
        self.call("board", "post", f"/api/v1/allocation/psr-schedules/{psr['id']}/approve/", expect=200)
        for cls, weight in (("savings", "1.00"), ("term", "1.25")):
            band = self.call("poolmanager", "post", "/api/v1/allocation/weightage-bands/", {
                "pool": pid, "participant_class": cls, "weightage": weight, "effective_from": "2026-01-01"}, expect=201).data
            self.call("board", "post", f"/api/v1/allocation/weightage-bands/{band['id']}/approve/", expect=200)

        # B4. Pool lifecycle: submit, Board approves, an independent checker or signatory opens it.
        self.call("poolmanager", "post", f"/api/v1/pools/pools/{pid}/submit-for-approval/", expect=200)
        self.call("board", "post", f"/api/v1/pools/pools/{pid}/approve/", expect=200)
        self.refused("poolmanager", "post", f"/api/v1/pools/pools/{pid}/open/")
        self.call("checker", "post", f"/api/v1/pools/pools/{pid}/open/", expect=200)
        self.assertEqual(self.call("poolmanager", "get", f"/api/v1/pools/pools/{pid}/", expect=200).data["status"], "open")
        return pid

    def phase_c_bank_pool_operations(self, pid):
        """Participants, balances, income and expense, the daily close, then the profit run and its four-person release."""
        # C1. People who put money into the pool. Pool manager or finance maker registers; Risk verifies KYC.
        people = [("CUS-001", "Aisha Depositor", "savings", "PK00TEST0000000000000001", "35202-1111111-1"),
                  ("CUS-002", "Bilal Depositor", "term", "PK00TEST0000000000000002", "35202-2222222-2")]
        ids = {}
        for ref, name, cls, iban, cnic in people:
            body = {"reference": ref, "full_name": name, "participant_class": cls, "iban": iban, "cnic_ntn": cnic,
                    "bank_name": "Test Bank", "tax_status": "filer", "email": f"{ref.lower()}@example.test"}
            self.refused("auditor", "post", "/api/v1/participants/participants/", body)
            ids[ref] = self.call("poolmanager", "post", "/api/v1/participants/participants/", body, expect=201).data["id"]
            self.refused("maker", "post", f"/api/v1/participants/participants/{ids[ref]}/verify-kyc/", {"note": "x"})
            self.call("risk", "post", f"/api/v1/participants/participants/{ids[ref]}/verify-kyc/", {"note": "ID checked"}, expect=200)
        # C2. Each person gets an account in the pool.
        for n, (ref, *_rest) in enumerate(people, start=1):
            self.call("poolmanager", "post", "/api/v1/participants/accounts/", {
                "participant": ids[ref], "pool": pid, "account_number": f"ACC-00{n}", "opened_date": "2026-01-01"}, expect=201)

        # C3. Pool income and expense: the maker records, a different checker posts (nothing counts before that).
        income = self.call("maker", "post", "/api/v1/accounting/income-expense-events/", {
            "pool": pid, "event_type": "income", "category": "Financing Profit", "amount": "120000.00",
            "event_date": "2026-01-03", "description": "Murabaha sales profit"}, expect=201).data
        expense = self.call("maker", "post", "/api/v1/accounting/income-expense-events/", {
            "pool": pid, "event_type": "expense", "category": "Direct Takaful", "amount": "20000.00",
            "event_date": "2026-01-04", "description": "Asset protection premium"}, expect=201).data
        for ev in (income, expense):
            self.refused("maker", "post", f"/api/v1/accounting/income-expense-events/{ev['id']}/post/")
            self.call("checker", "post", f"/api/v1/accounting/income-expense-events/{ev['id']}/post/", expect=200)

        # C4. Each day: balances come in (maker), then the day is closed (maker prepares, a different checker signs).
        for day in ("2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"):
            imp = self.call("maker", "post", "/api/v1/pools/balance-imports/", {
                "pool": pid, "value_date": day, "control_total_expected": "1500000.00",
                "records": [{"account_number": "ACC-001", "balance_amount": "1000000.00"},
                            {"account_number": "ACC-002", "balance_amount": "500000.00"}]}, expect=[200, 201])
            self.call("maker", "post", "/api/v1/pools/daily-closes/prepare/", {"pool": pid, "value_date": day, "notes": "Day checked"}, expect=[200, 201])
            close = self.call("maker", "get", f"/api/v1/pools/daily-closes/?pool={pid}", expect=200).data
            rows = close if isinstance(close, list) else close["results"]
            row = [c for c in rows if c["value_date"] == day][0]
            self.refused("maker", "post", f"/api/v1/pools/daily-closes/{row['id']}/sign/")
            self.call("checker", "post", f"/api/v1/pools/daily-closes/{row['id']}/sign/", expect=200)
        return ids

    def phase_d_profit_run(self, pid, people):
        """The month-end profit run: maker calculates, checker checks, Shariah reviews, signatory releases."""
        run = self.call("maker", "post", "/api/v1/allocation/allocation-runs/", {"pool": pid, "value_date": "2026-01-05", "period_start": "2026-01-01"}, expect=201).data
        rid = run["id"]
        base = f"/api/v1/allocation/allocation-runs/{rid}"
        self.refused("checker", "post", f"{base}/check/")  # not submitted yet
        self.refused("auditor", "post", f"{base}/submit-for-checking/")
        self.call("maker", "post", f"{base}/submit-for-checking/", expect=200)
        self.refused("maker", "post", f"{base}/check/")
        self.call("checker", "post", f"{base}/check/", expect=200)
        self.refused("signatory", "post", f"{base}/approve/")  # Shariah review comes first
        self.call("secretariat", "post", f"{base}/shariah-sign-off/", {"note": "Reviewed"}, expect=200)
        self.refused("checker", "post", f"{base}/approve/")
        self.call("signatory", "post", f"{base}/approve/", expect=200)
        done = self.call("auditor", "get", f"{base}/", expect=200).data
        self.assertIn(done["status"], ("signed",))
        # Statements, then give the first depositor a sign-in of their own (admin creates the user, pool manager links it).
        self.call("maker", "post", f"{base}/generate-statements/", expect=[200, 201])
        self.call("superadmin", "post", "/api/v1/auth/users/", {
            "email": f"cus001@{DOMAIN}", "full_name": "Aisha Depositor", "role": "investor_member", "tenant": str(self.tenant.id)}, expect=[200, 201])
        self.refused("maker", "post", f"/api/v1/participants/participants/{people['CUS-001']}/link-login/", {"email": f"cus001@{DOMAIN}"})
        self.call("poolmanager", "post", f"/api/v1/participants/participants/{people['CUS-001']}/link-login/", {"email": f"cus001@{DOMAIN}"}, expect=200)
        self.refused("poolmanager", "post", f"/api/v1/participants/participants/{people['CUS-002']}/link-login/", {"email": f"cus001@{DOMAIN}"})
        self.as_("cus001")
        mine = self.call("cus001", "get", "/api/v1/allocation/allocation-runs/my-statements/", expect=200).data
        self.assertTrue(len(mine) >= 1)
        return rid

    def test_full_lifecycle(self):
        self.phase_a_foundation()
        self.pool_id = self.phase_b_product_and_pool()
        self.people = self.phase_c_bank_pool_operations(self.pool_id)
        self.run_id = self.phase_d_profit_run(self.pool_id, self.people)
