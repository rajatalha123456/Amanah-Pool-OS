from decimal import Decimal

from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from apps.accounting.models import JournalBatch
from apps.participants.seed_ledger import make_pk_iban

from .models import PayoutBatchRecord
from .test_participant_ledger import ParticipantLedgerTestBase

BASE = "/api/v1/allocation/payout-clearing/"


class PayoutClearingTests(ParticipantLedgerTestBase):
    def setUp(self):
        super().setUp()
        for index, participant in enumerate((self.ali, self.bano), start=1):
            participant.iban = make_pk_iban("MEZN", f"{index * 1111111:016d}")
            participant.bank_name = "Meezan Bank Ltd"
            participant.bic = "MEZNPKKA"
            participant.tax_status = "filer"
            participant.save()
        # The pool's contract needs an approved Shariah decision for gate 1.
        from datetime import date

        from apps.products.models import JurisdictionRulePack, ShariahDecision, ShariahDecisionStatus

        decision = ShariahDecision.objects.create(
            tenant=self.tenant, decision_code="SD-PAYOUT", title="d", description="d",
            status=ShariahDecisionStatus.APPROVED, effective_date=date(2026, 1, 1),
        )
        template = self.pool.product.contract_template
        template.shariah_decision = decision
        template.save()
        self.pack = JurisdictionRulePack.objects.create(
            tenant=self.tenant, code="PK-PAYOUT", name="Payout test pack", effective_date=date(2026, 1, 1),
            is_default=True,
            rules_config={"wht_filer_pct": 15.0, "wht_non_filer_pct": 30.0, "per_ceiling_pct": 2.0},
        )
        self.run_id = self.sign_run()

    def get(self, path, user=None, **params):
        self.authenticate(user or self.checker)
        return self.client.get(BASE + path, params)

    def post(self, path, payload=None, user=None):
        self.authenticate(user or self.checker)
        return self.client.post(BASE + path, payload or {}, format="json")

    def batch(self, user=None):
        return self.get("batch-detail/", user, allocation_run=self.run_id)

    def test_batch_is_built_from_real_participants_and_persisted(self):
        response = self.batch()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        batch = response.data
        self.assertEqual(batch["mode"], "SIMULATION")
        names = sorted(t["beneficiary_name"] for t in batch["transactions"])
        self.assertEqual(names, ["Ali Khan", "Ali Khan", "Bano Bibi"])  # one payment per account
        self.assertEqual(batch["maker_email"], self.maker.email)  # the run's creator, not a hardcoded demo user

        record = PayoutBatchRecord.objects.get(allocation_run_id=self.run_id)
        self.assertEqual(record.payload["batch_id"], batch["batch_id"])
        # Stable across requests - not regenerated each time.
        self.assertEqual(self.batch().data["batch_id"], batch["batch_id"])

    def test_unsigned_runs_have_no_batch(self):
        unsigned_id = self.create_run(gross="10.00")  # simulated only; never approved
        listing = self.get("")
        self.assertEqual([b["allocation_run_id"] for b in listing.data["batches"]], [self.run_id])
        refused = self.get("batch-detail/", allocation_run=unsigned_id)
        self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST)

    def test_liquidity_gate_fails_without_a_configured_balance(self):
        with override_settings(PAYOUT_SETTLEMENT_ACCOUNT_BALANCE=None):
            gates = self.post("verify-gates/", {"allocation_run": self.run_id}, user=self.maker).data
        self.assertFalse(gates["gates_verified"])
        self.assertFalse(gates["gate_results"]["gate_4_settlement_liquidity"]["passed"])

    def test_full_flow_with_dual_control(self):
        payload = {"allocation_run": self.run_id}
        with override_settings(PAYOUT_SETTLEMENT_ACCOUNT_BALANCE=Decimal("1000000000")):
            gates = self.post("verify-gates/", payload, user=self.maker).data
        self.assertTrue(gates["gates_verified"], gates["gate_results"])
        self.assertEqual(gates["status"], "validated")

        # Only the Finance Checker authorises / dispatches.
        self.assertEqual(self.post("authorize/", payload, user=self.maker).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.post("dispatch-simulate/", payload).status_code, status.HTTP_400_BAD_REQUEST)  # not authorised yet

        authorised = self.post("authorize/", payload)
        self.assertEqual(authorised.status_code, status.HTTP_200_OK, authorised.data)
        self.assertEqual(authorised.data["checker_email"], self.checker.email)

        # No regeneration once authorised.
        regenerate = self.get("batch-detail/", allocation_run=self.run_id, force_regenerate="true")
        self.assertEqual(regenerate.status_code, status.HTTP_400_BAD_REQUEST)

        dispatched = self.post("dispatch-simulate/", payload)
        self.assertEqual(dispatched.status_code, status.HTTP_200_OK)
        self.assertEqual(dispatched.data["status"], "settled")
        self.assertEqual(dispatched.data["mode"], "SIMULATION")
        self.assertEqual(self.post("dispatch-simulate/", payload).status_code, status.HTTP_400_BAD_REQUEST)

        posted = self.post("post-contra-gl/", payload)
        self.assertEqual(posted.status_code, status.HTTP_200_OK, posted.data)
        voucher = JournalBatch.objects.get(pk=posted.data["journal_batch_id"])
        self.assertEqual(voucher.total_debit, voucher.total_credit)
        debits = {e.account_name for e in voucher.entries.filter(entry_type="debit")}
        self.assertEqual(debits, {"Depositor Payable - retail", "Depositor Payable - premium"})
        self.assertEqual(self.post("post-contra-gl/", payload).status_code, status.HTTP_400_BAD_REQUEST)

        # State survived: a fresh load returns the persisted, settled batch.
        self.assertEqual(self.batch().data["status"], "settled")

    def test_maker_cannot_authorize_own_batch(self):
        payload = {"allocation_run": self.run_id}
        with override_settings(PAYOUT_SETTLEMENT_ACCOUNT_BALANCE=Decimal("1000000000")):
            self.post("verify-gates/", payload, user=self.maker)
        PayoutBatchRecord.objects.filter(allocation_run_id=self.run_id).update(
            payload={**PayoutBatchRecord.objects.get(allocation_run_id=self.run_id).payload, "maker_email": self.checker.email}
        )
        response = self.post("authorize/", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_investors_cannot_read_batches(self):
        self.authenticate(self.investor_b)
        self.assertEqual(self.client.get(BASE).status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_run_is_a_400_not_a_crash(self):
        response = self.get("batch-detail/", allocation_run="00000000-0000-0000-0000-000000000000")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_withholding_rates_come_from_the_rule_pack(self):
        self.pack.rules_config = {**self.pack.rules_config, "wht_filer_pct": 10.0}
        self.pack.save()
        response = self.batch()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(all(t["wht_rate_pct"] == 10.0 for t in response.data["transactions"]))
        self.assertTrue(all(t["zakat_amount"] == 0 for t in response.data["transactions"]))  # not enabled in the pack

    def test_batch_is_refused_when_the_pack_has_no_withholding_rates(self):
        self.pack.rules_config = {}
        self.pack.save()
        self.assertGreaterEqual(self.batch().status_code, 400)

    def test_reserve_cap_above_the_rule_pack_ceiling_is_refused(self):
        self.authenticate(self.pool_manager)
        url = reverse("reserve-policy-list")
        body = {"pool": str(self.pool.id), "reserve_type": "per", "rate_percentage": "1.00", "is_active": False}
        self.assertEqual(self.client.post(url, {**body, "cap_percentage": "5.00"}, format="json").status_code, 400)
        self.assertLess(self.client.post(url, {**body, "cap_percentage": "2.00"}, format="json").status_code, 400)

    @override_settings(ALLOW_SIMULATED_INTEGRATIONS=False)
    def test_simulated_rails_are_refused_when_disabled(self):
        for user, url, body in (
            (self.checker, BASE + "dispatch-simulate/", {"allocation_run": self.run_id}),
            (self.checker, "/api/v1/banking/settle/", {
                "amount": "100", "source_title": "A", "source_iban": "X", "destination_title": "B", "destination_iban": "Y",
            }),
            (self.maker, "/api/v1/pools/balance-imports/cbs-sftp-daemon/", {"pool_id": str(self.pool.id)}),
        ):
            with self.subTest(url=url):
                self.authenticate(user)
                self.assertEqual(self.client.post(url, body, format="json").status_code, 409)


    def test_an_investor_gets_tax_support_for_their_own_payments_only(self):
        # CNICs are needed to match a payment line to its participant.
        from apps.participants.models import Participant

        Participant.objects.filter(pk=self.ali.pk).update(cnic_ntn="42101-1111111-1")
        Participant.objects.filter(pk=self.bano.pk).update(cnic_ntn="42101-2222222-2")
        self.assertEqual(self.batch().status_code, status.HTTP_200_OK)  # builds and stores the payout batch

        self.authenticate(self.investor_a)
        response = self.client.get("/api/v1/participants/my-tax-support/")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.data
        self.assertEqual(data["participant"], "P-ALI")
        self.assertEqual(len(data["rows"]), 2)  # Ali holds two accounts in the pool
        self.assertTrue(all(row["wht_rate_pct"] == 15.0 for row in data["rows"]))  # the filer rate from the rule pack
        gross = sum(float(r["gross_profit"]) for r in data["rows"])
        wht = sum(float(r["wht_amount"]) for r in data["rows"])
        self.assertAlmostEqual(wht, gross * 0.15, places=1)
        self.assertEqual(float(data["totals"]["wht_amount"]), round(wht, 2))
        self.assertNotIn("Bano", str(data))

        self.authenticate(self.maker)
        self.assertEqual(self.client.get("/api/v1/participants/my-tax-support/").status_code, 403)
