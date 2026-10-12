from datetime import date

from rest_framework.test import APIClient

from apps.allocation.test_participant_ledger import ParticipantLedgerTestBase

from .models import Asset, AssetAssignment, AssetStatus, AssetType, Pool


class AssetRuleTests(ParticipantLedgerTestBase):
    def setUp(self):
        super().setUp()
        self.pool2 = Pool.objects.create(
            tenant=self.tenant, name="Second", code="P2", product=self.pool.product, status="open",
            effective_date=date(2026, 1, 1),
        )
        self.asset = Asset.objects.create(
            tenant=self.tenant, reference_code="A-1", asset_type=AssetType.IJARAH, description="x", face_value=1000
        )
        self.api = APIClient()
        self.api.force_authenticate(self.pool_manager)
        self.api.credentials(HTTP_X_TENANT_CODE=self.tenant.code)

    def assign(self, pool, day="2026-03-01", asset=None):
        return self.api.post(
            "/api/v1/pools/asset-assignments/",
            {"asset": str((asset or self.asset).id), "pool": str(pool.id), "assigned_date": day},
            format="json",
        )

    def test_asset_type_must_be_eligible_for_the_product(self):
        product = self.pool.product
        product.eligible_asset_types = ["murabahah"]
        product.save()
        response = self.assign(self.pool)
        self.assertEqual(response.status_code, 400)
        self.assertIn("not eligible", str(response.data))
        product.eligible_asset_types = ["ijarah"]
        product.save()
        self.assertEqual(self.assign(self.pool).status_code, 201)

    def test_matured_or_written_off_assets_cannot_be_assigned(self):
        self.asset.status = AssetStatus.WRITTEN_OFF
        self.asset.save()
        self.assertEqual(self.assign(self.pool).status_code, 400)
        self.asset.status = AssetStatus.AVAILABLE
        self.asset.maturity_date = date(2026, 2, 1)
        self.asset.save()
        self.assertEqual(self.assign(self.pool).status_code, 400)

    def test_transfer_is_effective_dated_without_gap_or_overlap(self):
        first = self.assign(self.pool).data
        response = self.api.post(
            f"/api/v1/pools/asset-assignments/{first['id']}/transfer/",
            {"to_pool": str(self.pool2.id), "effective_date": "2026-03-15", "reason": "Rebalance"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        old = AssetAssignment._base_manager.get(id=first["id"])
        self.assertEqual(old.unassigned_date, date(2026, 3, 14))
        new = AssetAssignment._base_manager.get(id=response.data["id"])
        self.assertEqual((new.pool_id, new.assigned_date, new.unassigned_date), (self.pool2.id, date(2026, 3, 15), None))
        self.assertEqual(new.transferred_from_id, old.id)

    def test_transfer_needs_reason_and_a_later_date(self):
        first = self.assign(self.pool).data
        url = f"/api/v1/pools/asset-assignments/{first['id']}/transfer/"
        body = {"to_pool": str(self.pool2.id), "effective_date": "2026-03-15", "reason": ""}
        self.assertEqual(self.api.post(url, body, format="json").status_code, 400)
        body.update(reason="ok", effective_date="2026-03-01")
        self.assertEqual(self.api.post(url, body, format="json").status_code, 400)
