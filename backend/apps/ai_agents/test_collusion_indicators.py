from datetime import date

from django.test import TestCase

from apps.circles.models import CircleMember
from apps.core.context import set_current_tenant
from apps.pools.models import Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .services.collusion_detector import detect_fraud_and_collusion_network


class CollusionIndicatorTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="C", code="COL-T", data_residency="PK")
        set_current_tenant(self.tenant)
        contract = ContractTemplate.objects.create(tenant=self.tenant, name="C", contract_type="qard", version="1", clauses={})
        product = Product.objects.create(tenant=self.tenant, name="P", code="P-C", operating_model="community_circle", contract_template=contract)
        self.pool = Pool.objects.create(tenant=self.tenant, name="Circle", code="CIR-C", product=product, effective_date=date(2026, 1, 1))
        self.members = [
            CircleMember.objects.create(
                tenant=self.tenant, pool=self.pool, member_name=f"M{i}", member_reference=f"M-{i}",
                joined_date=date(2026, 1, 1), iban=f"PK36MEZN00010012345678{i:02d}", email=f"m{i}@x.test",
            )
            for i in range(1, 6)
        ]

    def tearDown(self):
        set_current_tenant(None)

    def test_nothing_is_flagged_without_shared_details(self):
        result = detect_fraud_and_collusion_network(self.tenant, str(self.pool.id))
        self.assertEqual((result["cluster_count"], result["suspicious_member_count"]), (0, 0))
        self.assertEqual(result["graph"]["edges"], [])
        self.assertNotIn("AML", result["investigation_dossier"])

    def test_a_shared_iban_is_reported_as_an_indicator(self):
        self.members[3].iban = self.members[1].iban
        self.members[3].save()
        result = detect_fraud_and_collusion_network(self.tenant, str(self.pool.id))
        self.assertEqual(result["cluster_count"], 1)
        self.assertEqual(result["clusters"][0]["cluster_type"], "SHARED_BANK_ACCOUNT")
        self.assertEqual(sorted(result["clusters"][0]["members"]), ["M2", "M4"])
        self.assertIn("not findings", result["disclaimer"])
