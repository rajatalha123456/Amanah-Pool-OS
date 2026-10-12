"""Demo governance configuration: approval matrix, accounting mapping and sealed pool versions (BR-001)."""

from decimal import Decimal

from apps.accounting.chart import ACCOUNTS
from apps.accounting.models import AccountMapping
from apps.accounts.models import ApprovalMatrixRule, UserRole

# logical account -> (GL code, GL account name) for the demo tenant's chart of accounts
GL_CHART = {
    "pool_income": ("4101-001", "Pool Financing Income"),
    "pool_direct_expense": ("5101-001", "Pool Direct Operating Expense"),
    "distributable_profit": ("3101-001", "Pool Distributable Profit Clearing"),
    "per_reserve": ("2301-001", "Profit Equalization Reserve (PER)"),
    "irr_reserve": ("2301-002", "Investment Risk Reserve (IRR)"),
    "mudarib_payable": ("2101-010", "Mudarib Fee Payable"),
    "depositor_payable": ("2101-001", "Pool Depositor Profit Payable"),
    "investor_capital": ("3201-001", "Investment Pool Investor Capital"),
    "investor_profit_payable": ("2101-020", "Investment Pool Investor Profit Payable"),
    "settlement_receivable": ("1201-001", "Subscription Settlement Receivable"),
    "redemption_payable": ("2101-030", "Redemption Payable"),
    "rounding_account": ("4901-001", "Pool Rounding Account"),
    "wht_payable": ("2102-005", "FBR Withholding Tax Payable"),
    "zakat_payable": ("2102-009", "Central Zakat Collection Account"),
    "settlement_clearing": ("1001-002", "Raast / 1LINK Settlement Clearing Account"),
    "unclaimed_profit": ("2109-099", "Unclaimed Depositor Profit Liability"),
    "provision_expense": ("5101-010", "Asset Provision Expense"),
    "provision_reserve": ("2301-010", "Asset Provision Reserve"),
    "asset_portfolio": ("1301-001", "Financing Asset Portfolio"),
    "pool_cash": ("1001-001", "Pool Cash"),
    "recovery_income": ("4101-020", "Recovery of Written-off Assets"),
}

MATRIX = [
    # (action, role, max_amount)
    ("allocation_release", UserRole.AUTHORIZED_SIGNATORY, Decimal("100000000.00")),
    ("distribution_approve", UserRole.FINANCE_CHECKER, Decimal("50000000.00")),
    ("payout_approve", UserRole.FINANCE_CHECKER, Decimal("10000000.00")),
]


def seed_governance_config(tenant):
    for key in ACCOUNTS:
        code, name = GL_CHART[key]
        AccountMapping.objects.get_or_create(
            tenant=tenant, pool=None, account_key=key, defaults={"gl_code": code, "gl_name": name}
        )
    for action, role, limit in MATRIX:
        ApprovalMatrixRule.objects.get_or_create(
            tenant=tenant, action=action, role=role, defaults={"max_amount": limit}
        )


def seal_pool_versions(tenant):
    """Rebuilds each seeded pool's version 1 from the configuration that actually governs it."""

    from apps.pools.config_snapshot import bound_rule_pack, build_pool_snapshot
    from apps.pools.models import Pool, PoolVersion

    for pool in Pool.objects.filter(tenant=tenant):
        if pool.rule_pack_id is None:
            pool.rule_pack = bound_rule_pack(pool)
            pool.save(update_fields=["rule_pack", "updated_at"])
        version = PoolVersion.objects.filter(pool=pool, version_number=1).first()
        if version is not None:
            version.snapshot = build_pool_snapshot(pool, change_rationale="Initial pool structure")
            version.save(update_fields=["snapshot", "updated_at"])
