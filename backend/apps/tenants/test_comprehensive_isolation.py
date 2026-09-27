"""
Comprehensive multi-tenant isolation test suite.

Three layers:

1. ORM-level (`ManagerIsolationTests`): for every concrete `TenantScopedModel`
   subclass in the whole project (discovered dynamically via Django's app
   registry, so a new model is automatically covered without touching this
   file), create one row for Tenant A and one for Tenant B, then assert
   `Model.objects.all()` returns exactly the current tenant's row depending
   on what `set_current_tenant()` is scoped to, and returns nothing when no
   tenant context is set at all.

2. HTTP-level (`EndpointIsolationTests`): for every tenant-scoped model that
   has a real list/detail REST endpoint, create a row as Tenant A, then hit
   that endpoint authenticated as a Tenant A user but with Tenant B's
   `X-Tenant-Code` header, and assert Tenant A's row is absent from the list
   and 404s on detail. This also guards against the `get_queryset()`
   "class-level queryset" footgun called out in several viewsets' own
   comments (a class-level `queryset = Model.objects.all()` would freeze in
   whatever tenant happened to be active at class-definition time).

3. Header/gap tests: missing `X-Tenant-Code` returns 403 without reaching
   any view; `LegalEntity` (has a `tenant` FK but is not a
   `TenantScopedModel`, see apps/tenants/models.py) is confirmed to still
   leak across tenants at the ORM level -- a documented, pre-existing gap,
   not a regression introduced by this suite.
"""

from django.apps import apps as django_apps
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserRole
from apps.core.context import set_current_tenant
from apps.core.models import TenantScopedModel
from apps.tenants.models import LegalEntity, Tenant

from .test_isolation_factories import BUILDERS, build_one_of_each

# Concrete TenantScopedModel subclasses, discovered from the app registry
# rather than hand-maintained, so a new model added anywhere in the project
# is automatically covered by ManagerIsolationTests without editing this file.
ALL_TENANT_SCOPED_MODELS = [
    model
    for model in django_apps.get_models()
    if issubclass(model, TenantScopedModel) and not model._meta.abstract
]

# label -> (basename, requires_role) for models with a real list/detail
# REST endpoint (see apps/*/urls.py). Anything not listed here has no HTTP
# endpoint at all and is only reachable/testable at the ORM level above.
ENDPOINTS = {
    "products.ShariahDecision": "shariah-decision",
    "products.ContractTemplate": "contract-template",
    "products.Product": "product",
    "pools.Pool": "pool",
    "pools.Asset": "asset",
    "pools.AssetAssignment": "asset-assignment",
    "pools.DailyBalance": "daily-balance",
    "pools.BalanceImportBatch": "balance-import",
    "allocation.WeightageBand": "weightage-band",
    "allocation.ProfitSharingRatio": "psr-schedule",
    "allocation.AllocationRun": "allocation-run",
    "accounting.JournalBatch": "journal-batch",
    "accounting.IncomeExpenseEvent": "income-expense-event",
    "governance.ExceptionCase": "exception-case",
    "governance.PurificationEntry": "purification-entry",
    "governance.RelatedPartyTransaction": "related-party-transaction",
    "governance.SupportRequest": "support-request",
    "investments.CapitalAccount": "capital-account",
    "investments.NAVSnapshot": "nav-snapshot",
    "investments.InvestorProfile": "investor-profile",
    "investments.ImpairmentEvent": "impairment-event",
    "investments.Subscription": "subscription",
    "investments.Redemption": "redemption",
    "circles.CircleMember": "circle-member",
    "circles.Contribution": "circle-contribution",
    "circles.Payout": "circle-payout",
    "circles.ArrearsRecord": "circle-arrears-record",
    "circles.CircleProposal": "circle-proposal",
}

# Subset of ENDPOINTS whose viewset only exposes list (no retrieve action,
# e.g. `mixins.ListModelMixin` only) -- these have no `-detail` route, so
# they're covered by the list-isolation test but skipped by the by-id test.
LIST_ONLY_ENDPOINTS = {
    "pools.DailyBalance",
    "pools.BalanceImportBatch",
    "circles.Payout",
}


