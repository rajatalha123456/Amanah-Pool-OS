from decimal import Decimal

from django.test import TestCase

from apps.core.context import set_current_tenant
from apps.tenants.models import Tenant

from .concentration_engine import _infer_asset_metadata
from .models import Asset


class AssetMetadataTests(TestCase):
    """BRD 5: concentration uses the recorded obligor and sector; only an unrecorded asset falls back to inference."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="AM", code="AM-T", data_residency="PK")
        set_current_tenant(self.tenant)

    def tearDown(self):
        set_current_tenant(None)

    def test_recorded_facts_win_and_inference_is_labelled(self):
        recorded = Asset.objects.create(
            tenant=self.tenant, reference_code="A1", asset_type="ijarah", description="Office building lease",
            face_value=Decimal("100"), obligor_name="Obligor One", obligor_group="Group A", sector="power_energy",
            is_related_party=True, credit_rating="A",
        )
        meta = _infer_asset_metadata(recorded)
        self.assertEqual((meta["obligor_group"], meta["sector"], meta["is_related_party"]), ("Group A", "Power & Energy", True))
        inferred = Asset.objects.create(
            tenant=self.tenant, reference_code="A2", asset_type="ijarah", description="Office building lease", face_value=Decimal("100"),
        )
        self.assertEqual(_infer_asset_metadata(inferred)["sector"], "Real Estate (inferred)")
