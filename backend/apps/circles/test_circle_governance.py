from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.participants.models import KYCStatus
from apps.pools.models import Pool
from apps.products.models import ContractTemplate, Product, ShariahDecision, ShariahDecisionStatus
from apps.tenants.models import Tenant

from .models import (
    CircleDraw,
    CircleMember,
    CircleMemberStatus,
    Contribution,
    ContributionStatus,
    Payout,
    PayoutStatus,
)
from .rotation import derive_order
from .rules import publish_and_accept_all

BASE = "/api/v1/circles/"


class CircleGovernanceTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Gov T", code="GOV-T", data_residency="PK")
        set_current_tenant(self.tenant)
        original_request = self.client.request

        def keep_tenant(**kwargs):
            try:
                return original_request(**kwargs)
            finally:
                set_current_tenant(self.tenant)

        self.client.request = keep_tenant
        self.pm = self._user("pm", UserRole.POOL_MANAGER)
        self.maker = self._user("maker", UserRole.FINANCE_MAKER)
        self.checker = self._user("checker", UserRole.FINANCE_CHECKER)
        decision = ShariahDecision.objects.create(
            tenant=self.tenant, decision_code="SD-G", title="Circle", description="d",
            status=ShariahDecisionStatus.APPROVED, effective_date=date(2026, 1, 1),
        )
        contract = ContractTemplate.objects.create(
            tenant=self.tenant, name="C", contract_type="qard", version="1", clauses={}, shariah_decision=decision
        )
        product = Product.objects.create(
            tenant=self.tenant, name="P", code="P-G", operating_model="community_circle", contract_template=contract
        )
        self.pool = Pool.objects.create(
            tenant=self.tenant, name="Circle", code="CIR-G", product=product, effective_date=date(2026, 1, 1)
        )
        self.members = [
            CircleMember.objects.create(
                tenant=self.tenant, pool=self.pool, member_name=f"Member {i}", member_reference=f"M-{i}",
                joined_date=date(2026, 1, 1), kyc_status=KYCStatus.VERIFIED,
            )
            for i in range(1, 5)
        ]

    def tearDown(self):
        set_current_tenant(None)

    def _user(self, name, role):
        return User.objects.create_user(
            email=f"{name}@gov.example.com", password="password", full_name=name.title(), role=role, tenant=self.tenant
        )

    def call(self, user, method, path, body=None):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code
        return getattr(self.client, method)(f"{BASE}{path}", body, format="json")

    def publish(self, **extra):
        body = {
            "pool": str(self.pool.id), "contribution_amount": "10000", "cycle_days": 30,
            "order_policy": "Verifiable draw", "hardship_policy": "Shariah-reviewed relief",
        }
        body.update(extra)
        return self.call(self.pm, "post", "rules/publish/", body)

    # ---- rules acceptance -------------------------------------------------------------------
    def test_draw_is_blocked_until_rules_are_published_and_accepted_by_everyone(self):
        blocked = self.call(self.pm, "post", "draws/commit/", {"pool": str(self.pool.id)})
        self.assertEqual(blocked.status_code, 400)
        self.assertEqual(self.publish().status_code, 201)
        for member in self.members[:3]:
            accepted = self.call(self.pm, "post", "rules/accept/", {"member": str(member.id), "method": "in_person"})
            self.assertEqual(accepted.status_code, 201)
        summary = self.call(self.pm, "get", f"rules/summary/?pool={self.pool.id}").data
        self.assertEqual((summary["accepted"], summary["total"], summary["missing"]), (3, 4, ["M-4"]))
        self.assertEqual(self.call(self.pm, "post", "draws/commit/", {"pool": str(self.pool.id)}).status_code, 400)
        self.call(self.pm, "post", "rules/accept/", {"member": str(self.members[3].id), "method": "in_person"})
        self.assertEqual(self.call(self.pm, "post", "draws/commit/", {"pool": str(self.pool.id)}).status_code, 201)

    def test_electronic_acceptance_needs_evidence_and_double_acceptance_is_refused(self):
        self.publish()
        body = {"member": str(self.members[0].id), "method": "otp"}
        self.assertEqual(self.call(self.pm, "post", "rules/accept/", body).status_code, 400)
        body["evidence_reference"] = "OTP-123"
        self.assertEqual(self.call(self.pm, "post", "rules/accept/", body).status_code, 201)
        self.assertEqual(self.call(self.pm, "post", "rules/accept/", body).status_code, 400)

    def test_new_rules_version_requires_reacceptance(self):
        publish_and_accept_all(self.pool, self.pm)
        self.assertEqual(self.call(self.pm, "post", "draws/commit/", {"pool": str(self.pool.id)}).status_code, 201)
        self.publish(contribution_amount="12000")
        summary = self.call(self.pm, "get", f"rules/summary/?pool={self.pool.id}").data
        self.assertEqual((summary["rules"]["version"], summary["accepted"]), (2, 0))

    # ---- verifiable draw --------------------------------------------------------------------
    def test_commit_reveal_draw_is_verifiable_and_the_seed_stays_hidden_until_execution(self):
        publish_and_accept_all(self.pool, self.pm)
        committed = self.call(self.pm, "post", "draws/commit/", {"pool": str(self.pool.id)}).data
        self.assertIsNone(committed["server_seed"])
        self.assertEqual(len(committed["commitment"]), 64)
        self.assertEqual(self.call(self.pm, "post", "draws/commit/", {"pool": str(self.pool.id)}).status_code, 400)

        draw_id = committed["id"]
        self.assertEqual(self.call(self.pm, "post", f"draws/{draw_id}/execute/", {"client_seed": "ab"}).status_code, 400)
        executed = self.call(self.pm, "post", f"draws/{draw_id}/execute/", {"client_seed": "members-chose-this"}).data
        self.assertEqual(sorted(a["position"] for a in executed["assignments"]), [1, 2, 3, 4])
        self.assertIsNotNone(executed["server_seed"])

        verdict = self.call(self.checker, "get", f"draws/{draw_id}/verify/").data
        self.assertTrue(verdict["verified"])
        by_position = [a["member_reference"] for a in sorted(executed["assignments"], key=lambda a: a["position"])]
        self.assertEqual(by_position, derive_order(executed["server_seed"], "members-chose-this", executed["participants"]))
        self.assertEqual(self.call(self.pm, "post", f"draws/{draw_id}/execute/", {"client_seed": "again-again"}).status_code, 400)

    def test_a_tampered_draw_fails_verification(self):
        publish_and_accept_all(self.pool, self.pm)
        draw_id = self.call(self.pm, "post", "draws/commit/", {"pool": str(self.pool.id)}).data["id"]
        self.call(self.pm, "post", f"draws/{draw_id}/execute/", {"client_seed": "seed-seed"})
        draw = CircleDraw._base_manager.get(pk=draw_id)
        draw.assignments = list(reversed(draw.assignments))
        draw.assignments[0]["position"], draw.assignments[1]["position"] = (
            draw.assignments[1]["position"], draw.assignments[0]["position"],
        )
        draw.save()
        self.assertFalse(self.call(self.pm, "get", f"draws/{draw_id}/verify/").data["verified"])

    def test_membership_change_after_commitment_blocks_execution(self):
        publish_and_accept_all(self.pool, self.pm)
        draw_id = self.call(self.pm, "post", "draws/commit/", {"pool": str(self.pool.id)}).data["id"]
        self.members[0].status = CircleMemberStatus.WITHDRAWN
        self.members[0].save()
        self.assertEqual(self.call(self.pm, "post", f"draws/{draw_id}/execute/", {"client_seed": "seed-seed"}).status_code, 400)

    # ---- closure ----------------------------------------------------------------------------
    def finish_all_cycles(self):
        for cycle, member in enumerate(self.members, start=1):
            for payer in self.members:
                Contribution.objects.create(
                    tenant=self.tenant, member=payer, amount="1000.00", contribution_date=date(2026, 3, 1),
                    cycle_number=cycle, status=ContributionStatus.RECEIVED,
                )
            Payout.objects.create(
                tenant=self.tenant, member=member, pool=self.pool, cycle_number=cycle, amount="4000.00",
                payout_date=date(2026, 3, 5), status=PayoutStatus.DISBURSED,
            )
            member.status = CircleMemberStatus.PAID_OUT
            member.save()

    def test_closure_is_blocked_while_members_are_unpaid(self):
        response = self.call(self.maker, "post", "closures/prepare/", {"pool": str(self.pool.id)})
        self.assertEqual(response.status_code, 400)
        self.assertIn("blockers", str(response.data))

    def test_balanced_circle_closes_with_a_different_checker(self):
        self.finish_all_cycles()
        preview = self.call(self.maker, "get", f"closures/preview/?pool={self.pool.id}").data
        self.assertEqual((preview["total_collected"], preview["total_disbursed"], preview["difference"]),
                         ("16000.00", "16000.00", "0.00"))
        prepared = self.call(self.maker, "post", "closures/prepare/", {"pool": str(self.pool.id)})
        self.assertEqual(prepared.status_code, 201)
        # the maker role cannot close (checker only)
        self.assertEqual(self.call(self.maker, "post", "closures/close/", {"pool": str(self.pool.id)}).status_code, 403)
        closed = self.call(self.checker, "post", "closures/close/", {"pool": str(self.pool.id)})
        self.assertEqual(closed.status_code, 200)
        self.pool.refresh_from_db()
        self.assertEqual(self.pool.status, "closed")
        self.assertIsNotNone(self.pool.closed_date)

    def test_a_surplus_needs_a_resolution_note(self):
        self.finish_all_cycles()
        Contribution.objects.create(
            tenant=self.tenant, member=self.members[0], amount="500.00", contribution_date=date(2026, 3, 9),
            cycle_number=5, status=ContributionStatus.RECEIVED,  # an over-payment outside the schedule
        )
        url = "closures/prepare/"
        self.assertEqual(self.call(self.maker, "post", url, {"pool": str(self.pool.id)}).status_code, 400)
        ok = self.call(self.maker, "post", url, {"pool": str(self.pool.id), "resolution_note": "Refunded to M-1"})
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(Decimal(ok.data["difference"]), Decimal("500.00"))
