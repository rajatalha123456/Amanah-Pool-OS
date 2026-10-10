from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.pools.models import Pool
from apps.products.models import ContractTemplate, Product, ShariahDecision, ShariahDecisionStatus
from apps.tenants.models import Tenant

from .models import CircleMember, CircleMemberStatus


class CircleRotationApiTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Circle Test Tenant", code="CIRCLE-TEST", data_residency="PK"
        )
        set_current_tenant(self.tenant)

        self.pool_manager = User.objects.create_user(
            email="pm@example.com",
            password="password",
            full_name="Pool Manager",
            role=UserRole.POOL_MANAGER,
            tenant=self.tenant,
        )
        self.maker = User.objects.create_user(
            email="maker@example.com",
            password="password",
            full_name="Finance Maker",
            role=UserRole.FINANCE_MAKER,
            tenant=self.tenant,
        )
        self.checker = User.objects.create_user(
            email="checker@example.com",
            password="password",
            full_name="Finance Checker",
            role=UserRole.FINANCE_CHECKER,
            tenant=self.tenant,
        )

        self.risk = User.objects.create_user(
            email="risk@example.com",
            password="password",
            full_name="Risk Officer",
            role=UserRole.RISK_COMPLIANCE,
            tenant=self.tenant,
        )

        self.pool = self._make_pool(self.tenant, "CIR-1")

        self.other_tenant = Tenant.objects.create(
            name="Other Tenant", code="CIRCLE-OTHER", data_residency="PK"
        )
        self.other_pool_manager = User.objects.create_user(
            email="other-pm@example.com",
            password="password",
            full_name="Other Pool Manager",
            role=UserRole.POOL_MANAGER,
            tenant=self.other_tenant,
        )
        set_current_tenant(self.other_tenant)
        self.other_pool = self._make_pool(self.other_tenant, "CIR-OTHER")
        set_current_tenant(self.tenant)

    def tearDown(self):
        set_current_tenant(None)

    def authenticate(self, user, tenant=None):
        self.client.force_authenticate(user=user)
        self.client.defaults["HTTP_X_TENANT_CODE"] = (tenant or user.tenant).code

    def _make_pool(self, tenant, code_suffix):
        decision = ShariahDecision.objects.create(
            tenant=tenant,
            decision_code="SD-CIRCLE-1" if code_suffix == "CIR-1" else f"SD-{code_suffix}",
            title="Qard circle approval",
            description="Approved",
            status=ShariahDecisionStatus.APPROVED,
            effective_date=date(2026, 1, 1),
        )
        contract = ContractTemplate.objects.create(
            tenant=tenant,
            name=f"Contract {code_suffix}",
            contract_type="qard",
            version="1",
            clauses={},
            shariah_decision=decision,
        )
        product = Product.objects.create(
            tenant=tenant,
            name=f"Product {code_suffix}",
            code=f"PRODUCT-{code_suffix}",
            operating_model="community_circle",
            contract_template=contract,
        )
        pool = Pool.objects.create(
            tenant=tenant,
            name=f"Pool {code_suffix}",
            code=f"POOL-{code_suffix}",
            product=product,
            effective_date=date(2026, 1, 1),
        )
        return pool

    def _create_member(self, pool, reference):
        self.authenticate(self.pool_manager)
        response = self.client.post(
            reverse("circle-member-list"),
            {
                "pool": str(pool.id),
                "member_name": f"Member {reference}",
                "member_reference": reference,
                "joined_date": "2026-09-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["id"]

    def test_full_rotation_flow(self):
        member_ids = [self._create_member(self.pool, f"MEM-{i}") for i in range(1, 6)]

        # Wrong role cannot run the draw.
        self.authenticate(self.checker)
        forbidden_draw = self.client.post(
            reverse("circle-member-run-draw", args=[str(self.pool.id)])
        )
        self.assertEqual(forbidden_draw.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate(self.pool_manager)
        draw_response = self.client.post(
            reverse("circle-member-run-draw", args=[str(self.pool.id)])
        )
        self.assertEqual(draw_response.status_code, status.HTTP_200_OK)
        self.assertIn("seed", draw_response.data)
        assignments = draw_response.data["assignments"]
        self.assertEqual(len(assignments), 5)

        positions = sorted(a["position"] for a in assignments)
        self.assertEqual(positions, [1, 2, 3, 4, 5])
        assigned_member_ids = {a["member_id"] for a in assignments}
        self.assertEqual(assigned_member_ids, set(member_ids))

        set_current_tenant(self.tenant)
        members_by_position = {
            m.payout_position: m for m in CircleMember.objects.filter(pool=self.pool)
        }
        first_turn_member = members_by_position[1]
        second_turn_member = members_by_position[2]

        # Record contributions for cycle 1 for every member except the
        # second-turn member, to exercise the "not everyone contributed"
        # check below.
        self.authenticate(self.maker)
        for position, member in members_by_position.items():
            if member.id == second_turn_member.id:
                continue
            contrib_response = self.client.post(
                reverse("circle-member-record-contribution", args=[str(member.id)]),
                {"amount": "1000.00", "contribution_date": "2026-09-05", "cycle_number": 1},
                format="json",
            )
            self.assertEqual(contrib_response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(contrib_response.data["status"], "received")

        request_url = reverse("circle-payout-request-payout", args=[str(self.pool.id)])
        body = {"member_id": str(first_turn_member.id), "settlement_rail": "raast_rtgs", "payout_date": "2026-09-10"}

        # Wrong role cannot request a payout.
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(request_url, body, format="json").status_code, status.HTTP_403_FORBIDDEN)

        # Wrong member (not first turn) is refused even though they are a valid member.
        self.authenticate(self.maker)
        wrong_turn = self.client.post(
            request_url, {**body, "member_id": str(second_turn_member.id)}, format="json"
        )
        self.assertEqual(wrong_turn.status_code, status.HTTP_400_BAD_REQUEST)

        # The first-turn member can't be paid: one member hasn't contributed, and KYC/bank details are missing.
        blocked = self.client.post(request_url, body, format="json")
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
        failed_text = " ".join(str(item) for item in blocked.data["error"]["details"]["preflight"])
        self.assertIn("contributed", failed_text)
        self.assertIn("KYC", failed_text)

        # Record the missing contribution; KYC (Risk) and bank details are still missing.
        contrib_response = self.client.post(
            reverse("circle-member-record-contribution", args=[str(second_turn_member.id)]),
            {"amount": "1000.00", "contribution_date": "2026-09-05", "cycle_number": 1},
            format="json",
        )
        self.assertEqual(contrib_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.client.post(request_url, body, format="json").status_code, status.HTTP_400_BAD_REQUEST)

        set_current_tenant(self.tenant)
        first_turn_member.iban = "PK36MEZN0001001234567801"
        first_turn_member.bank_name = "Meezan Bank Ltd"
        first_turn_member.save()
        # Only Risk & Compliance can verify KYC.
        kyc_url = reverse("circle-member-verify-kyc", args=[str(first_turn_member.id)])
        self.authenticate(self.maker)
        self.assertEqual(self.client.post(kyc_url).status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(self.risk)
        self.assertEqual(self.client.post(kyc_url).status_code, status.HTTP_200_OK)

        # Maker requests; the amount is the collected pot (5 x 1,000), not client input.
        self.authenticate(self.maker)
        requested = self.client.post(request_url, {**body, "amount": "999999.00"}, format="json")
        self.assertEqual(requested.status_code, status.HTTP_201_CREATED, requested.data)
        self.assertEqual(requested.data["status"], "pending")
        self.assertEqual(requested.data["amount"], "5000.00")
        payout_id = requested.data["id"]

        # The requester cannot approve; settlement needs approval first.
        approve_url = reverse("circle-payout-approve", args=[payout_id])
        settle_url = reverse("circle-payout-settle", args=[payout_id])
        self.assertEqual(self.client.post(approve_url).status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(self.checker)
        self.assertEqual(
            self.client.post(settle_url, {"settlement_utr": "RRN1"}, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        approved = self.client.post(approve_url)
        self.assertEqual(approved.status_code, status.HTTP_200_OK, approved.data)
        self.assertEqual(approved.data["status"], "approved")
        self.assertEqual(approved.data["shariah_certificate_number"], "SD-CIRCLE-1")

        # Settlement needs the bank's reference.
        self.authenticate(self.maker)
        self.assertEqual(self.client.post(settle_url, {}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        settled = self.client.post(settle_url, {"settlement_utr": "RAAST-REAL-0001"}, format="json")
        self.assertEqual(settled.status_code, status.HTTP_200_OK, settled.data)
        self.assertEqual(settled.data["status"], "disbursed")
        self.assertEqual(settled.data["settlement_utr"], "RAAST-REAL-0001")
        self.assertEqual(len(settled.data["ceremony_hash"]), 64)

        first_turn_member.refresh_from_db()
        self.assertEqual(first_turn_member.status, "paid_out")

        # A settled payout is final.
        self.authenticate(self.checker)
        self.assertEqual(self.client.post(approve_url).status_code, status.HTTP_400_BAD_REQUEST)

    def test_tenant_isolation_on_run_draw(self):
        self._create_member(self.pool, "TENANT-A-1")

        self.authenticate(self.pool_manager)
        cross_tenant_draw = self.client.post(
            reverse("circle-member-run-draw", args=[str(self.other_pool.id)])
        )
        # `Pool` is itself a TenantScopedModel, so a plain
        # Pool.objects.get(pk=...) while authenticated as this tenant
        # cannot see a pool belonging to a different tenant at all -
        # the view treats that the same as a missing pool (400).
        self.assertEqual(cross_tenant_draw.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tenant_isolation_on_member_list(self):
        self._create_member(self.pool, "LIST-A-1")

        set_current_tenant(self.other_tenant)
        other_member = CircleMember.objects.create(
            tenant=self.other_tenant,
            pool=self.other_pool,
            member_name="Other Member",
            member_reference="LIST-OTHER-1",
            joined_date=date(2026, 9, 1),
            status=CircleMemberStatus.ACTIVE,
        )
        set_current_tenant(self.tenant)

        self.authenticate(self.pool_manager)
        list_response = self.client.get(reverse("circle-member-list"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        returned_ids = {row["id"] for row in list_response.data}
        self.assertNotIn(str(other_member.id), returned_ids)
