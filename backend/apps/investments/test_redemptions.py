from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from apps.accounting.models import JournalEntry

from .models import CapitalAccount, Redemption
from .test_distribution import MudarabahBase


class RedemptionWorkflowTests(MudarabahBase):
    def request(self, account=None, units="100", day="2026-09-12", user=None):
        self.authenticate(user or self.maker)
        return self.client.post(
            reverse("capital-account-redeem", args=[(account or self.acc_a).id]),
            {"units_redeemed": units, "transaction_date": day},
            format="json",
        )

    def decide(self, redemption, verb="approve", user=None, **body):
        self.authenticate(user or self.checker)
        return self.client.post(reverse("redemption-detail", args=[redemption["id"]]) + f"{verb}/", body, format="json")

    def units(self, account):
        return CapitalAccount._base_manager.get(pk=account.pk).units_held

    def test_request_moves_nothing_until_a_checker_approves(self):
        pending = self.request().data
        self.assertEqual(pending["status"], "pending")
        self.assertEqual(self.units(self.acc_a), Decimal("1000"))
        done = self.decide(pending)
        self.assertEqual(done.status_code, 200, done.data)
        self.assertEqual(done.data["status"], "processed")
        self.assertEqual(self.units(self.acc_a), Decimal("900"))
        lines = JournalEntry._base_manager.filter(batch__pool=self.pool, account_key="redemption_payable")
        self.assertEqual(sum(l.amount for l in lines), Decimal(done.data["amount"]))

    def test_requester_cannot_approve_and_investor_cannot_approve(self):
        pending = self.request().data
        self.assertEqual(self.decide(pending, user=self.maker).status_code, 403)
        self.assertEqual(self.decide(pending, user=self.inv_a).status_code, 403)

    def test_investor_can_request_only_for_their_own_account(self):
        own = self.request(account=self.acc_a, user=self.inv_a)
        self.assertEqual(own.status_code, 201, own.data)
        other = self.request(account=self.acc_b, user=self.inv_a)
        self.assertEqual(other.status_code, 404)

    def test_pending_requests_reserve_units(self):
        self.assertEqual(self.request(units="700").status_code, 201)
        self.assertEqual(self.request(units="400").status_code, 400)  # only 300 left unreserved
        self.assertEqual(self.request(units="300").status_code, 201)

    def test_notice_period_is_enforced(self):
        product = self.pool.product
        product.redemption_notice_days = 10
        product.save()
        soon = (timezone.localdate() + timedelta(days=3)).isoformat()
        self.assertEqual(self.request(day=soon).status_code, 400)
        later = (timezone.localdate() + timedelta(days=10)).isoformat()
        self.assertEqual(self.request(day=later).status_code, 201)

    def test_dealing_date_must_have_arrived_before_approval(self):
        product = self.pool.product
        product.redemption_notice_days = 5
        product.save()
        later = (timezone.localdate() + timedelta(days=6)).isoformat()
        pending = self.request(day=later).data
        response = self.decide(pending)
        self.assertEqual(response.status_code, 400)
        self.assertIn("not arrived", str(response.data))

    def test_gate_blocks_redemptions_beyond_the_window_limit(self):
        product = self.pool.product
        product.redemption_gate_pct = Decimal("30.00")  # NAV pool value 1000 -> 300 per 30 days
        product.save()
        first = self.request(units="200").data
        self.assertEqual(self.decide(first).status_code, 200)
        second = self.request(units="150").data
        blocked = self.decide(second)
        self.assertEqual(blocked.status_code, 400)
        self.assertIn("gate", str(blocked.data).lower())
        small = self.request(units="100").data
        self.assertEqual(self.decide(small).status_code, 200)
        self.assertEqual(self.units(self.acc_a), Decimal("700"))

    def test_rejection_needs_a_reason_and_releases_the_reservation(self):
        pending = self.request(units="900").data
        self.assertEqual(self.decide(pending, "reject").status_code, 400)
        self.assertEqual(self.decide(pending, "reject", reason="Liquidity").status_code, 200)
        self.assertEqual(Redemption._base_manager.get(pk=pending["id"]).status, "rejected")
        self.assertEqual(self.units(self.acc_a), Decimal("1000"))
        self.assertEqual(self.request(units="900").status_code, 201)

    def test_decided_redemption_cannot_be_decided_again(self):
        pending = self.request().data
        self.decide(pending)
        self.assertEqual(self.decide(pending).status_code, 400)
        self.assertEqual(self.decide(pending, "reject", reason="x").status_code, 400)
