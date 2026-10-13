from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.pools.models import DailyBalance, Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .models import AllocationRun, PSRStatus, ProfitSharingRatio, WeightageBand, WeightageBandStatus


class ApprovalCeremonyApiTests(APITestCase):
    """UI Catalogue screen 14: prepared -> independent check -> Shariah review -> final release."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Ceremony Tenant", code="CEREMONY", data_residency="PK")
        set_current_tenant(self.tenant)
        original_request = self.client.request

        def request_keeping_tenant(**kwargs):
            try:
                return original_request(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = request_keeping_tenant

        def user(name, role):
            return User.objects.create_user(
                email=f"{name}@ceremony.example.com", password="password", full_name=name.title(),
                role=role, tenant=self.tenant,
            )

        self.maker = user("maker", UserRole.FINANCE_MAKER)
        self.checker = user("checker", UserRole.FINANCE_CHECKER)
        self.secretariat = user("secretariat", UserRole.SHARIAH_SECRETARIAT)
        self.board = user("board", UserRole.SHARIAH_BOARD)
        self.signatory = user("signatory", UserRole.AUTHORIZED_SIGNATORY)

    def tearDown(self):
        set_current_tenant(None)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    def _make_pool(self, operating_model, code_suffix):
        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name=f"Contract {code_suffix}", contract_type="mudarabah_unrestricted",
            version="1", clauses={},
        )
        product = Product.objects.create(
            tenant=self.tenant, name=f"Product {code_suffix}", code=f"PRODUCT-{code_suffix}",
            operating_model=operating_model, contract_template=contract,
        )
        pool = Pool.objects.create(
            tenant=self.tenant, name=f"Pool {code_suffix}", code=f"POOL-{code_suffix}", product=product,
            effective_date=date(2026, 1, 1),
        )
        value_date = date(2026, 9, 15)
        DailyBalance.objects.create(
            tenant=self.tenant, pool=pool, participant_class="retail", value_date=value_date,
            balance_amount=Decimal("1000.00"), status="validated",
        )
        # The day carries a signed daily close (the real workflow is exercised in pools/test_daily_close.py).
        from apps.pools.models import DailyClose

        DailyClose.objects.create(tenant=self.tenant, pool=pool, value_date=value_date, status="signed", gates=[])
        WeightageBand.objects.create(
            tenant=self.tenant, pool=pool, participant_class="retail", weightage=Decimal("1.00"),
            effective_from=date(2026, 1, 1), status=WeightageBandStatus.APPROVED,
        )
        ProfitSharingRatio.objects.create(
            tenant=self.tenant, pool=pool, depositor_share=Decimal("70.00"), mudarib_share=Decimal("30.00"),
            effective_from=date(2026, 1, 1), status=PSRStatus.APPROVED,
        )
        return pool, value_date

    def _prepared_run(self, operating_model, code):
        """A run created and submitted by the maker; returns its detail URL."""
        pool, value_date = self._make_pool(operating_model, code)
        self.authenticate(self.maker)
        response = self.client.post(
            reverse("allocation-run-list"),
            {"pool": str(pool.id), "value_date": str(value_date), "gross_income": "100.00",
             "override_reason": "test fixture"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        url = reverse("allocation-run-detail", args=[response.data["id"]])
        self.assertEqual(self.client.post(url + "submit-for-checking/").status_code, status.HTTP_200_OK)
        return url

    def post(self, user, url, payload=None):
        self.authenticate(user)
        return self.client.post(url, payload or {}, format="json")

    def states(self, url):
        self.authenticate(self.maker)
        return {s["key"]: s["state"] for s in self.client.get(url).data["stages"]}

    def test_bank_pool_runs_through_all_four_stages_in_order(self):
        url = self._prepared_run("bank_pool", "BANK")
        self.assertEqual(
            self.states(url),
            {"prepared": "completed", "independent_check": "in_review", "shariah_review": "waiting", "final_release": "waiting"},
        )

        # Nothing can be skipped.
        self.assertEqual(self.post(self.secretariat, url + "shariah-sign-off/").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.post(self.signatory, url + "approve/").status_code, status.HTTP_400_BAD_REQUEST)

        # Only the Finance Checker does the independent check.
        for wrong in (self.maker, self.secretariat, self.signatory):
            self.assertEqual(self.post(wrong, url + "check/").status_code, status.HTTP_403_FORBIDDEN)
        checked = self.post(self.checker, url + "check/")
        self.assertEqual(checked.status_code, status.HTTP_200_OK, checked.data)
        self.assertEqual(checked.data["status"], "checked")
        self.assertEqual(
            self.states(url),
            {"prepared": "completed", "independent_check": "completed", "shariah_review": "in_review", "final_release": "waiting"},
        )

        # Release is still blocked until the Shariah review is done.
        self.assertEqual(self.post(self.signatory, url + "approve/").status_code, status.HTTP_400_BAD_REQUEST)

        # Shariah review: Secretariat or Board; nobody else.
        for wrong in (self.maker, self.checker, self.signatory):
            self.assertEqual(self.post(wrong, url + "shariah-sign-off/").status_code, status.HTTP_403_FORBIDDEN)
        reviewed = self.post(self.secretariat, url + "shariah-sign-off/", {"note": "Reviewed against approved PSR."})
        self.assertEqual(reviewed.status_code, status.HTTP_200_OK, reviewed.data)
        self.assertEqual(reviewed.data["status"], "shariah_review")
        self.assertEqual(reviewed.data["shariah_review_note"], "Reviewed against approved PSR.")

        # Final release: only the Authorized Signatory - not the checker, not the Shariah reviewer.
        for wrong in (self.maker, self.checker, self.secretariat, self.board):
            self.assertEqual(self.post(wrong, url + "approve/").status_code, status.HTTP_403_FORBIDDEN)
        released = self.post(self.signatory, url + "approve/")
        self.assertEqual(released.status_code, status.HTTP_200_OK, released.data)
        self.assertEqual(released.data["status"], "signed")
        self.assertEqual(
            self.states(url),
            {"prepared": "completed", "independent_check": "completed", "shariah_review": "completed", "final_release": "completed"},
        )

        run = AllocationRun.objects.get(pk=released.data["id"])
        self.assertEqual(run.checked_by_id, self.checker.id)
        self.assertEqual(run.shariah_signed_off_by_id, self.secretariat.id)
        self.assertEqual(run.released_by_id, self.signatory.id)
        gates = {g["key"]: g["passed"] for g in released.data["control_gates"]}
        self.assertTrue(gates["final_authority"] and gates["shariah_review"] and gates["shariah_parameters_sealed"])

    def test_the_shariah_board_can_also_perform_the_shariah_review(self):
        url = self._prepared_run("bank_pool", "BANK-B")
        self.post(self.checker, url + "check/")
        self.assertEqual(self.post(self.board, url + "shariah-sign-off/", {"note": "ok"}).status_code, status.HTTP_200_OK)
        self.assertEqual(self.post(self.signatory, url + "approve/").status_code, status.HTTP_200_OK)

    def test_non_bank_pool_skips_the_shariah_stage(self):
        url = self._prepared_run("investment_pool", "INV")
        self.post(self.checker, url + "check/")
        self.assertEqual(
            [s["key"] for s in self.client.get(url).data["stages"]],
            ["prepared", "independent_check", "final_release"],
        )
        self.assertEqual(self.post(self.secretariat, url + "shariah-sign-off/").status_code, status.HTTP_400_BAD_REQUEST)
        released = self.post(self.signatory, url + "approve/")
        self.assertEqual(released.status_code, status.HTTP_200_OK, released.data)
        self.assertEqual(released.data["status"], "signed")

    def test_release_cannot_be_given_by_the_independent_checker_even_if_the_role_changed(self):
        url = self._prepared_run("investment_pool", "INV-2")
        self.post(self.checker, url + "check/")
        AllocationRun.objects.filter(pk=url.rstrip("/").split("/")[-1]).update(checked_by=self.signatory)
        response = self.post(self.signatory, url + "approve/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_each_stage_owner_can_reject_with_a_reason(self):
        for stage, rejecter in (("pending", self.checker), ("checked", self.secretariat), ("reviewed", self.signatory)):
            url = self._prepared_run("bank_pool", f"REJ-{stage}")
            if stage in ("checked", "reviewed"):
                self.post(self.checker, url + "check/")
            if stage == "reviewed":
                self.post(self.secretariat, url + "shariah-sign-off/", {"note": "ok"})
            # A reason is mandatory.
            self.assertEqual(self.post(rejecter, url + "reject/").status_code, status.HTTP_400_BAD_REQUEST)
            rejected = self.post(rejecter, url + "reject/", {"rejection_reason": f"Rejected at {stage}"})
            self.assertEqual(rejected.status_code, status.HTTP_200_OK, rejected.data)
            self.assertEqual(rejected.data["status"], "rejected")
            self.assertEqual(rejected.data["rejection_reason"], f"Rejected at {stage}")

    def test_makers_cannot_reject_and_signed_runs_cannot_be_rejected(self):
        url = self._prepared_run("investment_pool", "INV-3")
        self.assertEqual(
            self.post(self.maker, url + "reject/", {"rejection_reason": "x"}).status_code, status.HTTP_403_FORBIDDEN
        )
        self.post(self.checker, url + "check/")
        self.post(self.signatory, url + "approve/")
        self.assertEqual(
            self.post(self.checker, url + "reject/", {"rejection_reason": "x"}).status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_a_rejected_run_shows_where_it_stopped(self):
        url = self._prepared_run("bank_pool", "STOP")
        self.post(self.checker, url + "check/")
        self.post(self.secretariat, url + "reject/", {"rejection_reason": "PSR not as approved"})
        self.assertEqual(
            self.states(url),
            {"prepared": "completed", "independent_check": "completed", "shariah_review": "rejected", "final_release": "waiting"},
        )
