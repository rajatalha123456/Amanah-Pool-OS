"""
One small builder per concrete TenantScopedModel, used by
test_comprehensive_isolation.py to create a minimal-but-valid instance of
every tenant-scoped model for a given tenant.

Deliberately not a generic reflection-based factory: several models have a
real dependency chain (Product -> ContractTemplate, Pool -> Product,
CapitalAccount -> Pool, AllocationLine -> AllocationRun -> Pool, etc.) that
is much clearer to express explicitly than to infer from field introspection.

BUILDERS maps "app_label.ModelName" -> callable(tenant) -> saved instance.
Anything that depends on another tenant-scoped row builds (and caches) that
dependency first, keyed by tenant, so a whole tree can be built with a single
top-level call per model without duplicating rows across models that share a
dependency (e.g. Pool is reused by CapitalAccount, WeightageBand, etc.).
"""

from datetime import date
from decimal import Decimal

from apps.accounting.models import (
    IncomeExpenseEvent,
    JournalBatch,
    JournalEntry,
    ReconciliationBatch,
    ReconciliationItem,
)
from apps.allocation.models import (
    AllocationLine,
    AllocationRun,
    DepositorStatement,
    ProfitSharingRatio,
    ReservePolicy,
    WeightageBand,
)
from apps.circles.models import (
    ArrearsRecord,
    CircleMember,
    CircleProposal,
    CircleVote,
    Contribution,
    Payout,
)
from apps.core.models import TenantIsolationTestRecord
from apps.governance.models import (
    ExceptionCase,
    PurificationEntry,
    RelatedPartyTransaction,
    ShariahAuditFinding,
    ShariahAuditPlan,
    SupportRequest,
)
from apps.investments.models import (
    CapitalAccount,
    ImpairmentEvent,
    InvestorProfile,
    NAVSnapshot,
    Redemption,
    Subscription,
)
from apps.pools.models import (
    Asset,
    AssetAssignment,
    BalanceImportBatch,
    DailyBalance,
    PeriodCloseChecklist,
    Pool,
    PoolVersion,
)
from apps.products.models import (
    ContractTemplate,
    JurisdictionRulePack,
    Product,
    ShariahDecision,
    ShariahQuorumVote,
)

_D = date(2026, 1, 1)


class _Cache:
    """Per-tenant memoized dependency builder, scoped to one call tree."""

    def __init__(self, tenant):
        self.tenant = tenant
        self._built = {}

    def get(self, key, builder):
        if key not in self._built:
            self._built[key] = builder()
        return self._built[key]

    def contract_template(self):
        return self.get(
            "contract_template",
            lambda: ContractTemplate.objects.create(
                tenant=self.tenant,
                name=f"Template {self.tenant.code}",
                contract_type="mudarabah_unrestricted",
                version="1",
                clauses={},
            ),
        )

    def product(self):
        return self.get(
            "product",
            lambda: Product.objects.create(
                tenant=self.tenant,
                name=f"Product {self.tenant.code}",
                code=f"PROD-{self.tenant.code}",
                operating_model="investment_pool",
                contract_template=self.contract_template(),
            ),
        )

    def pool(self):
        return self.get(
            "pool",
            lambda: Pool.objects.create(
                tenant=self.tenant,
                name=f"Pool {self.tenant.code}",
                code=f"POOL-{self.tenant.code}",
                product=self.product(),
                effective_date=_D,
            ),
        )

    def asset(self):
        return self.get(
            "asset",
            lambda: Asset.objects.create(
                tenant=self.tenant,
                reference_code=f"ASSET-{self.tenant.code}",
                asset_type="murabahah",
                description="Test asset",
                face_value=Decimal("1000.00"),
            ),
        )

    def allocation_run(self):
        return self.get(
            "allocation_run",
            lambda: AllocationRun.objects.create(
                tenant=self.tenant,
                pool=self.pool(),
                value_date=_D,
                gross_income=Decimal("1000.00"),
                distributable_amount=Decimal("900.00"),
                total_weighted_funds=Decimal("100000.00"),
                depositor_pool_share=Decimal("700.00"),
                mudarib_share=Decimal("300.00"),
            ),
        )

    def journal_batch(self):
        return self.get(
            "journal_batch",
            lambda: JournalBatch.objects.create(
                tenant=self.tenant,
                allocation_run=self.allocation_run(),
                pool=self.pool(),
                batch_date=_D,
                total_debit=Decimal("100.00"),
                total_credit=Decimal("100.00"),
            ),
        )

    def capital_account(self):
        return self.get(
            "capital_account",
            lambda: CapitalAccount.objects.create(
                tenant=self.tenant,
                pool=self.pool(),
                investor_name=f"Investor {self.tenant.code}",
                investor_reference=f"INV-{self.tenant.code}",
            ),
        )

    def circle_member(self):
        return self.get(
            "circle_member",
            lambda: CircleMember.objects.create(
                tenant=self.tenant,
                pool=self.pool(),
                member_name=f"Member {self.tenant.code}",
                member_reference=f"MEM-{self.tenant.code}",
                joined_date=_D,
            ),
        )

    def circle_proposal(self):
        return self.get(
            "circle_proposal",
            lambda: CircleProposal.objects.create(
                tenant=self.tenant,
                pool=self.pool(),
                title="Proposal",
                description="Description",
                proposal_type="amount_change",
                voting_deadline=_D,
            ),
        )

    def reconciliation_batch(self):
        return self.get(
            "reconciliation_batch",
            lambda: ReconciliationBatch.objects.create(
                tenant=self.tenant,
                pool=self.pool(),
                reconciliation_date=_D,
                total_records=10,
                matched_records=10,
                variance_amount=Decimal("0.00"),
                status="matched",
            ),
        )

    def shariah_audit_plan(self):
        return self.get(
            "shariah_audit_plan",
            lambda: ShariahAuditPlan.objects.create(
                tenant=self.tenant,
                plan_year=2026,
                title=f"Plan {self.tenant.code}",
                scope="All pools",
                target_samples_count=50,
            ),
        )


