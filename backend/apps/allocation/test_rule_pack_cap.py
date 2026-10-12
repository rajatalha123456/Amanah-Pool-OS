from datetime import date
from decimal import Decimal

from django.urls import reverse

from apps.products.models import JurisdictionRulePack

from .test_participant_ledger import ParticipantLedgerTestBase


class RulePackCapTests(ParticipantLedgerTestBase):
    def setUp(self):
        super().setUp()
        # Close the base fixture's open-ended PSR so the new schedule does not overlap it.
        from .models import ProfitSharingRatio

        ProfitSharingRatio.objects.filter(pool=self.pool).update(effective_to=date(2026, 12, 31))

    def post_psr(self, mudarib):
        self.authenticate(self.pool_manager)
        return self.client.post(
            reverse("psr-schedule-list"),
            {"pool": str(self.pool.id), "depositor_share": str(Decimal("100") - Decimal(mudarib)), "mudarib_share": mudarib,
             "effective_from": "2027-01-01"},
            format="json",
        )

    def test_psr_above_the_rule_pack_cap_is_refused(self):
        pack = JurisdictionRulePack.objects.create(
            tenant=self.tenant, code="PK-TEST", name="Test", effective_date=date(2026, 1, 1), is_default=True,
            rules_config={"mudarib_share_cap_pct": 20.0},
        )
        self.pool.rule_pack = pack
        self.pool.save()
        self.assertEqual(self.post_psr("30.00").status_code, 400)
        self.assertEqual(self.post_psr("20.00").status_code, 201)

    def test_no_cap_in_the_pack_means_no_limit(self):
        self.assertEqual(self.post_psr("45.00").status_code, 201)
