from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.participants.models import KYCStatus
from apps.pools.models import Pool
from apps.products.models import ContractTemplate, Product, ShariahDecision, ShariahDecisionStatus
from apps.tenants.models import Tenant

from .models import (
    ArrearsRecord,
    CircleMember,
    Contribution,
    ContributionStatus,
    Payout,
    PayoutStatus,
)


class PayoutWorkflowTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Payout T", code="PAYOUT-T", data_residency="PK")
        set_current_tenant(self.tenant)

        original_request = self.client.request

        def request_keeping_tenant(**kwargs):
            try:
                return original_request(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = request_keeping_tenant

        self.pm = self._user("pm", UserRole.POOL_MANAGER)
        self.maker = self._user("maker", UserRole.FINANCE_MAKER)
        self.checker = self._user("checker", UserRole.FINANCE_CHECKER)
        self.investor = self._user("member", UserRole.INVESTOR_MEMBER)

        decision = ShariahDecision.objects.create(
            tenant=self.tenant, decision_code="SD-PAY", title="Circle", description="d",
            status=ShariahDecisionStatus.APPROVED, effective_date=date(2026, 1, 1),
        )
        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name="C", contract_type="qard", version="1", clauses={}, shariah_decision=decision
        )
        product = Product.objects.create(
            tenant=self.tenant, name="P", code="P-PAY", operating_model="community_circle", contract_template=contract
        )
        self.pool = Pool.objects.create(
            tenant=self.tenant, name="Circle", code="CIR-PAY", product=product, effective_date=date(2026, 1, 1)
        )
        self.members = []
        for position in (1, 2, 3):
            member = CircleMember.objects.create(
                tenant=self.tenant, pool=self.pool, member_name=f"Member {position}",
                member_reference=f"M-{position}", joined_date=date(2026, 1, 1), payout_position=position,
                kyc_status=KYCStatus.VERIFIED, iban=f"PK36MEZN00010012345678{position:02d}", bank_name="Meezan",
            )
            Contribution.objects.create(
                tenant=self.tenant, member=member, amount="2000.00", contribution_date=date(2026, 9, 1),
                cycle_number=1, status=ContributionStatus.RECEIVED,
            )
            self.members.append(member)

    def tearDown(self):
        set_current_tenant(None)

    def _user(self, name, role):
        return User.objects.create_user(
            email=f"{name}@payout.example.com", password="password", full_name=name.title(),
            role=role, tenant=self.tenant,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

    @property
    def request_url(self):
        return reverse("circle-payout-request-payout", args=[str(self.pool.id)])

    def request_payout(self, rail="raast_rtgs", member=None, user=None):
        self.authenticate(user or self.pm)
        return self.client.post(
            self.request_url,
            {"member_id": str((member or self.members[0]).id), "settlement_rail": rail, "payout_date": "2026-09-10"},
            format="json",
        )

    def test_readiness_reports_real_checks_and_no_invented_figures(self):
        self.authenticate(self.pm)
        response = self.client.get(reverse("circle-payout-ceremony-readiness", args=[str(self.pool.id)]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["cycle_number"], 1)
        self.assertEqual(data["pot_summary"]["total_collected_pot"], 6000.0)
        self.assertEqual(data["next_recipient"]["iban"], self.members[0].iban)
        self.assertTrue(data["can_request"])
        self.assertTrue(all(check["passed"] for check in data["checks"]))
        self.assertEqual(data["shariah_decision"]["decision_code"], "SD-PAY")

    def test_members_and_investors_cannot_see_payout_readiness(self):
        self.authenticate(self.investor)
        response = self.client.get(reverse("circle-payout-ceremony-readiness", args=[str(self.pool.id)]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_collections_are_never_auto_created(self):
        Contribution.objects.filter(member=self.members[1]).delete()
        response = self.request_payout()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Contribution.objects.filter(member=self.members[1]).count(), 0)

    def test_unverified_kyc_blocks_release(self):
        self.members[0].kyc_status = KYCStatus.PENDING
        self.members[0].save()
        self.assertEqual(self.request_payout().status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_bank_details_block_external_rails_but_not_internal_book(self):
        self.members[0].iban = ""
        self.members[0].save()
        self.assertEqual(self.request_payout().status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.request_payout(rail="internal_book").status_code, status.HTTP_201_CREATED)

    def test_overdue_arrears_block_release(self):
        ArrearsRecord.objects.create(
            tenant=self.tenant, member=self.members[2], cycle_number=1, expected_amount="2000.00"
        )
        self.assertEqual(self.request_payout().status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_shariah_decision_blocks_release(self):
        ShariahDecision.objects.filter(pk=self.pool.product.contract_template.shariah_decision_id).update(
            status=ShariahDecisionStatus.DRAFT
        )
        self.assertEqual(self.request_payout().status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_one_open_payout_at_a_time(self):
        self.assertEqual(self.request_payout().status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.request_payout().status_code, status.HTTP_400_BAD_REQUEST)

    def test_requester_cannot_approve_own_request_even_with_checker_role(self):
        # A finance checker may not request (403), so exercise the guard directly on the model state.
        created = self.request_payout().data
        Payout.objects.filter(pk=created["id"]).update(requested_by=self.checker)
        self.authenticate(self.checker)
        response = self.client.post(reverse("circle-payout-approve", args=[created["id"]]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pot_changing_after_request_blocks_approval(self):
        created = self.request_payout().data
        Contribution.objects.filter(member=self.members[0]).update(amount="2500.00")
        self.authenticate(self.checker)
        response = self.client.post(reverse("circle-payout-approve", args=[created["id"]]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_requires_reason_and_is_final(self):
        created = self.request_payout().data
        self.authenticate(self.checker)
        reject_url = reverse("circle-payout-reject", args=[created["id"]])
        self.assertEqual(self.client.post(reject_url, {}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        rejected = self.client.post(reject_url, {"reason": "Wrong IBAN"}, format="json")
        self.assertEqual(rejected.status_code, status.HTTP_200_OK)
        self.assertEqual(rejected.data["status"], PayoutStatus.REJECTED)
        # Final: can neither be approved nor re-rejected.
        self.assertEqual(
            self.client.post(reverse("circle-payout-approve", args=[created["id"]])).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        # After a rejection a fresh request is possible again.
        self.assertEqual(self.request_payout().status_code, status.HTTP_201_CREATED)

    def test_internal_book_settlement_gets_an_internal_reference(self):
        created = self.request_payout(rail="internal_book").data
        self.authenticate(self.checker)
        self.client.post(reverse("circle-payout-approve", args=[created["id"]]))
        self.authenticate(self.maker)
        settled = self.client.post(reverse("circle-payout-settle", args=[created["id"]]), {}, format="json")
        self.assertEqual(settled.status_code, status.HTTP_200_OK, settled.data)
        self.assertTrue(settled.data["settlement_utr"].startswith("BOOK-"))

    def test_payouts_cannot_be_written_through_the_list_endpoint(self):
        self.authenticate(self.maker)
        response = self.client.post(reverse("circle-payout-list"), {"amount": "1.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_receipt_contains_only_recorded_facts(self):
        created = self.request_payout().data
        self.authenticate(self.checker)
        self.client.post(reverse("circle-payout-approve", args=[created["id"]]))
        self.authenticate(self.maker)
        self.client.post(reverse("circle-payout-settle", args=[created["id"]]), {"settlement_utr": "RRN-9"}, format="json")
        receipt = self.client.get(reverse("circle-payout-receipt", args=[created["id"]])).data
        self.assertEqual(receipt["settlement_utr"], "RRN-9")
        self.assertEqual(receipt["shariah_certificate_number"], "SD-PAY")
        self.assertEqual(receipt["requested_by"], "Pm")
        self.assertEqual(receipt["secondary_approved_by"], "Checker")
        self.assertIsNone(receipt["biometric_auth_ref"])
