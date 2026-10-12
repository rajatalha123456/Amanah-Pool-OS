from decimal import Decimal

from django.urls import reverse

from apps.accounts.models import UserRole
from apps.products.models import Product

from .models import CapitalAccount, InvestorProfile
from .test_distribution import MudarabahBase


class ParticipationTermsTests(MudarabahBase):
    """BRD section 5 "Participation": minimum, cap, tenure, KYC tier, member limits, and the pool calendar."""

    def set_terms(self, **terms):
        """Change the product terms; they are part of the investor disclosure, so investors acknowledge it afresh."""
        from .disclosures import ensure_acknowledged

        Product._base_manager.filter(pk=self.pool.product_id).update(**terms)
        for account in (self.acc_a, self.acc_b):
            ensure_acknowledged(CapitalAccount._base_manager.get(pk=account.pk), self.pm)

    def sub(self, amount, account=None, day="2026-09-15"):
        self.authenticate(self.maker)
        return self.client.post(
            reverse("capital-account-subscribe", args=[(account or self.acc_a).id]),
            {"amount": str(amount), "transaction_date": day}, format="json",
        )

    def redeem(self, day, account=None, units="10"):
        self.authenticate(self.maker)
        return self.client.post(
            reverse("capital-account-redeem", args=[(account or self.acc_a).id]),
            {"units_redeemed": units, "transaction_date": day}, format="json",
        )

    def test_minimum_subscription_is_enforced(self):
        self.set_terms(minimum_subscription=Decimal("5000.00"))
        refused = self.sub("1000")
        self.assertEqual(refused.status_code, 400)
        self.assertIn("minimum subscription", str(refused.data))
        self.assertEqual(self.sub("5000").status_code, 201)

    def test_the_cap_counts_everything_already_subscribed(self):
        self.set_terms(subscription_cap=Decimal("6000.00"))
        self.assertEqual(self.sub("4000").status_code, 201)
        over = self.sub("3000")
        self.assertEqual(over.status_code, 400)
        self.assertIn("cap per account", str(over.data))
        self.assertEqual(self.sub("1000").status_code, 201)  # 1000 from setUp + 4000 + 1000 = exactly the cap

    def test_a_product_can_require_a_higher_kyc_tier(self):
        self.set_terms(required_kyc_tier="enhanced")
        self.assertEqual(self.sub("1000").status_code, 400)
        InvestorProfile._base_manager.filter(capital_account=self.acc_a).update(kyc_tier="enhanced")
        self.assertEqual(self.sub("1000").status_code, 201)

    def test_kyc_tier_is_set_when_a_checker_verifies(self):
        profile = InvestorProfile._base_manager.get(capital_account=self.acc_a)
        self.authenticate(self._user("risk", UserRole.RISK_COMPLIANCE))
        response = self.client.post(
            reverse("investor-profile-verify-kyc", args=[profile.id]), {"kyc_status": "verified", "kyc_tier": "bogus"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_minimum_holding_period_blocks_an_early_redemption(self):
        self.set_terms(minimum_tenure_days=3650)
        self.assertEqual(self.sub("1000").status_code, 201)
        early = self.redeem("2026-09-20")
        self.assertEqual(early.status_code, 400, early.content)
        self.assertIn("minimum holding", str(early.data))

    def test_a_pool_calendar_limits_dealing_dates(self):
        from apps.pools.models import Pool

        Pool._base_manager.filter(pk=self.pool.pk).update(calendar="mon_fri")
        saturday = self.redeem("2026-09-12")  # a Saturday
        self.assertEqual(saturday.status_code, 400, saturday.content)
        self.assertIn("not a working day", str(saturday.data))
        self.assertEqual(self.redeem("2026-09-14").status_code, 201)  # Monday

    def test_the_participant_limit_stops_new_accounts(self):
        self.set_terms(max_participants=CapitalAccount._base_manager.filter(pool=self.pool).count())
        self.authenticate(self.maker)
        response = self.client.post(
            reverse("capital-account-list"),
            {"pool": str(self.pool.id), "investor_reference": "INV-NEW", "investor_name": "New Investor", "participant": None},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("pool is full", str(response.data))

    def test_invalid_terms_are_refused_by_the_product_form(self):
        self.authenticate(self._user("prodmgr", UserRole.PRODUCT_MANAGER))
        url = reverse("product-detail", args=[self.pool.product_id])
        bad = self.client.patch(url, {"minimum_subscription": "9000", "subscription_cap": "1000"}, format="json")
        self.assertEqual(bad.status_code, 400, bad.content)
