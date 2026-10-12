from decimal import Decimal

from apps.allocation.test_participant_ledger import ParticipantLedgerTestBase


class PortfolioSummaryTests(ParticipantLedgerTestBase):
    def get(self, user):
        self.authenticate(user)
        return self.client.get("/api/v1/pools/pools/portfolio-summary/")

    def test_no_data_means_null_not_placeholders(self):
        row = self.get(self.maker).data["pools"][0]
        self.assertIsNone(row["annualised_yield_pct"])
        self.assertIsNone(row["last_signed_profit"])

    def test_signed_run_gives_real_profit_and_yield(self):
        self.pool.product.operating_model = "bank_pool"
        self.pool.product.save()
        self.sign_run()
        data = self.get(self.maker).data
        row = data["pools"][0]
        self.assertEqual(row["last_signed_profit"], "600.00")
        self.assertEqual(Decimal(data["total_signed_profit"]), Decimal("600.00"))
        self.assertIsNotNone(row["annualised_yield_pct"])
        self.assertIsNotNone(row["funds"])

    def test_investors_cannot_read_it(self):
        self.assertEqual(self.get(self.investor_a).status_code, 403)
