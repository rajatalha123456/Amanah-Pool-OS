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

        from apps.products.models import ShariahDecision, ShariahDecisionStatus

        decision = ShariahDecision.objects.create(
            tenant=self.tenant, decision_code="SD-PAYOUT", title="d", description="d",
            status=ShariahDecisionStatus.APPROVED, effective_date=date(2026, 1, 1),
        )
        template = self.pool.product.contract_template
        template.shariah_decision = decision
        template.save()
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
