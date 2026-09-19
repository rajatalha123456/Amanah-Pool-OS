from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.pools.models import Pool
from apps.products.models import ContractTemplate, ContractType, OperatingModel, Product
from apps.tenants.models import Tenant


class RelatedPartyTransactionApiTests(APITestCase):
	def setUp(self):
		self.tenant = Tenant.objects.create(
			name="Test Tenant", code="TEST", data_residency="PK"
		)
		set_current_tenant(self.tenant)
		self.maker = User.objects.create_user(
			email="maker@example.com",
			password="password",
			full_name="Finance Maker",
			role=UserRole.FINANCE_MAKER,
			tenant=self.tenant,
		)
		self.risk_user = User.objects.create_user(
			email="risk@example.com",
			password="password",
			full_name="Risk Reviewer",
			role=UserRole.RISK_COMPLIANCE,
			tenant=self.tenant,
		)
		self.pool_manager = User.objects.create_user(
			email="manager@example.com",
			password="password",
			full_name="Pool Manager",
			role=UserRole.POOL_MANAGER,
			tenant=self.tenant,
		)
		self.product = Product.objects.create(
			tenant=self.tenant,
			name="Test Product",
			code="TEST-PRODUCT",
			operating_model=OperatingModel.BANK_POOL,
			contract_template=ContractTemplate.objects.create(
				tenant=self.tenant,
				name="Test Contract",
				contract_type=ContractType.MUDARABAH_UNRESTRICTED,
				version="1.0",
				clauses={},
			),
		)
		self.pool = Pool.objects.create(
			tenant=self.tenant,
			name="Test Pool",
			code="TEST-POOL",
			product=self.product,
			effective_date=date(2026, 1, 1),
		)
		self.url = reverse("related-party-transaction-list")

	def tearDown(self):
		set_current_tenant(None)

	def authenticate(self, user):
		self.client.force_authenticate(user=user)
		self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

	def transaction_payload(self):
		return {
			"pool": str(self.pool.id),
			"related_party_name": "Amanah Holdings",
			"relationship_type": "affiliate_company",
			"transaction_type": "Management services",
			"amount": "125000.00",
			"transaction_date": "2026-09-18",
		}

	def test_create_review_approve_and_flag(self):
		self.authenticate(self.maker)
		response = self.client.post(self.url, self.transaction_payload(), format="json")
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		transaction_url = reverse(
			"related-party-transaction-detail", args=[response.data["id"]]
		)

		self.authenticate(self.risk_user)
		approved = self.client.post(
			f"{transaction_url}review/", {"decision": "approved", "notes": "Reviewed."}, format="json"
		)
		self.assertEqual(approved.status_code, status.HTTP_200_OK)
		self.assertEqual(approved.data["disclosure_status"], "approved")

		self.authenticate(self.maker)
		second = self.client.post(self.url, self.transaction_payload(), format="json")
		self.authenticate(self.risk_user)
		flagged = self.client.post(
			f"{reverse('related-party-transaction-detail', args=[second.data['id']])}review/",
			{"decision": "flagged", "notes": "Needs escalation."},
			format="json",
		)
		self.assertEqual(flagged.status_code, status.HTTP_200_OK)
		self.assertEqual(flagged.data["disclosure_status"], "flagged")

	def test_wrong_role_cannot_create_or_review(self):
		self.authenticate(self.risk_user)
		create_response = self.client.post(self.url, self.transaction_payload(), format="json")
		self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

		self.authenticate(self.maker)
		response = self.client.post(self.url, self.transaction_payload(), format="json")
		transaction_url = reverse(
			"related-party-transaction-detail", args=[response.data["id"]]
		)
		forbidden_review = self.client.post(
			f"{transaction_url}review/", {"decision": "approved"}, format="json"
		)
		self.assertEqual(forbidden_review.status_code, status.HTTP_403_FORBIDDEN)


