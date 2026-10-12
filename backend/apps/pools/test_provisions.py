from datetime import date
from decimal import Decimal

from apps.accounting.models import IncomeExpenseEvent, JournalEntry
from apps.allocation.test_participant_ledger import ParticipantLedgerTestBase

from .models import Asset, AssetAssignment, AssetStatus, AssetType
from .provisions import asset_position

URL = "/api/v1/pools/asset-provisions/"


class ProvisionTests(ParticipantLedgerTestBase):
    def setUp(self):
        super().setUp()
        self.asset = Asset.objects.create(
            tenant=self.tenant, reference_code="A-9", asset_type=AssetType.MURABAHAH, description="x",
            face_value=Decimal("1000.00"),
        )
        AssetAssignment.objects.create(
            tenant=self.tenant, asset=self.asset, pool=self.pool, assigned_date=date(2026, 1, 1)
        )

    def request(self, entry_type, amount, user=None, day="2026-09-25"):
        self.authenticate(user or self.maker)
        return self.client.post(
            URL,
            {"asset": str(self.asset.id), "entry_type": entry_type, "amount": amount, "effective_date": day,
             "reason": "Obligor in default"},
            format="json",
        )

    def decide(self, entry, verb="approve", user=None, **body):
        self.authenticate(user or self.checker)
        return self.client.post(f"{URL}{entry['id']}/{verb}/", body, format="json")

    def done(self, entry_type, amount):
        entry = self.request(entry_type, amount).data
        self.assertEqual(self.decide(entry).status_code, 200)
        return entry

    def position(self):
        return {k: str(v) for k, v in asset_position(Asset._base_manager.get(pk=self.asset.pk)).items()}

    def test_provision_posts_a_balanced_journal_and_a_pool_expense(self):
        entry = self.done("provision", "200.00")
        saved = IncomeExpenseEvent._base_manager.get(category="Asset provision")
        self.assertEqual((saved.amount, saved.event_type, saved.status), (Decimal("200.00"), "expense", "posted"))
        lines = JournalEntry._base_manager.filter(batch__pool=self.pool, account_key__startswith="provision")
        self.assertEqual({(l.account_key, l.entry_type) for l in lines},
                         {("provision_expense", "debit"), ("provision_reserve", "credit")})
        self.assertEqual(self.position()["provision_balance"], "200.00")
        self.assertEqual(self.decide(entry).status_code, 400)  # already decided

    def test_maker_cannot_approve_their_own_entry(self):
        entry = self.request("provision", "50.00").data
        self.assertEqual(self.decide(entry, user=self.maker).status_code, 403)

    def test_checker_is_blocked_when_also_the_maker(self):
        self.authenticate(self.checker)
        # a checker is not allowed to create at all
        self.assertEqual(self.request("provision", "50.00", user=self.checker).status_code, 403)

    def test_provision_cannot_exceed_exposure_or_release_more_than_held(self):
        self.assertEqual(self.request("provision", "1500.00").status_code, 400)
        self.done("provision", "100.00")
        self.assertEqual(self.request("release", "150.00").status_code, 400)
        self.done("release", "40.00")
        self.assertEqual(self.position()["provision_balance"], "60.00")

    def test_write_off_uses_the_provision_first_and_expenses_only_the_excess(self):
        self.done("provision", "300.00")
        entry = self.done("write_off", "500.00")
        pos = self.position()
        self.assertEqual((pos["provision_balance"], pos["written_off"], pos["exposure"]), ("0.00", "500.00", "500.00"))
        events = IncomeExpenseEvent._base_manager.filter(category="Asset write-off")
        self.assertEqual([e.amount for e in events], [Decimal("200.00")])
        batch_lines = JournalEntry._base_manager.filter(batch__pool=self.pool, account_key="asset_portfolio")
        self.assertEqual(sum(l.amount for l in batch_lines), Decimal("500.00"))

    def test_full_write_off_closes_the_asset_and_recovery_is_capped(self):
        self.done("write_off", "1000.00")
        asset = Asset._base_manager.get(pk=self.asset.pk)
        self.assertEqual(asset.status, AssetStatus.WRITTEN_OFF)
        self.assertFalse(AssetAssignment._base_manager.filter(asset=asset, unassigned_date__isnull=True).exists())
        self.assertEqual(self.request("recovery", "1200.00", day="2026-09-28").status_code, 400)
        self.done("recovery", "250.00")
        income = IncomeExpenseEvent._base_manager.get(category="Recovery of written-off asset")
        self.assertEqual((income.event_type, income.amount), ("income", Decimal("250.00")))
        self.assertEqual(self.position()["recoverable_balance"], "750.00")

    def test_rejection_needs_a_reason_and_leaves_no_trace(self):
        entry = self.request("provision", "80.00").data
        self.assertEqual(self.decide(entry, "reject").status_code, 400)
        self.assertEqual(self.decide(entry, "reject", reason="Not justified").status_code, 200)
        self.assertEqual(self.position()["provision_balance"], "0.00")
        self.assertFalse(IncomeExpenseEvent._base_manager.filter(category="Asset provision").exists())
