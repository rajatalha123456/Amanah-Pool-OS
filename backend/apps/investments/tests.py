from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.core.models import AuditLog
from apps.pools.models import Pool
from apps.products.models import ContractTemplate, Product
from apps.tenants.models import Tenant

from .models import CapitalAccount, InvestorProfile, KYCStatus, NAVSnapshot, NAVSnapshotStatus


class InvestorProfileAndSubscriptionApiTests(APITestCase):
	def setUp(self):
		self.tenant = Tenant.objects.create(
			name="Investment Test Tenant", code="INV-TEST", data_residency="PK"
		)
		set_current_tenant(self.tenant)
		self.maker = User.objects.create_user(
			email="maker@example.com",
			password="password",
			full_name="Finance Maker",
			role=UserRole.FINANCE_MAKER,
			tenant=self.tenant,
		)
		self.risk = User.objects.create_user(
			email="risk@example.com",
			password="password",
			full_name="Risk Compliance",
			role=UserRole.RISK_COMPLIANCE,
			tenant=self.tenant,
		)
		contract = ContractTemplate.objects.create(
			tenant=self.tenant,
			name="Investment Contract",
			contract_type="mudarabah_unrestricted",
			version="1",
			clauses={},
		)
		product = Product.objects.create(
			tenant=self.tenant,
			name="Investment Product",
			code="INV-PRODUCT",
			operating_model="investment_pool",
			contract_template=contract,
		)
		self.pool = Pool.objects.create(
			tenant=self.tenant,
			name="Investment Pool",
			code="INV-POOL",
			product=product,
			effective_date=date(2026, 1, 1),
		)
		self.account = CapitalAccount.objects.create(
			tenant=self.tenant,
			pool=self.pool,
			investor_name="Test Investor",
			investor_reference="INV-001",
		)
		self.profile_url = reverse("investor-profile-list")
		self.account_url = reverse("capital-account-detail", args=[self.account.id])

	def tearDown(self):
		set_current_tenant(None)

	def authenticate(self, user):
		self.client.force_authenticate(user=user)
		self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

	def profile_payload(self):
		return {
			"capital_account": str(self.account.id),
			"id_document_type": "passport",
			"id_document_number": "P-12345",
			"date_of_birth": "1985-04-10",
			"address": "1 Investor Street",
			"risk_tolerance": "moderate",
			"suitability_assessment_notes": "Initial assessment",
		}

	def test_kyc_is_required_before_subscription_and_verification_unlocks_it(self):
		self.authenticate(self.maker)
		profile_response = self.client.post(self.profile_url, self.profile_payload(), format="json")
		self.assertEqual(profile_response.status_code, status.HTTP_201_CREATED)

		blocked = self.client.post(
			f"{self.account_url}subscribe/",
			{"amount": "100.00", "transaction_date": "2026-09-18"},
			format="json",
		)
		self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("KYC verification required", str(blocked.data))

		self.authenticate(self.risk)
		verify_url = reverse("investor-profile-detail", args=[profile_response.data["id"]])
		verified = self.client.post(
			f"{verify_url}verify-kyc/",
			{"kyc_status": "verified", "notes": "Documents checked."},
			format="json",
		)
		self.assertEqual(verified.status_code, status.HTTP_200_OK)
		self.assertEqual(verified.data["kyc_status"], "verified")

		NAVSnapshot.objects.create(
			tenant=self.tenant,
			pool=self.pool,
			valuation_date=date(2026, 9, 17),
			total_pool_value="10000.00",
			total_units_outstanding="100.000000",
			nav_per_unit="100.000000",
			status=NAVSnapshotStatus.PUBLISHED,
		)
		self.authenticate(self.maker)
		subscribed = self.client.post(
			f"{self.account_url}subscribe/",
			{"amount": "100.00", "transaction_date": "2026-09-18"},
			format="json",
		)
		self.assertEqual(subscribed.status_code, status.HTTP_201_CREATED)

	def test_only_risk_compliance_can_verify_kyc(self):
		self.authenticate(self.maker)
		profile_response = self.client.post(self.profile_url, self.profile_payload(), format="json")
		verify_url = reverse("investor-profile-detail", args=[profile_response.data["id"]])
		forbidden = self.client.post(
			f"{verify_url}verify-kyc/", {"kyc_status": "verified"}, format="json"
		)
		self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

	def test_shariah_approval_reduces_all_active_accounts_proportionally(self):
		shariah = User.objects.create_user(
			email="shariah@example.com",
			password="password",
			full_name="Shariah Board",
			role=UserRole.SHARIAH_BOARD,
			tenant=self.tenant,
		)
		self.account.units_held = "100.000000"
		self.account.save(update_fields=["units_held", "updated_at"])
		second_account = CapitalAccount.objects.create(
			tenant=self.tenant,
			pool=self.pool,
			investor_name="Second Investor",
			investor_reference="INV-002",
			units_held="300.000000",
		)
		NAVSnapshot.objects.create(
			tenant=self.tenant,
			pool=self.pool,
			valuation_date=date(2026, 9, 18),
			total_pool_value="10000.00",
			total_units_outstanding="400.000000",
			nav_per_unit="25.000000",
			status=NAVSnapshotStatus.PUBLISHED,
		)

		self.authenticate(self.maker)
		create_response = self.client.post(
			reverse("impairment-event-list"),
			{
				"pool": str(self.pool.id),
				"valuation_date": "2026-09-18",
				"loss_amount": "1000.00",
				"reason": "Portfolio asset impairment",
			},
			format="json",
		)
		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(create_response.data["loss_percentage"], "10.000000")

		self.authenticate(shariah)
		approve_response = self.client.post(
			f"{reverse('impairment-event-detail', args=[create_response.data['id']])}approve/",
			format="json",
		)
		self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
		self.assertEqual(approve_response.data["status"], "approved")

		self.account.refresh_from_db()
		second_account.refresh_from_db()
		self.assertEqual(str(self.account.units_held), "90.000000")
		self.assertEqual(str(second_account.units_held), "270.000000")
		self.assertEqual(
			self.account.units_held + second_account.units_held,
			Decimal("360.000000"),
		)
		self.assertEqual(
			AuditLog.objects.filter(
				model_name="CapitalAccount", action="impairment_reduce_units"
			).count(),
			2,
		)


