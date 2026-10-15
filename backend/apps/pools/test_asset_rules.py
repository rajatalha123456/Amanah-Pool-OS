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

    def propose(self, assignment_id, **extra):
        body = {
            "to_pool": str(self.pool2.id), "effective_date": "2026-03-15", "reason": "Rebalance",
            "valuation": "950.00", "valuation_basis": "Independent valuer report VR-77", **extra,
        }
        return self.api.post(f"/api/v1/pools/asset-assignments/{assignment_id}/transfer/", body, format="json")

    def as_user(self, user):
        client = APIClient()
        client.force_authenticate(user)
        client.credentials(HTTP_X_TENANT_CODE=self.tenant.code)
        return client

    def test_transfer_is_effective_dated_without_gap_or_overlap_once_approved(self):
        first = self.assign(self.pool).data
        response = self.propose(first["id"])
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(response.data["status"], "pending")
        # nothing has moved yet
        self.assertIsNone(AssetAssignment._base_manager.get(id=first["id"]).unassigned_date)

        approved = self.as_user(self.checker).post(f"/api/v1/pools/asset-transfers/{response.data['id']}/approve/")
        self.assertEqual(approved.status_code, 200, approved.data)
        old = AssetAssignment._base_manager.get(id=first["id"])
        self.assertEqual(old.unassigned_date, date(2026, 3, 14))
        new = AssetAssignment._base_manager.get(id=approved.data["new_assignment"])
        self.assertEqual((new.pool_id, new.assigned_date, new.unassigned_date), (self.pool2.id, date(2026, 3, 15), None))
        self.assertEqual(new.transferred_from_id, old.id)
        self.assertEqual(str(new.transfer_valuation), "950.00")
        self.assertIn("VR-77", new.transfer_valuation_basis)

    def test_a_transfer_needs_a_valuation_its_basis_a_reason_a_later_date_and_a_different_approver(self):
        first = self.assign(self.pool).data
        self.assertEqual(self.propose(first["id"], reason="").status_code, 400)
        self.assertEqual(self.propose(first["id"], effective_date="2026-03-01").status_code, 400)
        self.assertEqual(self.propose(first["id"], valuation="0").status_code, 400)
        self.assertEqual(self.propose(first["id"], valuation="").status_code, 400)
        self.assertEqual(self.propose(first["id"], valuation_basis=" ").status_code, 400)

        made = self.propose(first["id"])
        self.assertEqual(made.status_code, 202)
        self.assertEqual(self.propose(first["id"]).status_code, 400, "a second proposal while one is pending")
        url = f"/api/v1/pools/asset-transfers/{made.data['id']}/"
        self.assertEqual(self.as_user(self.pool_manager).post(url + "approve/").status_code, 403)  # not an approver role
        self.assertEqual(self.as_user(self.checker).post(url + "reject/", {}, format="json").status_code, 400)
        rejected = self.as_user(self.checker).post(url + "reject/", {"reason": "Valuation report is stale"}, format="json")
        self.assertEqual(rejected.data["status"], "rejected")
        self.assertIsNone(AssetAssignment._base_manager.get(id=first["id"]).unassigned_date)
        self.assertEqual(self.as_user(self.checker).post(url + "approve/").status_code, 400, "already decided")
