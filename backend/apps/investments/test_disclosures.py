from decimal import Decimal

from django.urls import reverse

from apps.allocation.models import ProfitSharingRatio

from .models import DisclosureAcknowledgement, PoolDisclosure
from .test_distribution import MudarabahBase

BASE = "/api/v1/investments/disclosures/"


class DisclosureTests(MudarabahBase):
    def call(self, user, method, path, body=None):
        self.authenticate(user)
        return getattr(self.client, method)(f"{BASE}{path}", body, format="json")

    def prepare(self, **extra):
        body = {"pool": str(self.pool.id), "risk_warnings": "Capital at risk.", "fee_statement": "No fees beyond PSR."}
        body.update(extra)
        return self.call(self.pm, "post", "publish/", body)

    def publish(self, **extra):
        """Prepare, then approve by a different person (the board); returns the approved record's response."""
        response = self.prepare(**extra)
        if response.status_code != 201:
            return response
        return self.call(self.shariah, "post", f"{response.data['id']}/approve/")

    def subscribe_status(self, account, user=None):
        return self.call(user or self.maker, "get", f"subscription-status/?capital_account={account.id}").data

    def test_disclosure_states_only_real_terms_and_is_sealed(self):
        # setUp's helper published v1; a manual publish with new warnings is v2 built from the live configuration.
        response = self.publish(risk_warnings="Capital at risk; no guarantee of returns.")
        self.assertEqual(response.status_code, 200, response.data)
        terms = response.data["terms"]
        self.assertEqual(terms["contract"]["type"], "mudarabah_unrestricted")
        self.assertEqual(terms["profit_sharing"]["manager_share_pct"], 20.0)
        self.assertEqual(terms["redemption"], {"notice_days": 0, "gate_pct_per_30_days": "100.00"})
        disclosure = PoolDisclosure._base_manager.get(pk=response.data["id"])
        disclosure.risk_warnings = "edited"
        with self.assertRaises(Exception):
            disclosure.save()

    def test_identical_republish_is_refused_and_warnings_are_required(self):
        self.assertEqual(self.publish(risk_warnings="").status_code, 400)
        first = self.publish(risk_warnings="Warning A").data
        self.assertEqual(first["version"], 2)
        self.assertEqual(self.publish(risk_warnings="Warning A").status_code, 400)

    def test_only_pool_or_product_manager_prepares_and_only_board_or_risk_approves(self):
        self.assertEqual(self.call(self.maker, "post", "publish/", {"pool": str(self.pool.id)}).status_code, 403)
        self.assertEqual(self.call(self.inv_a, "post", "publish/", {"pool": str(self.pool.id)}).status_code, 403)
        self.assertEqual(self.call(self.shariah, "post", "publish/", {"pool": str(self.pool.id)}).status_code, 403)
        draft = self.prepare(risk_warnings="Draft warnings").data
        self.assertEqual(draft["status"], "pending_review")
        for user in (self.pm, self.maker, self.inv_a):
            self.assertEqual(self.call(user, "post", f"{draft['id']}/approve/").status_code, 403)

    def test_a_pending_disclosure_is_not_binding_until_a_different_person_approves_it(self):
        ProfitSharingRatio.objects.filter(pool=self.pool).update(depositor_share=Decimal("70.00"), mudarib_share=Decimal("30.00"))
        draft = self.prepare().data
        # Still blocked: investors cannot acknowledge, and the old disclosure no longer matches the terms.
        ack = self.call(self.inv_a, "post", f"{draft['id']}/acknowledge/",
                        {"capital_account": str(self.acc_a.id), "risk_acknowledged": True})
        self.assertEqual(ack.status_code, 404)  # a draft is invisible to investors
        self.assertFalse(self.subscribe_status(self.acc_a)["may_subscribe"])
        self.assertEqual([d["id"] for d in self.call(self.inv_a, "get", "").data if d["id"] == draft["id"]], [])
        approved = self.call(self.shariah, "post", f"{draft['id']}/approve/")
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["status"], "published")
        self.assertEqual(self.call(self.shariah, "post", f"{draft['id']}/approve/").status_code, 400)  # already approved

    def test_a_change_in_terms_blocks_subscription_until_a_new_disclosure_is_acknowledged(self):
        self.assertTrue(self.subscribe_status(self.acc_a)["may_subscribe"])
        ProfitSharingRatio.objects.filter(pool=self.pool).update(depositor_share=Decimal("70.00"), mudarib_share=Decimal("30.00"))
        blocked = self.subscribe_status(self.acc_a)
        self.assertFalse(blocked["may_subscribe"])
        self.assertIn("terms have changed", blocked["reason"])
        published = self.publish().data
        again = self.subscribe_status(self.acc_a)
        self.assertFalse(again["may_subscribe"])
        self.assertIn("not acknowledged", again["reason"])
        ack = self.call(self.inv_a, "post", f"{published['id']}/acknowledge/",
                        {"capital_account": str(self.acc_a.id), "risk_acknowledged": True})
        self.assertEqual(ack.status_code, 201, ack.data)
        self.assertTrue(self.subscribe_status(self.acc_a)["may_subscribe"])
        self.assertFalse(self.subscribe_status(self.acc_b)["may_subscribe"])  # B has not acknowledged v-new

    def test_investor_acknowledges_only_for_themselves_through_the_portal_with_the_risk_box_ticked(self):
        published = self.publish(risk_warnings="New warnings").data
        url = f"{published['id']}/acknowledge/"
        body = {"capital_account": str(self.acc_b.id), "risk_acknowledged": True}
        self.assertEqual(self.call(self.inv_a, "post", url, body).status_code, 400)  # not their account
        mine = {"capital_account": str(self.acc_a.id)}
        self.assertEqual(self.call(self.inv_a, "post", url, mine).status_code, 400)  # risk not ticked
        self.assertEqual(self.call(self.inv_a, "post", url, {**mine, "risk_acknowledged": True, "method": "in_person"}).status_code, 400)
        self.assertEqual(self.call(self.inv_a, "post", url, {**mine, "risk_acknowledged": True}).status_code, 201)
        self.assertEqual(self.call(self.inv_a, "post", url, {**mine, "risk_acknowledged": True}).status_code, 400)  # twice

    def test_staff_record_electronic_acknowledgements_with_evidence_and_stale_versions_are_refused(self):
        old = PoolDisclosure._base_manager.get(pool=self.pool, version=1)
        new = self.publish(risk_warnings="Changed warnings").data
        stale = self.call(self.maker, "post", f"{old.id}/acknowledge/",
                          {"capital_account": str(self.acc_a.id), "method": "in_person", "risk_acknowledged": True})
        self.assertEqual(stale.status_code, 400)
        url = f"{new['id']}/acknowledge/"
        body = {"capital_account": str(self.acc_a.id), "method": "otp", "risk_acknowledged": True}
        self.assertEqual(self.call(self.maker, "post", url, body).status_code, 400)  # needs evidence
        self.assertEqual(self.call(self.maker, "post", url, {**body, "evidence_reference": "OTP-77"}).status_code, 201)
        ack = DisclosureAcknowledgement._base_manager.get(capital_account=self.acc_a, disclosure_id=new["id"])
        self.assertEqual((ack.method, ack.evidence_reference, ack.by_investor), ("otp", "OTP-77", False))

    def test_subscribe_endpoint_itself_enforces_the_gate(self):
        ProfitSharingRatio.objects.filter(pool=self.pool).update(depositor_share=Decimal("60.00"), mudarib_share=Decimal("40.00"))
        self.authenticate(self.maker)
        response = self.client.post(
            reverse("capital-account-subscribe", args=[self.acc_a.id]),
            {"amount": "10.00", "transaction_date": "2026-09-15"}, format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("disclosure", str(response.data))