def _build_product(tenant, cache):
    return cache.product()


def _build_contract_template(tenant, cache):
    return cache.contract_template()


def _build_shariah_decision(tenant, cache):
    return ShariahDecision.objects.create(
        tenant=tenant,
        decision_code=f"SD-{tenant.code}",
        title="Decision",
        description="Description",
        effective_date=_D,
    )


def _build_shariah_quorum_vote(tenant, cache):
    # Reuse the tenant's single ShariahDecision (built just before this one)
    # so the "exactly one row per model" isolation check still holds.
    decision = ShariahDecision._base_manager.filter(tenant=tenant).first()
    return ShariahQuorumVote.objects.create(
        tenant=tenant,
        decision=decision,
        scholar_name="Scholar",
        scholar_title="Mufti",
        digital_signature_hash="0" * 64,
    )


def _build_pool(tenant, cache):
    return cache.pool()


def _build_pool_version(tenant, cache):
    return PoolVersion.objects.create(
        tenant=tenant, pool=cache.pool(), version_number=1, snapshot={}
    )


def _build_asset(tenant, cache):
    return cache.asset()


def _build_asset_assignment(tenant, cache):
    return AssetAssignment.objects.create(
        tenant=tenant, asset=cache.asset(), pool=cache.pool(), assigned_date=_D
    )


def _build_daily_balance(tenant, cache):
    return DailyBalance.objects.create(
        tenant=tenant,
        pool=cache.pool(),
        participant_class="savings_tier_a",
        value_date=_D,
        balance_amount=Decimal("1000.00"),
    )


def _build_balance_import_batch(tenant, cache):
    return BalanceImportBatch.objects.create(
        tenant=tenant, pool=cache.pool(), value_date=_D, total_records=1
    )


def _build_weightage_band(tenant, cache):
    return WeightageBand.objects.create(
        tenant=tenant,
        pool=cache.pool(),
        participant_class="savings_tier_a",
        weightage=Decimal("1.00"),
        effective_from=_D,
    )


def _build_psr(tenant, cache):
    return ProfitSharingRatio.objects.create(
        tenant=tenant,
        pool=cache.pool(),
        depositor_share=Decimal("70.00"),
        mudarib_share=Decimal("30.00"),
        effective_from=_D,
    )


def _build_allocation_run(tenant, cache):
    return cache.allocation_run()


def _build_allocation_line(tenant, cache):
    return AllocationLine.objects.create(
        tenant=tenant,
        allocation_run=cache.allocation_run(),
        participant_class="savings_tier_a",
        daily_funds=Decimal("1000.00"),
        weightage=Decimal("1.00"),
        weighted_funds=Decimal("1000.00"),
        allocated_amount=Decimal("700.00"),
    )


def _build_depositor_statement(tenant, cache):
    return DepositorStatement.objects.create(
        tenant=tenant,
        allocation_run=cache.allocation_run(),
        participant_class="savings_tier_a",
        period_start=_D,
        period_end=_D,
        opening_balance=Decimal("1000.00"),
        profit_allocated=Decimal("70.00"),
        closing_balance=Decimal("1070.00"),
        narrative="Statement",
    )


def _build_journal_batch(tenant, cache):
    return cache.journal_batch()


def _build_journal_entry(tenant, cache):
    return JournalEntry.objects.create(
        tenant=tenant,
        batch=cache.journal_batch(),
        account_name="Profit Expense",
        entry_type="debit",
        amount=Decimal("100.00"),
    )


