from datetime import date

from django.urls import reverse

from apps.accounts.models import UserRole
from apps.allocation.test_participant_ledger import END, START, ParticipantLedgerTestBase

from .models import PeriodCloseChecklist

BASE = "/api/v1/pools/period-closes/"


class PeriodCloseWorkflowTests(ParticipantLedgerTestBase):
    def setUp(self):
        super().setUp()
        product = self.pool.product
        product.operating_model = "bank_pool"
        product.save()
        self.board = self._user("board", UserRole.SHARIAH_BOARD)

    def post(self, user, path, body=None):
        self.authenticate(user)
        return self.client.post(f"{BASE}{path}", body or {}, format="json")

    def open_period(self):
        response = self.post(self.pool_manager, "", {
            "pool": str(self.pool.id), "period_start": str(START), "period_end": str(END), "status": "locked",
        })
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def sign(self, close_id, user, role, **extra):
        return self.post(user, f"{close_id}/sign-off-role/", {"role": role, **extra})

    def test_status_and_gates_cannot_be_written_by_a_client(self):
        close_id = self.open_period()
        self.assertEqual(PeriodCloseChecklist._base_manager.get(pk=close_id).status, "open")  # "locked" ignored
        self.authenticate(self.pool_manager)
        self.assertEqual(self.client.patch(f"{BASE}{close_id}/", {"status": "locked"}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(f"{BASE}{close_id}/").status_code, 405)
        self.assertEqual(self.post(self.checker, f"{close_id}/certify/").status_code, 400)

    def test_gates_come_from_the_records(self):
        close_id = self.open_period()
        result = self.post(self.pool_manager, f"{close_id}/auto-verify-gates/").data
        self.assertFalse(result["all_passed"])
        self.assertFalse(result["gates"]["allocation_signed"]["passed"])
        self.assertFalse(result["gates"]["journals_posted"]["passed"])
        self.assertTrue(result["gates"]["reconciled"]["passed"])
        # No sign-off while a gate fails.
        self.assertEqual(self.sign(close_id, self.pool_manager, "pool_manager").status_code, 400)

        self.sign_run()
        result = self.post(self.pool_manager, f"{close_id}/auto-verify-gates/").data
        self.assertTrue(result["all_passed"], result["gates"])

    def test_three_different_people_in_their_own_roles_then_lock(self):
        close_id = self.open_period()
        self.sign_run()
        # Roles are bound: a finance checker cannot sign as the Shariah reviewer.
        self.assertEqual(self.sign(close_id, self.checker, "shariah_reviewer", fatwa_ref="SD-1").status_code, 403)
        # The pool manager signs first.
        self.assertEqual(self.sign(close_id, self.checker, "cfo_checker").status_code, 400)
        self.assertEqual(self.sign(close_id, self.pool_manager, "pool_manager").status_code, 200)
        self.assertEqual(self.sign(close_id, self.secretariat, "shariah_reviewer").status_code, 400)  # needs ruling ref
        self.assertEqual(self.sign(close_id, self.secretariat, "shariah_reviewer", fatwa_ref="SD-1").status_code, 200)
        # Locking needs certification first.
        self.assertEqual(self.post(self.checker, f"{close_id}/lock-ceremony/").status_code, 400)
        certified = self.sign(close_id, self.checker, "cfo_checker")
        self.assertEqual(certified.data["status"], "certified")
        # Only a finance checker / signatory locks.
        self.assertEqual(self.post(self.pool_manager, f"{close_id}/lock-ceremony/").status_code, 403)
        locked = self.post(self.signatory, f"{close_id}/lock-ceremony/", {"lock_note": "September closed"})
        self.assertEqual(locked.status_code, 200, locked.data)
        self.assertEqual(len(locked.data["cryptographic_seal"]), 64)
        self.authenticate(self.checker)
        package = self.client.get(f"{BASE}{close_id}/filing-package/").data
        self.assertEqual(set(package["signatories"]), {"pool_manager", "shariah_reviewer", "cfo_checker"})
        self.assertIn("not a regulatory filing", package["statement"])

        # The locked period now refuses new runs for its dates.
        self.authenticate(self.maker)
        rerun = self.client.post(
            reverse("allocation-run-list"),
            {"pool": str(self.pool.id), "period_start": str(START), "value_date": str(END),
             "gross_income": "600.00", "direct_expenses": "0.00", "override_reason": "x"},
            format="json",
        )
        self.assertEqual(rerun.status_code, 400)

    def test_the_same_person_cannot_sign_twice(self):
        close_id = self.open_period()
        self.sign_run()
        self.assertEqual(self.sign(close_id, self.pool_manager, "pool_manager").status_code, 200)
        self.assertEqual(self.sign(close_id, self.pool_manager, "pool_manager").status_code, 400)

    def test_overlapping_close_records_are_refused(self):
        self.open_period()
        response = self.post(self.pool_manager, "", {
            "pool": str(self.pool.id), "period_start": str(date(2026, 9, 5)), "period_end": str(date(2026, 9, 20)),
        })
        self.assertEqual(response.status_code, 400)