class CapitalAccountDetailApiTests(APITestCase):
	def setUp(self):
		self.tenant = Tenant.objects.create(
			name="Detail Test Tenant", code="DETAIL-TEST", data_residency="PK"
		)
		set_current_tenant(self.tenant)
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
		contract = ContractTemplate.objects.create(
			tenant=self.tenant,
			name="Detail Contract",
			contract_type="mudarabah_unrestricted",
			version="1",
			clauses={},
		)
		product = Product.objects.create(
			tenant=self.tenant,
			name="Detail Product",
			code="DETAIL-PRODUCT",
			operating_model="investment_pool",
			contract_template=contract,
		)
		self.pool = Pool.objects.create(
			tenant=self.tenant,
			name="Detail Pool",
			code="DETAIL-POOL",
			product=product,
			effective_date=date(2026, 1, 1),
		)
		self.account = CapitalAccount.objects.create(
			tenant=self.tenant,
			pool=self.pool,
			investor_name="Detail Investor",
			investor_reference="DET-001",
		)
		InvestorProfile.objects.create(
			tenant=self.tenant,
			capital_account=self.account,
			kyc_status=KYCStatus.VERIFIED,
			id_document_type="passport",
			id_document_number="P-99999",
			date_of_birth="1990-01-01",
			address="1 Detail Street",
			risk_tolerance="moderate",
		)
		NAVSnapshot.objects.create(
			tenant=self.tenant,
			pool=self.pool,
			valuation_date=date(2026, 9, 1),
			total_pool_value="10000.00",
			total_units_outstanding="100.000000",
			nav_per_unit="100.000000",
			status=NAVSnapshotStatus.PUBLISHED,
		)

	def tearDown(self):
		set_current_tenant(None)

	def authenticate(self, user):
		self.client.force_authenticate(user=user)
		self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

	def test_account_detail_subscription_and_redemption_history(self):
		self.authenticate(self.maker)
		account_url = reverse("capital-account-detail", args=[self.account.id])

		subscribe_response = self.client.post(
			f"{account_url}subscribe/",
			{"amount": "500.00", "transaction_date": "2026-09-10"},
			format="json",
		)
		self.assertEqual(subscribe_response.status_code, status.HTTP_201_CREATED)

		self.authenticate(self.checker)
		redeem_response = self.client.post(
			f"{account_url}redeem/",
			{"units_redeemed": "2.000000", "transaction_date": "2026-09-15"},
			format="json",
		)
		self.assertEqual(redeem_response.status_code, status.HTTP_201_CREATED)

		self.authenticate(self.maker)
		detail_response = self.client.get(account_url)
		self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
		self.assertEqual(detail_response.data["units_held"], "3.000000")

		subscriptions_response = self.client.get(
			reverse("subscription-list"), {"capital_account": str(self.account.id)}
		)
		self.assertEqual(subscriptions_response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(subscriptions_response.data), 1)
		self.assertEqual(subscriptions_response.data[0]["amount"], "500.00")

		redemptions_response = self.client.get(
			reverse("redemption-list"), {"capital_account": str(self.account.id)}
		)
		self.assertEqual(redemptions_response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(redemptions_response.data), 1)
		self.assertEqual(redemptions_response.data[0]["units_redeemed"], "2.000000")

# Create your tests here.