def _build_income_expense_event(tenant, cache):
    return IncomeExpenseEvent.objects.create(
        tenant=tenant,
        pool=cache.pool(),
        event_type="income",
        category="profit",
        amount=Decimal("100.00"),
        event_date=_D,
        description="Event",
    )


def _build_exception_case(tenant, cache):
    return ExceptionCase.objects.create(
        tenant=tenant,
        source_module="other",
        severity="low",
        title="Exception",
        description="Description",
    )


def _build_purification_entry(tenant, cache):
    return PurificationEntry.objects.create(
        tenant=tenant,
        pool=cache.pool(),
        source_description="Non-halal income",
        amount=Decimal("10.00"),
        identified_date=_D,
    )


def _build_related_party_transaction(tenant, cache):
    return RelatedPartyTransaction.objects.create(
        tenant=tenant,
        pool=cache.pool(),
        related_party_name="Related Co",
        relationship_type="director",
        transaction_type="loan",
        amount=Decimal("100.00"),
        transaction_date=_D,
    )


def _build_support_request(tenant, cache):
    return SupportRequest.objects.create(
        tenant=tenant,
        request_type="general_complaint",
        subject="Subject",
        description="Description",
        raised_by_name="Someone",
    )


def _build_capital_account(tenant, cache):
    return cache.capital_account()


def _build_investor_profile(tenant, cache):
    return InvestorProfile.objects.create(
        tenant=tenant,
        capital_account=cache.capital_account(),
        id_document_type="national_id",
        id_document_number="12345",
        date_of_birth=_D,
        address="Address",
        risk_tolerance="moderate",
    )


def _build_impairment_event(tenant, cache):
    return ImpairmentEvent.objects.create(
        tenant=tenant,
        pool=cache.pool(),
        valuation_date=_D,
        loss_amount=Decimal("10.00"),
        loss_percentage=Decimal("1.00"),
        reason="Reason",
    )


def _build_subscription(tenant, cache):
    return Subscription.objects.create(
        tenant=tenant,
        capital_account=cache.capital_account(),
        amount=Decimal("1000.00"),
        nav_per_unit=Decimal("10.00"),
        units_allotted=Decimal("100.00"),
        transaction_date=_D,
    )


def _build_nav_snapshot(tenant, cache):
    return NAVSnapshot.objects.create(
        tenant=tenant,
        pool=cache.pool(),
        valuation_date=_D,
        total_pool_value=Decimal("100000.00"),
        total_units_outstanding=Decimal("10000.00"),
        nav_per_unit=Decimal("10.00"),
    )


def _build_redemption(tenant, cache):
    return Redemption.objects.create(
        tenant=tenant,
        capital_account=cache.capital_account(),
        units_redeemed=Decimal("10.00"),
        nav_per_unit=Decimal("10.00"),
        amount=Decimal("100.00"),
        transaction_date=_D,
    )


def _build_circle_member(tenant, cache):
    return cache.circle_member()


def _build_contribution(tenant, cache):
    return Contribution.objects.create(
        tenant=tenant,
        member=cache.circle_member(),
        amount=Decimal("100.00"),
        contribution_date=_D,
        cycle_number=1,
    )


def _build_payout(tenant, cache):
    return Payout.objects.create(
        tenant=tenant,
        member=cache.circle_member(),
        pool=cache.pool(),
        cycle_number=1,
        amount=Decimal("100.00"),
        payout_date=_D,
    )


def _build_circle_proposal(tenant, cache):
    return cache.circle_proposal()


def _build_circle_vote(tenant, cache):
    return CircleVote.objects.create(
        tenant=tenant,
        proposal=cache.circle_proposal(),
        member=cache.circle_member(),
        decision="approve",
    )


def _build_arrears_record(tenant, cache):
    return ArrearsRecord.objects.create(
        tenant=tenant,
        member=cache.circle_member(),
        cycle_number=1,
        expected_amount=Decimal("100.00"),
    )


def _build_tenant_isolation_test_record(tenant, cache):
    return TenantIsolationTestRecord.objects.create(tenant=tenant, label=f"Record {tenant.code}")


def _build_reserve_policy(tenant, cache):
    return ReservePolicy.objects.create(
        tenant=tenant,
        pool=cache.pool(),
        reserve_type="per",
        rate_percentage=Decimal("2.00"),
        cap_percentage=Decimal("5.00"),
        current_balance=Decimal("0.00"),
        is_active=True,
    )


def _build_reconciliation_batch(tenant, cache):
    return cache.reconciliation_batch()


def _build_reconciliation_item(tenant, cache):
    return ReconciliationItem.objects.create(
        tenant=tenant,
        batch=cache.reconciliation_batch(),
        account_reference=f"REF-{tenant.code}",
        cbs_amount=Decimal("500.00"),
        gl_amount=Decimal("500.00"),
        variance=Decimal("0.00"),
        status="matched",
    )


