from datetime import date

from rest_framework.test import APITestCase

from apps.accounts.models import UserRole
from apps.circles.models import CircleMember
from apps.circles.tests import CircleRotationApiTests
from apps.core.context import set_current_tenant

from .models import Pool, PoolStatus


class PoolLifecycleTests(APITestCase):
    """Freeze / unfreeze / archive (BRD pool states frozen and archived)."""

    authenticate = CircleRotationApiTests.authenticate
    _make_pool = CircleRotationApiTests._make_pool

    def setUp(self):
        CircleRotationApiTests.setUp(self)
        set_current_tenant(self.tenant)
        Pool.objects.filter(pk=self.pool.pk).update(status=PoolStatus.OPEN)
        self.pool.refresh_from_db()
        self.member = CircleMember.objects.create(
            tenant=self.tenant, pool=self.pool, member_name="M", member_reference="M-1", joined_date=date(2026, 1, 1)
        )
        self.url = f"/api/v1/pools/pools/{self.pool.id}/"

    def tearDown(self):
        set_current_tenant(None)

    def freeze(self, reason="Suspected data breach under review"):
        self.authenticate(self.pool_manager)
        return self.client.post(self.url + "freeze/", {"reason": reason}, format="json")

    def test_freeze_needs_a_reason_and_an_open_pool(self):
        self.assertEqual(self.freeze("short").status_code, 400)
        self.assertEqual(self.freeze().status_code, 200)
        self.assertEqual(self.freeze().status_code, 400)  # already frozen
        self.pool.refresh_from_db()
        self.assertEqual(self.pool.status, PoolStatus.FROZEN)
        self.assertEqual(self.pool.frozen_by, self.pool_manager)

    def test_a_frozen_pool_refuses_money_movements(self):
        self.freeze()
        self.authenticate(self.maker)
        response = self.client.post(
            f"/api/v1/circles/circle-members/{self.member.id}/record-contribution/",
            {"amount": "1000", "contribution_date": "2026-02-01", "cycle_number": 1, "payment_reference": "R-1"},
            format="json",
        )
        self.assertEqual(response.status_code, 409, response.content)
        self.assertIn("frozen", str(response.data).lower())

    def test_only_a_different_person_can_unfreeze(self):
        self.freeze()
        # The checker is allowed to lift a freeze, but not one they applied themselves.
        Pool._base_manager.filter(pk=self.pool.pk).update(frozen_by=self.checker)
        self.authenticate(self.checker)
        own = self.client.post(self.url + "unfreeze/", {"reason": "Review completed, risk cleared"}, format="json")
        self.assertEqual(own.status_code, 409, own.content)
        Pool._base_manager.filter(pk=self.pool.pk).update(frozen_by=self.pool_manager)
        ok = self.client.post(self.url + "unfreeze/", {"reason": "Review completed, risk cleared"}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        self.pool.refresh_from_db()
        self.assertEqual(self.pool.status, PoolStatus.OPEN)

    def test_staff_without_the_role_cannot_freeze_or_unfreeze(self):
        self.authenticate(self.maker)
        self.assertEqual(self.client.post(self.url + "freeze/", {"reason": "Not allowed to do this"}, format="json").status_code, 403)
        self.freeze()
        self.authenticate(self.maker)
        self.assertEqual(self.client.post(self.url + "unfreeze/", {"reason": "Not allowed to do this"}, format="json").status_code, 403)

    def test_only_a_closed_pool_can_be_archived_and_archived_pools_stay_blocked(self):
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(self.url + "archive/").status_code, 400)
        self.assertEqual(self.client.post(self.url + "close/").status_code, 200)
        self.assertEqual(self.client.post(self.url + "archive/").status_code, 200)
        self.pool.refresh_from_db()
        self.assertEqual(self.pool.status, PoolStatus.ARCHIVED)
        self.assertEqual(UserRole.FINANCE_CHECKER, self.checker.role)
