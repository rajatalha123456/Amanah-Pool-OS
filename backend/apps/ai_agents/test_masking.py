from django.test import SimpleTestCase

from .recording import mask_sensitive


class MaskingTests(SimpleTestCase):
    def test_identifiers_are_masked_but_ordinary_figures_are_not(self):
        text = "CNIC 42101-1234567-8, IBAN PK36MEZN0000001234567890, mail a.b@x.com, mobile 0300-1234567, acct 123456789012"
        masked = mask_sensitive(text)
        for raw in ("42101-1234567-8", "PK36MEZN0000001234567890", "a.b@x.com", "0300-1234567", "123456789012"):
            self.assertNotIn(raw, masked)
        self.assertEqual(mask_sensitive("Pool POOL-GEN-01 on 2026-09-30 earned PKR 1,300,000.50"), "Pool POOL-GEN-01 on 2026-09-30 earned PKR 1,300,000.50")