def _build_period_close_checklist(tenant, cache):
    return PeriodCloseChecklist.objects.create(
        tenant=tenant,
        pool=cache.pool(),
        period_start=_D,
        period_end=date(2026, 1, 31),
    )


def _build_shariah_audit_plan(tenant, cache):
    return cache.shariah_audit_plan()


def _build_shariah_audit_finding(tenant, cache):
    return ShariahAuditFinding.objects.create(
        tenant=tenant,
        audit_plan=cache.shariah_audit_plan(),
        title="Sample Finding",
        severity="medium",
        observation="Observation details",
    )


def _build_jurisdiction_rule_pack(tenant, cache):
    return JurisdictionRulePack.objects.create(
        tenant=tenant,
        code=f"JRP-{tenant.code}",
        name=f"Rule Pack {tenant.code}",
        version="2026.01",
        effective_date=_D,
    )


# "app_label.ModelName" -> (model_class, builder(tenant, cache) -> instance)
BUILDERS = {
    "core.TenantIsolationTestRecord": (TenantIsolationTestRecord, _build_tenant_isolation_test_record),
    "products.ShariahDecision": (ShariahDecision, _build_shariah_decision),
    "products.ShariahQuorumVote": (ShariahQuorumVote, _build_shariah_quorum_vote),
    "products.ContractTemplate": (ContractTemplate, _build_contract_template),
    "products.Product": (Product, _build_product),
    "products.JurisdictionRulePack": (JurisdictionRulePack, _build_jurisdiction_rule_pack),
    "pools.Pool": (Pool, _build_pool),
    "pools.PoolVersion": (PoolVersion, _build_pool_version),
    "pools.Asset": (Asset, _build_asset),
    "pools.AssetAssignment": (AssetAssignment, _build_asset_assignment),
    "pools.DailyBalance": (DailyBalance, _build_daily_balance),
    "pools.BalanceImportBatch": (BalanceImportBatch, _build_balance_import_batch),
    "pools.PeriodCloseChecklist": (PeriodCloseChecklist, _build_period_close_checklist),
    "allocation.WeightageBand": (WeightageBand, _build_weightage_band),
    "allocation.ProfitSharingRatio": (ProfitSharingRatio, _build_psr),
    "allocation.AllocationRun": (AllocationRun, _build_allocation_run),
    "allocation.AllocationLine": (AllocationLine, _build_allocation_line),
    "allocation.DepositorStatement": (DepositorStatement, _build_depositor_statement),
    "allocation.ReservePolicy": (ReservePolicy, _build_reserve_policy),
    "accounting.JournalBatch": (JournalBatch, _build_journal_batch),
    "accounting.JournalEntry": (JournalEntry, _build_journal_entry),
    "accounting.IncomeExpenseEvent": (IncomeExpenseEvent, _build_income_expense_event),
    "accounting.ReconciliationBatch": (ReconciliationBatch, _build_reconciliation_batch),
    "accounting.ReconciliationItem": (ReconciliationItem, _build_reconciliation_item),
    "governance.ExceptionCase": (ExceptionCase, _build_exception_case),
    "governance.PurificationEntry": (PurificationEntry, _build_purification_entry),
    "governance.RelatedPartyTransaction": (RelatedPartyTransaction, _build_related_party_transaction),
    "governance.SupportRequest": (SupportRequest, _build_support_request),
    "governance.ShariahAuditPlan": (ShariahAuditPlan, _build_shariah_audit_plan),
    "governance.ShariahAuditFinding": (ShariahAuditFinding, _build_shariah_audit_finding),
    "investments.CapitalAccount": (CapitalAccount, _build_capital_account),
    "investments.InvestorProfile": (InvestorProfile, _build_investor_profile),
    "investments.ImpairmentEvent": (ImpairmentEvent, _build_impairment_event),
    "investments.Subscription": (Subscription, _build_subscription),
    "investments.NAVSnapshot": (NAVSnapshot, _build_nav_snapshot),
    "investments.Redemption": (Redemption, _build_redemption),
    "circles.CircleMember": (CircleMember, _build_circle_member),
    "circles.Contribution": (Contribution, _build_contribution),
    "circles.Payout": (Payout, _build_payout),
    "circles.CircleProposal": (CircleProposal, _build_circle_proposal),
    "circles.CircleVote": (CircleVote, _build_circle_vote),
    "circles.ArrearsRecord": (ArrearsRecord, _build_arrears_record),
}


def build_one_of_each(tenant):
    """Creates one instance of every tenant-scoped model for `tenant`.

    Returns {label: instance}. Shared dependencies (Pool, Product, etc.)
    are created once and reused, so this creates the minimum number of rows
    needed to populate every model at least once.
    """
    cache = _Cache(tenant)
    return {label: builder(tenant, cache) for label, (_, builder) in BUILDERS.items()}