class ExceptionCaseInvestigationLifecycleApiTests(APITestCase):
	def setUp(self):
		self.tenant = Tenant.objects.create(
			name="Exception Test Tenant", code="EXC-TEST", data_residency="PK"
		)
		set_current_tenant(self.tenant)
		self.risk_user = User.objects.create_user(
			email="risk@example.com",
			password="password",
			full_name="Risk Reviewer",
			role=UserRole.RISK_COMPLIANCE,
			tenant=self.tenant,
		)
		self.pool_manager = User.objects.create_user(
			email="manager@example.com",
			password="password",
			full_name="Pool Manager",
			role=UserRole.POOL_MANAGER,
			tenant=self.tenant,
		)

		from apps.governance.models import ExceptionCase, ExceptionSeverity, ExceptionSourceModule

		self.case = ExceptionCase.objects.create(
			tenant=self.tenant,
			source_module=ExceptionSourceModule.OTHER,
			severity=ExceptionSeverity.MEDIUM,
			title="Unusual balance mismatch",
			description="A discrepancy was found during balance import.",
		)
		self.case_url = reverse("exception-case-detail", args=[self.case.id])

	def tearDown(self):
		set_current_tenant(None)

	def authenticate(self, user):
		self.client.force_authenticate(user=user)
		self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

	def test_full_investigation_lifecycle(self):
		self.authenticate(self.risk_user)

		start_response = self.client.post(
			f"{self.case_url}start-investigation/",
			{"investigation_notes": "Reviewing source records for the mismatch."},
			format="json",
		)
		self.assertEqual(start_response.status_code, status.HTTP_200_OK)
		self.assertEqual(start_response.data["status"], "investigating")
		self.assertEqual(
			start_response.data["investigation_notes"], "Reviewing source records for the mismatch."
		)

		treatment_response = self.client.post(
			f"{self.case_url}set-treatment/",
			{"treatment_plan": "Reconcile against the balance import batch and correct the entry."},
			format="json",
		)
		self.assertEqual(treatment_response.status_code, status.HTTP_200_OK)
		self.assertEqual(treatment_response.data["status"], "investigating")
		self.assertEqual(
			treatment_response.data["treatment_plan"],
			"Reconcile against the balance import batch and correct the entry.",
		)

		resolve_response = self.client.post(
			f"{self.case_url}resolve/",
			{"resolution_notes": "Corrected the entry; balances now match."},
			format="json",
		)
		self.assertEqual(resolve_response.status_code, status.HTTP_200_OK)
		self.assertEqual(resolve_response.data["status"], "resolved")

	def test_start_investigation_requires_notes_and_open_status(self):
		self.authenticate(self.risk_user)

		missing_notes = self.client.post(f"{self.case_url}start-investigation/", {}, format="json")
		self.assertEqual(missing_notes.status_code, status.HTTP_400_BAD_REQUEST)

		self.client.post(
			f"{self.case_url}start-investigation/", {"investigation_notes": "Looking into it."}, format="json"
		)
		repeat_attempt = self.client.post(
			f"{self.case_url}start-investigation/", {"investigation_notes": "Again."}, format="json"
		)
		self.assertEqual(repeat_attempt.status_code, status.HTTP_400_BAD_REQUEST)

	def test_set_treatment_requires_investigating_status(self):
		self.authenticate(self.risk_user)

		too_early = self.client.post(
			f"{self.case_url}set-treatment/", {"treatment_plan": "Plan"}, format="json"
		)
		self.assertEqual(too_early.status_code, status.HTTP_400_BAD_REQUEST)

	def test_wrong_role_cannot_start_investigation_or_set_treatment(self):
		self.authenticate(self.pool_manager)

		forbidden_start = self.client.post(
			f"{self.case_url}start-investigation/", {"investigation_notes": "x"}, format="json"
		)
		self.assertEqual(forbidden_start.status_code, status.HTTP_403_FORBIDDEN)

		forbidden_treatment = self.client.post(
			f"{self.case_url}set-treatment/", {"treatment_plan": "x"}, format="json"
		)
		self.assertEqual(forbidden_treatment.status_code, status.HTTP_403_FORBIDDEN)