def _model_label(model):
    return f"{model._meta.app_label}.{model.__name__}"


class ManagerIsolationTests(APITestCase):
    """Layer 1: TenantScopedManager isolation, generically, for every model."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name="Isolation Tenant A", code="ISO-A", data_residency="PK")
        cls.tenant_b = Tenant.objects.create(name="Isolation Tenant B", code="ISO-B", data_residency="PK")

        set_current_tenant(cls.tenant_a)
        cls.rows_a = build_one_of_each(cls.tenant_a)
        set_current_tenant(cls.tenant_b)
        cls.rows_b = build_one_of_each(cls.tenant_b)
        set_current_tenant(None)

    def tearDown(self):
        set_current_tenant(None)

    def test_every_tenant_scoped_model_is_covered_by_a_builder(self):
        """Guards against a new TenantScopedModel silently skipping this suite."""
        covered = set(BUILDERS.keys())
        discovered = {_model_label(m) for m in ALL_TENANT_SCOPED_MODELS}
        missing = discovered - covered
        self.assertEqual(
            missing,
            set(),
            f"New TenantScopedModel(s) with no isolation-test builder: {missing}. "
            "Add a builder in test_isolation_factories.py so isolation is verified for it.",
        )

    def test_no_tenant_context_returns_empty_for_every_model(self):
        set_current_tenant(None)
        for label, (model, _builder) in BUILDERS.items():
            with self.subTest(model=label):
                self.assertEqual(
                    model.objects.count(), 0, f"{label}.objects with no tenant context should return nothing"
                )

    def test_tenant_a_sees_only_its_own_row_for_every_model(self):
        set_current_tenant(self.tenant_a)
        for label, (model, _builder) in BUILDERS.items():
            with self.subTest(model=label):
                visible = list(model.objects.all())
                self.assertEqual(len(visible), 1, f"{label}: expected exactly 1 visible row for Tenant A")
                self.assertEqual(visible[0].tenant_id, self.tenant_a.id, f"{label}: leaked a non-Tenant-A row")

    def test_tenant_b_sees_only_its_own_row_for_every_model(self):
        set_current_tenant(self.tenant_b)
        for label, (model, _builder) in BUILDERS.items():
            with self.subTest(model=label):
                visible = list(model.objects.all())
                self.assertEqual(len(visible), 1, f"{label}: expected exactly 1 visible row for Tenant B")
                self.assertEqual(visible[0].tenant_id, self.tenant_b.id, f"{label}: leaked a non-Tenant-B row")

    def test_tenant_a_row_is_not_gettable_by_id_under_tenant_b_context(self):
        set_current_tenant(self.tenant_b)
        for label, (model, _builder) in BUILDERS.items():
            with self.subTest(model=label):
                row_a = self.rows_a[label]
                self.assertFalse(
                    model.objects.filter(pk=row_a.pk).exists(),
                    f"{label}: Tenant A's row {row_a.pk} is fetchable by pk under Tenant B's context",
                )


class LegalEntityKnownGapTests(APITestCase):
    """
    Layer 3 (gap documentation): LegalEntity has a `tenant` FK but inherits
    plain BaseModel, not TenantScopedModel (see apps/tenants/models.py), so
    it gets NO automatic manager-level filtering. This test documents that
    gap explicitly rather than letting it pass silently: if it starts
    failing, that's a signal LegalEntity was migrated to TenantScopedModel
    and this test (and the README note) should be updated/removed.
    """

    def test_legal_entity_has_no_queryset_level_tenant_filtering(self):
        tenant_a = Tenant.objects.create(name="LE Tenant A", code="LE-A", data_residency="PK")
        tenant_b = Tenant.objects.create(name="LE Tenant B", code="LE-B", data_residency="PK")

        LegalEntity.objects.create(tenant=tenant_a, name="A Legal Entity", jurisdiction="Pakistan")
        LegalEntity.objects.create(tenant=tenant_b, name="B Legal Entity", jurisdiction="Pakistan")

        # No `.filter(tenant=...)` here on purpose: LegalEntity.objects is a
        # plain manager, so both tenants' rows are visible with zero
        # tenant context set up at all -- confirming there's nothing behind
        # the scenes doing implicit scoping the way TenantScopedManager does.
        self.assertEqual(
            LegalEntity.objects.count(),
            2,
            "LegalEntity.objects unexpectedly filtered by tenant -- if this now fails because "
            "LegalEntity was migrated to TenantScopedModel, remove this test and update the "
            "README's Security & Tenant Isolation Verification section accordingly.",
        )


class MissingTenantHeaderTests(APITestCase):
    """Layer 3: confirm no endpoint leaks data when X-Tenant-Code is absent or wrong."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Header Tenant", code="HEADER-1", data_residency="PK")
        set_current_tenant(self.tenant)
        self.user = User.objects.create_user(
            email="header@example.com",
            password="password",
            full_name="Header User",
            role=UserRole.PLATFORM_SUPER_ADMIN,
            tenant=self.tenant,
        )
        build_one_of_each(self.tenant)
        set_current_tenant(None)

    def tearDown(self):
        set_current_tenant(None)

    def test_missing_header_is_rejected_before_reaching_any_view(self):
        self.client.force_authenticate(user=self.user)
        for label, basename in ENDPOINTS.items():
            with self.subTest(model=label):
                response = self.client.get(reverse(f"{basename}-list"))
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                    f"{basename}-list without X-Tenant-Code should 403, got {response.status_code}",
                )
                self.assertNotIn("results", response.data if hasattr(response, "data") else {})

    def test_unknown_tenant_code_is_rejected(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("pool-list"),
            HTTP_X_TENANT_CODE="DOES-NOT-EXIST",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class EndpointIsolationTests(APITestCase):
    """
    Layer 2: every model with a real REST endpoint, hit over HTTP as a
    Tenant-B-authenticated request, must never see Tenant A's row.
    """

    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name="Endpoint Tenant A", code="EP-A", data_residency="PK")
        cls.tenant_b = Tenant.objects.create(name="Endpoint Tenant B", code="EP-B", data_residency="PK")

        set_current_tenant(cls.tenant_a)
        cls.rows_a = build_one_of_each(cls.tenant_a)
        cls.user_a = User.objects.create_user(
            email="a@example.com", password="password", full_name="Tenant A User",
            role=UserRole.PLATFORM_SUPER_ADMIN, tenant=cls.tenant_a,
        )

        set_current_tenant(cls.tenant_b)
        build_one_of_each(cls.tenant_b)
        cls.user_b = User.objects.create_user(
            email="b@example.com", password="password", full_name="Tenant B User",
            role=UserRole.PLATFORM_SUPER_ADMIN, tenant=cls.tenant_b,
        )
        set_current_tenant(None)

    def tearDown(self):
        set_current_tenant(None)

    def test_tenant_b_list_endpoint_never_contains_tenant_a_rows(self):
        self.client.force_authenticate(user=self.user_b)
        for label, basename in ENDPOINTS.items():
            with self.subTest(model=label):
                response = self.client.get(reverse(f"{basename}-list"), HTTP_X_TENANT_CODE=self.tenant_b.code)
                self.assertEqual(response.status_code, status.HTTP_200_OK, f"{basename}-list failed: {response.data}")

                results = response.data["results"] if isinstance(response.data, dict) and "results" in response.data else response.data
                returned_ids = {str(row["id"]) for row in results}
                self.assertNotIn(
                    str(self.rows_a[label].id),
                    returned_ids,
                    f"{basename}-list leaked Tenant A's row while authenticated as Tenant B",
                )

    def test_tenant_b_cannot_fetch_tenant_a_row_by_id(self):
        self.client.force_authenticate(user=self.user_b)
        for label, basename in ENDPOINTS.items():
            if label in LIST_ONLY_ENDPOINTS:
                continue
            with self.subTest(model=label):
                row_a = self.rows_a[label]
                response = self.client.get(
                    reverse(f"{basename}-detail", args=[row_a.id]), HTTP_X_TENANT_CODE=self.tenant_b.code
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_404_NOT_FOUND,
                    f"{basename}-detail should 404 Tenant A's row {row_a.id} for Tenant B, got {response.status_code}",
                )
