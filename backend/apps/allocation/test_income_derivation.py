"""BR-005: allocation income/expenses come from posted ledger events; non-permissible income never reaches participants."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from rest_framework import status

from apps.accounting.models import IncomeExpenseEvent
from apps.governance.models import PurificationEntry

from .ceremony_helpers import complete_ceremony
from .models import AllocationRun, AllocationRunStatus
from .test_participant_ledger import END, START, ParticipantLedgerTestBase

EVENTS_URL = "/api/v1/accounting/income-expense-events/"


class IncomeDerivationBase(ParticipantLedgerTestBase):
    def event(self, event_type, category, amount, day, description, post=True):
        self.authenticate(self.maker)
        response = self.client.post(
            EVENTS_URL,
            {"pool": str(self.pool.id), "event_type": event_type, "category": category, "amount": amount,
             "event_date": day, "description": description},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        if post:
            self.authenticate(self.checker)
            posted = self.client.post(f"{EVENTS_URL}{response.data['id']}/post/")
            self.assertEqual(posted.status_code, status.HTTP_200_OK, posted.data)
        return response.data["id"]

    def standard_events(self):
        self.event("income", "Financing Profit", "1000.00", "2026-09-03", "Sukuk rental")
        self.event("income", "Financing Profit", "500.00", "2026-09-08", "Murabaha profit")
        self.event("income", "Penalty income", "40.00", "2026-09-04", "Late payment penalty")
        self.event("expense", "Direct Takaful", "100.00", "2026-09-05", "Takaful premium")
        self.event("expense", "Overhead", "60.00", "2026-09-06", "Branch rent")

    def run_payload(self, **extra):
        return {"pool": str(self.pool.id), "period_start": str(START), "value_date": str(END), **extra}

    def create(self, **extra):
        self.authenticate(self.maker)
        return self.client.post(reverse("allocation-run-list"), self.run_payload(**extra), format="json")

    def submit_and_approve(self, run_id):
        self.authenticate(self.maker)
        base = reverse("allocation-run-detail", args=[run_id])
        self.client.post(base + "submit-for-checking/")
        return complete_ceremony(self, run_id)


class DerivedFromEventsTests(IncomeDerivationBase):
    def test_run_figures_come_from_posted_events_and_exclude_non_permissible_and_overhead(self):
        self.standard_events()
        response = self.create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.data
        self.assertEqual(Decimal(data["gross_income"]), Decimal("1500.00"))  # penalty income excluded
        self.assertEqual(Decimal(data["direct_expenses"]), Decimal("100.00"))  # branch rent is bank overhead
        self.assertEqual(Decimal(data["distributable_amount"]), Decimal("1400.00"))

        source = data["config_snapshot"]["income_source"]
        self.assertEqual(source["mode"], "derived_from_events")
        self.assertEqual(source["event_count"], 5)  # all five are consumed; two are excluded from the totals
        self.assertEqual(source["excluded_non_permissible_income"], "40.00")
        self.assertEqual(source["excluded_bank_absorbed_overhead"], "60.00")

    def test_non_permissible_income_is_routed_to_purification_when_posted(self):
        self.standard_events()
        entry = PurificationEntry.objects.get()
        self.assertEqual(entry.amount, Decimal("40.00"))
        self.assertEqual(entry.status, "identified")
        self.assertEqual(entry.income_event.category, "Penalty income")

    def test_sealed_hash_covers_the_event_set(self):
        self.standard_events()
        run_id = self.create().data["id"]
        run = AllocationRun.objects.get(pk=run_id)
        self.assertEqual(len(run.config_snapshot["income_source"]["event_ids"]), 5)
        self.assertEqual(self.submit_and_approve(run_id).status_code, status.HTTP_200_OK)

    def test_without_events_or_an_override_the_run_is_refused(self):
        response = self.create()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No posted income/expense events", str(response.data))

    def test_pending_events_block_a_run_but_not_a_simulation(self):
        self.standard_events()
        self.event("income", "Financing Profit", "10.00", "2026-09-09", "Not yet posted", post=False)
        self.assertEqual(self.create().status_code, status.HTTP_400_BAD_REQUEST)

        self.authenticate(self.maker)
        simulated = self.client.post(reverse("allocation-run-simulate"), self.run_payload(), format="json")
        self.assertEqual(simulated.status_code, status.HTTP_200_OK, simulated.data)
        self.assertEqual(len(simulated.data["warnings"]), 1)
        self.assertEqual(Decimal(simulated.data["gross_income"]), Decimal("1500.00"))

    def test_events_outside_the_period_are_ignored(self):
        self.standard_events()
        self.event("income", "Financing Profit", "9999.00", "2026-10-02", "Next period")
        self.assertEqual(Decimal(self.create().data["gross_income"]), Decimal("1500.00"))


class ManualOverrideTests(IncomeDerivationBase):
    def test_hand_typed_income_needs_a_reason_and_seals_it(self):
        self.assertEqual(self.create(gross_income="777.00").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.create(gross_income="777.00", override_reason="   ").status_code, status.HTTP_400_BAD_REQUEST
        )
        response = self.create(gross_income="777.00", override_reason="CBS feed outage; figure from GL")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        source = response.data["config_snapshot"]["income_source"]
        self.assertEqual(source["mode"], "manual_override")
        self.assertEqual(source["reason"], "CBS feed outage; figure from GL")

    def test_expenses_without_gross_income_is_rejected(self):
        self.standard_events()
        self.assertEqual(self.create(direct_expenses="5.00").status_code, status.HTTP_400_BAD_REQUEST)

    def test_override_records_what_the_ledger_said(self):
        self.standard_events()
        response = self.create(gross_income="2000.00", override_reason="Includes accrual not yet booked")
        self.assertEqual(response.data["config_snapshot"]["income_source"]["derived_gross_income"], "1500.00")


class ConsumptionTests(IncomeDerivationBase):
    def test_signing_consumes_the_events_and_they_cannot_feed_another_run(self):
        self.standard_events()
        run_id = self.create().data["id"]
        self.assertEqual(self.submit_and_approve(run_id).status_code, status.HTTP_200_OK)
        consumed = IncomeExpenseEvent.objects.filter(allocation_run_id=run_id)
        self.assertEqual(consumed.count(), 5)  # incl. the purified penalty and the absorbed overhead: none can be reused

        again = self.create()
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)

    def test_late_posted_event_blocks_approval_of_a_stale_run(self):
        self.standard_events()
        run_id = self.create().data["id"]
        self.event("income", "Financing Profit", "25.00", "2026-09-09", "Posted after the run was calculated")
        response = self.submit_and_approve(run_id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The independent check passed, but the final release refuses a run whose events changed.
        self.assertEqual(AllocationRun.objects.get(pk=run_id).status, AllocationRunStatus.CHECKED)

    def test_two_competing_runs_only_the_first_can_be_signed(self):
        self.standard_events()
        first = self.create().data["id"]
        second = self.create().data["id"]
        self.assertEqual(self.submit_and_approve(first).status_code, status.HTTP_200_OK)
        self.assertEqual(self.submit_and_approve(second).status_code, status.HTTP_400_BAD_REQUEST)

    def test_restatement_rederives_the_period_and_relinks_events(self):
        self.standard_events()
        run_id = self.create().data["id"]
        self.submit_and_approve(run_id)
        self.event("income", "Financing Profit", "200.00", "2026-09-10", "Late accrual")

        self.authenticate(self.maker)
        base = reverse("allocation-run-detail", args=[run_id])
        restated = self.client.post(base + "restate/", {"restatement_reason": "Late accrual"}, format="json")
        self.assertEqual(restated.status_code, status.HTTP_201_CREATED, restated.data)
        self.assertEqual(Decimal(restated.data["gross_income"]), Decimal("1700.00"))  # 1500 + the late 200

        new_id = restated.data["id"]
        self.assertEqual(self.submit_and_approve(new_id).status_code, status.HTTP_200_OK)
        self.assertEqual(AllocationRun.objects.get(pk=run_id).status, AllocationRunStatus.REVERSED)
        self.assertEqual(IncomeExpenseEvent.objects.filter(allocation_run_id=new_id).count(), 6)
        self.assertEqual(IncomeExpenseEvent.objects.filter(allocation_run_id=run_id).count(), 0)


class EventIntegrityTests(IncomeDerivationBase):
    def test_posted_events_are_immutable(self):
        event_id = self.event("income", "Financing Profit", "10.00", "2026-09-03", "x")
        event = IncomeExpenseEvent.objects.get(pk=event_id)
        event.amount = Decimal("99999.00")
        with self.assertRaises(DjangoValidationError):
            event.save()
        with self.assertRaises(DjangoValidationError):
            event.save(update_fields=["amount"])

    def test_events_cannot_be_patched_or_deleted_through_the_api(self):
        event_id = self.event("income", "Financing Profit", "10.00", "2026-09-03", "x")
        self.authenticate(self.maker)
        self.assertEqual(
            self.client.patch(f"{EVENTS_URL}{event_id}/", {"amount": "1.00"}, format="json").status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(self.client.delete(f"{EVENTS_URL}{event_id}/").status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_creator_cannot_post_their_own_event(self):
        event_id = self.event("income", "Financing Profit", "10.00", "2026-09-03", "x", post=False)
        IncomeExpenseEvent.objects.filter(pk=event_id).update(created_by=self.checker)
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(f"{EVENTS_URL}{event_id}/post/").status_code, status.HTTP_400_BAD_REQUEST)

    def test_events_are_blocked_in_a_closed_period(self):
        from apps.pools.models import PeriodCloseChecklist

        PeriodCloseChecklist.objects.create(
            tenant=self.tenant, pool=self.pool, period_start=date(2026, 9, 1), period_end=date(2026, 9, 30),
            status="locked",
        )
        self.authenticate(self.maker)
        response = self.client.post(
            EVENTS_URL,
            {"pool": str(self.pool.id), "event_type": "income", "category": "Financing Profit", "amount": "5.00",
             "event_date": "2026-09-03", "description": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