class RiskDashboardAggregationApiTests(APITestCase):
	"""
	Reproduces the exact sequence of real HTTP requests
	RiskLimitDashboard.tsx makes to compute its StatCards, since it is a
	pure client-side aggregation over existing endpoints with no
	dedicated backend for this dashboard.
	"""

	def setUp(self):
		self.tenant = Tenant.objects.create(
			name="Risk Dashboard Test Tenant", code="RISK-DASH-TEST", data_residency="PK"
		)
		set_current_tenant(self.tenant)
		self.risk_user = User.objects.create_user(
			email="risk@example.com",
			password="password",
			full_name="Risk Reviewer",
			role=UserRole.RISK_COMPLIANCE,
			tenant=self.tenant,
		)
		product = Product.objects.create(
			tenant=self.tenant,
			name="Risk Dashboard Product",
			code="RISK-DASH-PRODUCT",
			operating_model=OperatingModel.BANK_POOL,
			contract_template=ContractTemplate.objects.create(
				tenant=self.tenant,
				name="Risk Dashboard Contract",
				contract_type=ContractType.MUDARABAH_UNRESTRICTED,
				version="1.0",
				clauses={},
			),
		)
		self.pool = Pool.objects.create(
			tenant=self.tenant,
			name="Risk Dashboard Pool",
			code="RISK-DASH-POOL",
			product=product,
			effective_date=date(2026, 1, 1),
		)

		from apps.governance.models import (
			ExceptionCase,
			ExceptionSeverity,
			ExceptionSourceModule,
			PurificationEntry,
			PurificationStatus,
			RelatedPartyDisclosureStatus,
			RelatedPartyTransaction,
			RelatedPartyRelationshipType,
		)

		ExceptionCase.objects.create(
			tenant=self.tenant,
			source_module=ExceptionSourceModule.OTHER,
			severity=ExceptionSeverity.CRITICAL,
			title="Critical open exception",
			description="Needs attention.",
		)
		ExceptionCase.objects.create(
			tenant=self.tenant,
			source_module=ExceptionSourceModule.OTHER,
			severity=ExceptionSeverity.MEDIUM,
			title="Medium open exception",
			description="Also needs attention.",
		)
		ExceptionCase.objects.create(
			tenant=self.tenant,
			source_module=ExceptionSourceModule.OTHER,
			severity=ExceptionSeverity.LOW,
			title="Resolved exception, should not count",
			description="Already handled.",
			status="resolved",
		)

		RelatedPartyTransaction.objects.create(
			tenant=self.tenant,
			pool=self.pool,
			related_party_name="Pending Party",
			relationship_type=RelatedPartyRelationshipType.DIRECTOR,
			transaction_type="loan",
			amount="1000.00",
			transaction_date=date(2026, 9, 1),
			disclosure_status=RelatedPartyDisclosureStatus.PENDING_REVIEW,
		)
		RelatedPartyTransaction.objects.create(
			tenant=self.tenant,
			pool=self.pool,
			related_party_name="Approved Party",
			relationship_type=RelatedPartyRelationshipType.SHAREHOLDER,
			transaction_type="loan",
			amount="2000.00",
			transaction_date=date(2026, 9, 1),
			disclosure_status=RelatedPartyDisclosureStatus.APPROVED,
		)

		PurificationEntry.objects.create(
			tenant=self.tenant,
			pool=self.pool,
			source_description="Incidental interest",
			amount="50.00",
			identified_date=date(2026, 9, 1),
			status=PurificationStatus.IDENTIFIED,
		)
		PurificationEntry.objects.create(
			tenant=self.tenant,
			pool=self.pool,
			source_description="Already distributed",
			amount="25.00",
			identified_date=date(2026, 9, 1),
			status=PurificationStatus.DISTRIBUTED,
		)

	def tearDown(self):
		set_current_tenant(None)

	def authenticate(self, user):
		self.client.force_authenticate(user=user)
		self.client.defaults["HTTP_X_TENANT_CODE"] = self.tenant.code

	def test_dashboard_aggregation_from_real_endpoints(self):
		self.authenticate(self.risk_user)

		exceptions_response = self.client.get(reverse("exception-case-list"), {"status": "open"})
		self.assertEqual(exceptions_response.status_code, status.HTTP_200_OK)
		open_exceptions = exceptions_response.data
		self.assertEqual(len(open_exceptions), 2)

		severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
		for exception in open_exceptions:
			severity_counts[exception["severity"]] += 1
		self.assertEqual(severity_counts, {"low": 0, "medium": 1, "high": 0, "critical": 1})

		related_party_response = self.client.get(reverse("related-party-transaction-list"))
		self.assertEqual(related_party_response.status_code, status.HTTP_200_OK)
		pending_related_party = [
			t for t in related_party_response.data if t["disclosure_status"] == "pending_review"
		]
		self.assertEqual(len(pending_related_party), 1)

		purification_response = self.client.get(reverse("purification-entry-list"))
		self.assertEqual(purification_response.status_code, status.HTTP_200_OK)
		pending_purification = [
			e for e in purification_response.data if e["status"] == "identified"
		]
		self.assertEqual(len(pending_purification), 1)

# Create your tests here.
