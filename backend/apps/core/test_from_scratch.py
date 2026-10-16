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

        # BRD 6.1: the Shariah authority may also return or reject. A returned draft goes back to the Secretariat; votes
        # of the earlier round stop counting. A quorum of rejections rejects it for good.
        other = self.call("secretariat", "post", "/api/v1/products/shariah-decisions/", {**ruling, "decision_code": "FATWA-T-002"}, expect=201).data
        o = f"/api/v1/products/shariah-decisions/{other['id']}/"
        self.call("board", "post", o + "cast-quorum-vote/", vote, expect=200)
        self.refused("board2", "post", o + "return-for-revision/", {})  # a reason is required
        self.refused("secretariat", "post", o + "return-for-revision/", {"note": "x"})
        back = self.call("board2", "post", o + "return-for-revision/", {"note": "Cite the SBP circular as well"}, expect=200).data
        self.assertEqual((back["status"], back["review_round"]), ("returned", 2))
        self.refused("board3", "post", o + "cast-quorum-vote/", vote)  # nothing to vote on while it is with the Secretariat
        self.call("secretariat", "patch", o, {"fiqh_reference": "AAOIFI SS 13; SBP IBD circular"}, expect=200)
        self.call("secretariat", "post", o + "resubmit/", expect=200)
        again = self.call("board", "post", o + "cast-quorum-vote/", vote, expect=200).data
        self.assertEqual(again["status"], "draft", "the first-round vote no longer counts, so one new vote is not a quorum")
        no = {"vote": "reject", "fiqh_opinion_notes": "Not convinced"}
        self.call("board2", "post", o + "cast-quorum-vote/", no, expect=200)
        done = self.call("board3", "post", o + "cast-quorum-vote/", no, expect=200).data
        self.assertEqual(done["status"], "rejected")

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

        # BRD 10: posting books the journal. Income: Dr accrued income / Cr pool income; expense: Dr pool expense / Cr payable.
        from apps.accounting.models import IncomeExpenseEvent, JournalEntry

        def legs(event_id):
            batch = IncomeExpenseEvent._base_manager.get(pk=event_id).journal_batch_id
            return sorted((e.account_key, e.entry_type, str(e.amount)) for e in JournalEntry._base_manager.filter(batch_id=batch))

        self.assertEqual(legs(income["id"]), [("accrued_income_receivable", "debit", "120000.00"), ("pool_income", "credit", "120000.00")])
        self.assertEqual(legs(expense["id"]), [("expense_payable", "credit", "20000.00"), ("pool_direct_expense", "debit", "20000.00")])

        # Non-permissible income (a late-payment penalty) never reaches the pool: it is booked to the clearing account,
        # the Board approves the purification, a finance checker records the charity payment.
        penalty = self.call("maker", "post", "/api/v1/accounting/income-expense-events/", {
            "pool": pid, "event_type": "income", "category": "Late payment penalty", "amount": "3000.00",
            "event_date": "2026-01-04", "description": "Charity-bound late payment amount"}, expect=201).data
        self.call("checker", "post", f"/api/v1/accounting/income-expense-events/{penalty['id']}/post/", expect=200)
        self.assertEqual(legs(penalty["id"]), [("accrued_income_receivable", "debit", "3000.00"), ("non_permissible_clearing", "credit", "3000.00")])
        entries = self.call("risk", "get", f"/api/v1/governance/purification-entries/?pool={pid}", expect=200).data
        entry = (entries if isinstance(entries, list) else entries["results"])[0]
        self.refused("checker", "post", f"/api/v1/governance/purification-entries/{entry['id']}/approve/")
        self.call("board", "post", f"/api/v1/governance/purification-entries/{entry['id']}/approve/", expect=200)
        self.call("checker", "post", f"/api/v1/governance/purification-entries/{entry['id']}/mark-distributed/", {
            "charity_recipient": "Registered charity (training)", "distributed_date": "2026-01-05"}, expect=200)
        from apps.governance.models import PurificationEntry

        saved = PurificationEntry._base_manager.get(pk=entry["id"])
        self.assertIsNotNone(saved.approval_journal_id)
        self.assertIsNotNone(saved.distribution_journal_id)

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
        # BRD R-114: the simulator calculates but writes nothing (no run, line, journal or AI record).
        from apps.accounting.models import JournalBatch
        from apps.ai_agents.models import AIRecommendation
        from apps.allocation.models import AllocationLine, AllocationRun

        def rows():
            return (AllocationRun._base_manager.count(), AllocationLine._base_manager.count(),
                    JournalBatch._base_manager.count(), AIRecommendation._base_manager.count())

        before = rows()
        self.call("maker", "post", "/api/v1/allocation/allocation-runs/simulate/", {"pool": pid, "value_date": "2026-01-05", "period_start": "2026-01-01"}, expect=200)
        self.assertEqual(rows(), before, "simulate must not write anything")
        run = self.call("maker", "post", "/api/v1/allocation/allocation-runs/", {"pool": pid, "value_date": "2026-01-05", "period_start": "2026-01-01"}, expect=201).data
        rid = run["id"]
        # BRD 6.3 step 19: tolerance, fairness, negative yield and prior-period tests are on the run before anyone checks it.
        tests = {t["key"]: t["status"] for t in run["run_tests"]}
        self.assertEqual(tests, {"tolerance": "pass", "fairness": "pass", "negative_yield": "pass", "prior_period": "info"})
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
        # BRD 9: the explanation also in Urdu and Arabic, from the signed figures.
        stmt = mine[0]
        for lang in ("ur", "ur_roman", "ar"):
            self.assertIn(str(stmt["profit_allocated"]), stmt["narrative_translations"][lang], lang)
        return rid

    def phase_e_community_circle(self):
        """A rotating savings circle (Qard) from nothing: ruling, product, pool, rules, members, contributions, draw, payout, closure."""
        from apps.tenants.models import LegalEntity

        ruling = {"decision_code": "FATWA-C-001", "title": "Qard-based rotating savings circle", "decision_type": "product_approval",
                  "description": "A circle in which members lend each other in turn and no one receives more than the pot collected.",
                  "fiqh_reference": "AAOIFI Shariah Standard No. 19 (Qard)", "mandatory_caveats": "No interest, late charge or uplift.",
                  "effective_date": "2026-01-01"}
        d = self.call("secretariat", "post", "/api/v1/products/shariah-decisions/", ruling, expect=201).data["id"]
        vote = {"vote": "approve", "fiqh_opinion_notes": "Qard without benefit"}
        self.call("board", "post", f"/api/v1/products/shariah-decisions/{d}/cast-quorum-vote/", vote, expect=200)
        self.call("board2", "post", f"/api/v1/products/shariah-decisions/{d}/cast-quorum-vote/", vote, expect=200)
        ct = self.call("pm", "post", "/api/v1/products/contract-templates/", {
            "name": "Qard Circle Charter", "contract_type": "qard", "version": "1.0", "clauses": {}, "shariah_decision": d}, expect=201).data
        self.call("board", "post", f"/api/v1/products/contract-templates/{ct['id']}/approve/", expect=200)
        prod = self.call("pm", "post", "/api/v1/products/products/", {
            "name": "Neighbourhood Circle", "code": "CIRCLE-1", "operating_model": "community_circle", "contract_template": ct["id"],
            "base_currency": "PKR", "eligible_asset_types": [], "minimum_subscription": "1000.00"}, expect=201).data
        self.call("pm", "post", f"/api/v1/products/products/{prod['id']}/submit-for-review/", expect=200)
        self.call("board", "post", f"/api/v1/products/products/{prod['id']}/approve/", expect=200)
        entity = LegalEntity.objects.filter(tenant=self.tenant).first()
        pool = self.call("poolmanager", "post", "/api/v1/pools/pools/", {
            "name": "Neighbourhood Circle 2026", "code": "CIR-2026", "product": prod["id"], "effective_date": "2026-01-01",
            "legal_entity": str(entity.id), "branch": "Main Branch", "timezone": "Asia/Karachi", "calendar": "daily"}, expect=201).data
        pid = pool["id"]
        ready = self.call("poolmanager", "get", f"/api/v1/pools/pools/{pid}/activation-readiness/", expect=200).data
        self.call("poolmanager", "post", f"/api/v1/pools/pools/{pid}/submit-for-approval/", expect=200)
        self.call("board", "post", f"/api/v1/pools/pools/{pid}/approve/", expect=200)
        self.call("checker", "post", f"/api/v1/pools/pools/{pid}/open/", expect=200)

        # Rules first: the organizer publishes them, then members are recorded as having accepted them.
        self.refused("maker", "post", "/api/v1/circles/rules/publish/", {"pool": pid, "contribution_amount": "10000", "cycle_days": 30})
        self.call("poolmanager", "post", "/api/v1/circles/rules/publish/", {
            "pool": pid, "contribution_amount": "10000.00", "cycle_days": 30, "first_due_date": "2026-02-01",
            "order_policy": "Random provably fair draw", "hardship_policy": "Deferral without any charge"}, expect=201)
        members = []
        for n in (1, 2, 3):
            m = self.call("poolmanager", "post", "/api/v1/circles/circle-members/", {
                "pool": pid, "member_name": f"Member {n}", "member_reference": f"M-{n}", "joined_date": "2026-01-15",
                "email": f"m{n}@example.test", "iban": f"PK00TEST00000000000010{n}", "bank_name": "Test Bank"}, expect=201).data["id"]
            self.refused("maker", "post", f"/api/v1/circles/circle-members/{m}/verify-kyc/", {})
            self.call("risk", "post", f"/api/v1/circles/circle-members/{m}/verify-kyc/", {}, expect=200)
            self.call("poolmanager", "post", "/api/v1/circles/rules/accept/", {"member": m, "method": "in_person", "evidence_reference": f"SIGN-{n}"}, expect=201)
            members.append(m)

        # The draw fixes the order: commit first (the organizer cannot see the result), then execute with a client seed.
        draw = self.call("poolmanager", "post", "/api/v1/circles/draws/commit/", {"pool": pid}, expect=201).data
        self.call("poolmanager", "post", f"/api/v1/circles/draws/{draw['id']}/execute/", {"client_seed": "witness-seed-1"}, expect=200)
        self.assertTrue(self.call("auditor", "get", f"/api/v1/circles/draws/{draw['id']}/verify/", expect=200).data)

        # Three cycles (one per member): everyone pays in, then the member whose turn it is receives exactly the pot.
        for cycle in (1, 2, 3):
            day = f"2026-0{cycle + 1}-01"
            for m in members:
                if cycle == 1:
                    self.refused("poolmanager", "post", f"/api/v1/circles/circle-members/{m}/record-contribution/", {"amount": "10000.00", "contribution_date": day, "cycle_number": cycle})
                self.call("maker", "post", f"/api/v1/circles/circle-members/{m}/record-contribution/", {
                    "amount": "10000.00", "contribution_date": day, "cycle_number": cycle, "payment_reference": f"RAAST-{cycle}-{m[:6]}"}, expect=[200, 201])
            roster = self.call("poolmanager", "get", f"/api/v1/circles/circle-members/?pool={pid}", expect=200).data
            rows = roster if isinstance(roster, list) else roster["results"]
            turn = [r for r in rows if r["payout_position"] == cycle][0]
            req = self.call("poolmanager", "post", f"/api/v1/circles/payouts/request-payout/{pid}/", {
                "member_id": turn["id"], "cycle_number": cycle, "settlement_rail": "internal_book", "payout_date": f"2026-0{cycle + 1}-02"}, expect=201).data
            self.assertEqual(req["amount"], "30000.00", "the payout is exactly the pot collected, nothing more")
            if cycle == 1:
                self.refused("poolmanager", "post", f"/api/v1/circles/payouts/{req['id']}/approve/")
            self.call("checker", "post", f"/api/v1/circles/payouts/{req['id']}/approve/", expect=200)
            self.call("maker", "post", f"/api/v1/circles/payouts/{req['id']}/settle/", {}, expect=200)

        # Closure: collected equals disbursed, the organizer prepares, a finance checker closes.
        preview = self.call("poolmanager", "get", f"/api/v1/circles/closures/preview/?pool={pid}", expect=200).data
        self.call("poolmanager", "post", "/api/v1/circles/closures/prepare/", {"pool": pid, "resolution_note": "All cycles paid"}, expect=201)
        self.refused("poolmanager", "post", "/api/v1/circles/closures/close/", {"pool": pid})
        closed = self.call("checker", "post", "/api/v1/circles/closures/close/", {"pool": pid}, expect=200).data
        self.assertEqual(closed["difference"], "0.00", preview)
        return pid, members

    def phase_e2_wakalah_circle(self):
        """The approved Wakalah model: a fixed, disclosed service fee per payout, payment mandates verified first."""
        from apps.tenants.models import LegalEntity

        d = self.call("secretariat", "post", "/api/v1/products/shariah-decisions/", {
            "decision_code": "FATWA-C-002", "title": "Wakalah-serviced savings circle", "decision_type": "product_approval",
            "description": "An agent runs the circle for a fixed disclosed fee per payout; no interest or time-based charge.",
            "fiqh_reference": "AAOIFI Shariah Standard No. 23 (Agency)", "mandatory_caveats": "Fee is fixed and disclosed.",
            "effective_date": "2026-01-01"}, expect=201).data["id"]
        vote = {"vote": "approve", "fiqh_opinion_notes": "Agency for a known fee"}
        self.call("board", "post", f"/api/v1/products/shariah-decisions/{d}/cast-quorum-vote/", vote, expect=200)
        self.call("board2", "post", f"/api/v1/products/shariah-decisions/{d}/cast-quorum-vote/", vote, expect=200)
        ct = self.call("pm", "post", "/api/v1/products/contract-templates/", {
            "name": "Wakalah Circle Charter", "contract_type": "wakalah", "version": "1.0", "clauses": {}, "shariah_decision": d}, expect=201).data
        self.call("board", "post", f"/api/v1/products/contract-templates/{ct['id']}/approve/", expect=200)
        prod = self.call("pm", "post", "/api/v1/products/products/", {
            "name": "Serviced Circle", "code": "CIRCLE-W", "operating_model": "community_circle", "contract_template": ct["id"],
            "base_currency": "PKR", "eligible_asset_types": [], "minimum_subscription": "1000.00"}, expect=201).data
        self.call("pm", "post", f"/api/v1/products/products/{prod['id']}/submit-for-review/", expect=200)
        self.call("board", "post", f"/api/v1/products/products/{prod['id']}/approve/", expect=200)
        entity = LegalEntity.objects.filter(tenant=self.tenant).first()
        pid = self.call("poolmanager", "post", "/api/v1/pools/pools/", {
            "name": "Serviced Circle 2026", "code": "CIRW-2026", "product": prod["id"], "effective_date": "2026-01-01",
            "legal_entity": str(entity.id), "branch": "Main Branch", "timezone": "Asia/Karachi", "calendar": "daily"}, expect=201).data["id"]
        self.call("poolmanager", "post", f"/api/v1/pools/pools/{pid}/submit-for-approval/", expect=200)
        self.call("board", "post", f"/api/v1/pools/pools/{pid}/approve/", expect=200)
        self.call("checker", "post", f"/api/v1/pools/pools/{pid}/open/", expect=200)

        rules = {"pool": pid, "contribution_amount": "10000.00", "cycle_days": 30, "first_due_date": "2026-02-01",
                 "order_policy": "Random provably fair draw", "hardship_policy": "Deferral without any charge",
                 "operating_model": "wakalah", "service_fee_per_cycle": "500.00", "mandates_required": True}
        self.refused("poolmanager", "post", "/api/v1/circles/rules/publish/", {**rules, "service_fee_per_cycle": "10000.00"})
        self.call("poolmanager", "post", "/api/v1/circles/rules/publish/", rules, expect=201)
        members = []
        for n in (1, 2):
            m = self.call("poolmanager", "post", "/api/v1/circles/circle-members/", {
                "pool": pid, "member_name": f"Serviced Member {n}", "member_reference": f"W-{n}", "joined_date": "2026-01-15",
                "mandate_reference": f"MANDATE-{n}", "mandate_bank": "Test Bank",
                "guarantor_name": f"Guarantor {n}", "guarantor_reference": f"GUAR-{n}"}, expect=201).data["id"]
            self.call("risk", "post", f"/api/v1/circles/circle-members/{m}/verify-kyc/", {}, expect=200)
            self.call("poolmanager", "post", "/api/v1/circles/rules/accept/", {"member": m, "method": "in_person"}, expect=201)
            members.append(m)
        draw = self.call("poolmanager", "post", "/api/v1/circles/draws/commit/", {"pool": pid}, expect=201).data
        self.call("poolmanager", "post", f"/api/v1/circles/draws/{draw['id']}/execute/", {"client_seed": "w-seed"}, expect=200)
        for m in members:
            self.call("maker", "post", f"/api/v1/circles/circle-members/{m}/record-contribution/", {
                "amount": "10000.00", "contribution_date": "2026-02-01", "cycle_number": 1, "payment_reference": f"R-{m[:6]}"}, expect=[200, 201])
        rows = self.call("poolmanager", "get", f"/api/v1/circles/circle-members/?pool={pid}", expect=200).data
        rows = rows if isinstance(rows, list) else rows["results"]
        first = [r for r in rows if r["payout_position"] == 1][0]
        body = {"member_id": first["id"], "cycle_number": 1, "settlement_rail": "internal_book", "payout_date": "2026-02-02"}
        self.refused("poolmanager", "post", f"/api/v1/circles/payouts/request-payout/{pid}/", body)  # mandates not verified yet
        for m in members:
            self.refused("poolmanager", "post", f"/api/v1/circles/circle-members/{m}/verify-mandate/", {})
            self.call("checker", "post", f"/api/v1/circles/circle-members/{m}/verify-mandate/", {}, expect=200)
        req = self.call("poolmanager", "post", f"/api/v1/circles/payouts/request-payout/{pid}/", body, expect=201).data
        self.assertEqual((req["amount"], req["service_fee"]), ("19500.00", "500.00"), "pot 20,000 less only the disclosed fee")

    def phase_f_investment_pool(self):
        """An investment (unit/NAV) pool from nothing: ruling, product, pool, investor, disclosure, NAV, subscription, profit."""
        from apps.tenants.models import LegalEntity

        ruling = {"decision_code": "FATWA-I-001", "title": "Unrestricted Mudarabah investment pool", "decision_type": "product_approval",
                  "description": "Investors subscribe at published NAV; profit is shared by the approved ratio.",
                  "fiqh_reference": "AAOIFI Shariah Standard No. 13", "mandatory_caveats": "Loss is borne by investors except for negligence.",
                  "effective_date": "2026-01-01"}
        d = self.call("secretariat", "post", "/api/v1/products/shariah-decisions/", ruling, expect=201).data["id"]
        vote = {"vote": "approve", "fiqh_opinion_notes": "Compliant"}
        self.call("board", "post", f"/api/v1/products/shariah-decisions/{d}/cast-quorum-vote/", vote, expect=200)
        self.call("board2", "post", f"/api/v1/products/shariah-decisions/{d}/cast-quorum-vote/", vote, expect=200)
        ct = self.call("pm", "post", "/api/v1/products/contract-templates/", {
            "name": "Investment Mudarabah Charter", "contract_type": "mudarabah_unrestricted", "version": "1.0", "clauses": {}, "shariah_decision": d}, expect=201).data
        self.call("board", "post", f"/api/v1/products/contract-templates/{ct['id']}/approve/", expect=200)
        prod = self.call("pm", "post", "/api/v1/products/products/", {
            "name": "Growth Investment Pool", "code": "INV-1", "operating_model": "investment_pool", "contract_template": ct["id"],
            "base_currency": "PKR", "eligible_asset_types": ["murabahah"], "minimum_subscription": "1000.00"}, expect=201).data
        self.call("pm", "post", f"/api/v1/products/products/{prod['id']}/submit-for-review/", expect=200)
        self.call("board", "post", f"/api/v1/products/products/{prod['id']}/approve/", expect=200)
        entity = LegalEntity.objects.filter(tenant=self.tenant).first()
        pool = self.call("poolmanager", "post", "/api/v1/pools/pools/", {
            "name": "Growth Investment Pool 2026", "code": "INV-2026", "product": prod["id"], "effective_date": "2026-01-01",
            "legal_entity": str(entity.id), "branch": "Main Branch", "timezone": "Asia/Karachi", "calendar": "mon_fri"}, expect=201).data
        pid = pool["id"]
        ready = self.call("poolmanager", "get", f"/api/v1/pools/pools/{pid}/activation-readiness/", expect=200).data
        missing = [c["key"] for c in ready.get("checks", []) if not c["passed"]]
        psr = self.call("poolmanager", "post", "/api/v1/allocation/psr-schedules/", {
            "pool": pid, "depositor_share": "80.00", "mudarib_share": "20.00", "effective_from": "2026-01-01"}, expect=201).data
        self.call("board", "post", f"/api/v1/allocation/psr-schedules/{psr['id']}/approve/", expect=200)
        self.call("poolmanager", "post", f"/api/v1/pools/pools/{pid}/submit-for-approval/", expect=200)
        self.call("board", "post", f"/api/v1/pools/pools/{pid}/approve/", expect=200)
        self.call("checker", "post", f"/api/v1/pools/pools/{pid}/open/", expect=200)

        # Investor: capital account, profile (suitability), KYC by Risk.
        acct = self.call("poolmanager", "post", "/api/v1/investments/capital-accounts/", {
            "pool": pid, "investor_name": "Tariq Investor", "investor_reference": "INV-001"}, expect=201).data["id"]
        prof = self.call("maker", "post", "/api/v1/investments/investor-profiles/", {
            "capital_account": acct, "id_document_type": "cnic", "id_document_number": "35202-3333333-3",
            "date_of_birth": "1985-05-05", "address": "Lahore", "risk_tolerance": "moderate",
            "suitability_assessment_notes": "Understands capital is at risk"}, expect=201).data["id"]
        self.refused("maker", "post", f"/api/v1/investments/investor-profiles/{prof}/verify-kyc/", {"kyc_status": "verified"})
        self.call("risk", "post", f"/api/v1/investments/investor-profiles/{prof}/verify-kyc/", {"kyc_status": "verified"}, expect=200)

        # No subscription before the disclosure is prepared, validated by someone else, and acknowledged.
        self.refused("maker", "post", f"/api/v1/investments/capital-accounts/{acct}/subscribe/", {"amount": "100000.00", "transaction_date": "2026-02-02"})
        disc = self.call("poolmanager", "post", "/api/v1/investments/disclosures/publish/", {
            "pool": pid, "risk_warnings": "Capital is at risk; returns are not guaranteed.", "fee_statement": "Fees are the stated profit share only.",
            "summary": "Unrestricted Mudarabah pool"}, expect=201).data
        self.refused("poolmanager", "post", f"/api/v1/investments/disclosures/{disc['id']}/approve/")
        self.call("risk", "post", f"/api/v1/investments/disclosures/{disc['id']}/approve/", expect=200)
        self.call("maker", "post", f"/api/v1/investments/disclosures/{disc['id']}/acknowledge/", {
            "capital_account": acct, "method": "in_person", "evidence_reference": "FORM-1", "risk_acknowledged": True}, expect=201)

        # NAV: the maker proposes the pool value, a different checker publishes it.
        # The first NAV of an empty pool is a launch price (nothing to divide by yet); without it the request is refused.
        self.refused("maker", "post", "/api/v1/investments/nav-snapshots/", {"pool": pid, "valuation_date": "2026-02-01", "total_pool_value": "0.00"})
        nav = self.call("maker", "post", "/api/v1/investments/nav-snapshots/", {
            "pool": pid, "valuation_date": "2026-02-01", "total_pool_value": "0.00", "launch_nav_per_unit": "10.00"}, expect=201).data
        self.refused("maker", "post", f"/api/v1/investments/nav-snapshots/{nav['id']}/publish/")
        self.call("checker", "post", f"/api/v1/investments/nav-snapshots/{nav['id']}/publish/", expect=200)
        sub = self.call("maker", "post", f"/api/v1/investments/capital-accounts/{acct}/subscribe/", {"amount": "100000.00", "transaction_date": "2026-02-02"}, expect=[200, 201]).data
        # Month end: the maker records pool income, the next NAV reflects it, and the profit is shared by the 4-person ceremony.
        ev = self.call("maker", "post", "/api/v1/accounting/income-expense-events/", {
            "pool": pid, "event_type": "income", "category": "Financing Profit", "amount": "5000.00",
            "event_date": "2026-02-20", "description": "Murabaha profit"}, expect=201).data
        self.call("checker", "post", f"/api/v1/accounting/income-expense-events/{ev['id']}/post/", expect=200)
        nav2 = self.call("maker", "post", "/api/v1/investments/nav-snapshots/", {"pool": pid, "valuation_date": "2026-02-28", "total_pool_value": "105000.00"}, expect=201).data
        self.call("checker", "post", f"/api/v1/investments/nav-snapshots/{nav2['id']}/publish/", expect=200)
        body = {"pool": pid, "period_start": "2026-02-01", "period_end": "2026-02-28", "gross_income": "5000.00", "direct_expenses": "0.00"}
        run = self.call("maker", "post", "/api/v1/investments/distribution-runs/", body, expect=201).data
        base = f"/api/v1/investments/distribution-runs/{run['id']}"
        self.call("maker", "post", f"{base}/submit-for-checking/", expect=200)
        self.refused("maker", "post", f"{base}/check/")
        self.call("checker", "post", f"{base}/check/", expect=200)
        self.refused("signatory", "post", f"{base}/approve/")
        self.call("secretariat", "post", f"{base}/shariah-sign-off/", {"note": "Reviewed"}, expect=200)
        self.call("signatory", "post", f"{base}/approve/", expect=200)

        # Redemption: the investor's units go back at the published NAV; a different finance checker approves.
        red = self.call("maker", "post", f"/api/v1/investments/capital-accounts/{acct}/redeem/", {
            "units_redeemed": "1000.000000", "transaction_date": "2026-03-02"}, expect=[200, 201]).data
        self.refused("maker", "post", f"/api/v1/investments/redemptions/{red['id']}/approve/")
        self.call("checker", "post", f"/api/v1/investments/redemptions/{red['id']}/approve/", expect=200)
        return pid, acct, missing

    def phase_g_ledger_and_close(self, pid):
        """After the run: hand the journals to the GL, check the trial balance, park a difference, close the period."""
        base = "/api/v1/accounting"
        pending = self.call("maker", "get", f"{base}/gl-exports/pending-batches/?pool={pid}", expect=200).data
        self.assertGreaterEqual(pending["pending_batches"], 1, "the signed run's journal is waiting to go to the GL")
        self.refused("checker", "post", f"{base}/gl-exports/", {"pool": pid})
        export = self.call("maker", "post", f"{base}/gl-exports/", {"pool": pid}, expect=201).data
        self.refused("maker", "post", f"{base}/gl-exports/{export['id']}/confirm/", {"gl_reference": "GL-001"})
        self.call("checker", "post", f"{base}/gl-exports/{export['id']}/confirm/", {"gl_reference": "GL-001"}, expect=200)
        tb = self.call("checker", "get", f"{base}/trial-balance/?pool={pid}", expect=200).data
        self.assertTrue(tb.get("balanced", True), tb)

        item = self.call("maker", "post", f"{base}/suspense-items/", {
            "pool": pid, "side": "unidentified_receipt", "amount": "150.00", "description": "Unmatched bank receipt", "reference": "BANK-77"}, expect=201).data
        self.refused("maker", "post", f"{base}/suspense-items/{item['id']}/approve/")
        self.call("checker", "post", f"{base}/suspense-items/{item['id']}/approve/", expect=200)

        pc = self.call("poolmanager", "post", "/api/v1/pools/period-closes/", {"pool": pid, "period_start": "2026-01-01", "period_end": "2026-01-31"}, expect=201).data
        gates = self.call("checker", "post", f"/api/v1/pools/period-closes/{pc['id']}/auto-verify-gates/", expect=200).data
        sign = f"/api/v1/pools/period-closes/{pc['id']}/sign-off-role/"
        self.refused("checker", "post", sign, {"role": "cfo_checker"})  # the pool manager signs first
        self.call("poolmanager", "post", sign, {"role": "pool_manager", "notes": "Checked"}, expect=200)
        self.refused("poolmanager", "post", sign, {"role": "shariah_reviewer", "fatwa_ref": "FATWA-T-001"})  # wrong role
        self.refused("secretariat", "post", sign, {"role": "shariah_reviewer"})  # the ruling must be cited
        self.call("secretariat", "post", sign, {"role": "shariah_reviewer", "fatwa_ref": "FATWA-T-001", "notes": "Reviewed"}, expect=200)
        self.call("checker", "post", sign, {"role": "cfo_checker", "notes": "Figures agree"}, expect=200)
        self.call("signatory", "post", f"/api/v1/pools/period-closes/{pc['id']}/lock-ceremony/", {"lock_note": "January closed"}, expect=200)
        # A back-dated event in the closed period is refused: it needs a restatement.
        self.refused("maker", "post", "/api/v1/accounting/income-expense-events/", {
            "pool": pid, "event_type": "income", "category": "Financing Profit", "amount": "10.00", "event_date": "2026-01-10", "description": "late"})
        # BRD 7.3: asked for explicitly, the same late item enters the adjustment period (today), keeping its real date.
        from django.utils import timezone

        late = self.call("maker", "post", "/api/v1/accounting/income-expense-events/", {
            "pool": pid, "event_type": "income", "category": "Financing Profit", "amount": "10.00", "event_date": "2026-01-10",
            "description": "late", "book_in_adjustment_period": True}, expect=201).data
        self.assertEqual((late["event_date"], late["adjusted_from_date"]), (str(timezone.localdate()), "2026-01-10"))
        self.refused("maker", "post", "/api/v1/accounting/income-expense-events/", {
            "pool": pid, "event_type": "income", "category": "Financing Profit", "amount": "10.00", "event_date": "2026-03-10",
            "description": "not closed", "book_in_adjustment_period": True})
        return gates

    def test_full_lifecycle(self):
        self.phase_a_foundation()
        self.pool_id = self.phase_b_product_and_pool()
        self.people = self.phase_c_bank_pool_operations(self.pool_id)
        self.run_id = self.phase_d_profit_run(self.pool_id, self.people)
        self.gates = self.phase_g_ledger_and_close(self.pool_id)
        self.circle = self.phase_e_community_circle()
        self.investment = self.phase_f_investment_pool()
        self.phase_e2_wakalah_circle()
