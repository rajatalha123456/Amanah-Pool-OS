"""
Logical pool accounts and their mapping to the enterprise GL (BRD Section 10).

Postings name accounts through an `AccountMapping` (pool override -> tenant default); when a
logical account has no mapping the built-in descriptive name is used and the entry carries no
GL code. Activating a pool requires the mapping of every account its operating model posts to
(BR-001), so a live pool never posts to an unmapped account.
"""

from .models import AccountMapping

# key -> (default name, how a per-class / per-pool suffix is added)
ACCOUNTS = {
    "pool_income": "Pool Income",
    "pool_direct_expense": "Pool Direct Expense",
    "distributable_profit": "Pool Distributable Profit",
    "per_reserve": "PER Reserve",
    "irr_reserve": "IRR Reserve",
    "mudarib_payable": "Mudarib Share Payable",
    "depositor_payable": "Depositor Payable",
    "investor_capital": "Investor Capital",
    "investor_profit_payable": "Investor Profit Payable",
    "settlement_receivable": "Settlement Receivable",
    "redemption_payable": "Redemption Payable",
    "rounding_account": "Pool Rounding Account",
    # Payout clearing voucher (optional - the clearing rails are simulated).
    "wht_payable": "Federal Board of Revenue Withholding Tax Payable",
    "zakat_payable": "Central Zakat Collection Account",
    "settlement_clearing": "Raast / 1LINK Settlement Clearing Account",
    "unclaimed_profit": "Unclaimed Depositor Profit Liability",
    # Asset provisions, write-offs and recoveries.
    "provision_expense": "Asset Provision Expense",
    "provision_reserve": "Asset Provision Reserve",
    "asset_portfolio": "Financing Asset Portfolio",
    "pool_cash": "Pool Cash",
    "recovery_income": "Recovery of Written-off Assets",
    # Amounts that cannot be placed yet, each one a named item (accounting/suspense.py).
    "suspense": "Suspense - Unidentified Items",
}

REQUIRED_BY_MODEL = {
    "bank_pool": [
        "pool_income", "pool_direct_expense", "distributable_profit", "per_reserve", "irr_reserve",
        "mudarib_payable", "depositor_payable", "rounding_account",
    ],
    "investment_pool": [
        "pool_income", "pool_direct_expense", "distributable_profit", "mudarib_payable", "investor_capital",
        "investor_profit_payable", "settlement_receivable", "redemption_payable", "rounding_account",
    ],
    "community_circle": [],
}


class ChartResolver:
    """Resolves logical accounts for one tenant/pool with a single query."""

    def __init__(self, tenant_id, pool=None):
        rows = AccountMapping._base_manager.filter(tenant_id=tenant_id)
        self._default = {}
        self._pool = {}
        for row in rows:
            if row.pool_id is None:
                self._default[row.account_key] = row
            elif pool is not None and row.pool_id == pool.id:
                self._pool[row.account_key] = row

    def mapping(self, key):
        return self._pool.get(key) or self._default.get(key)

    def resolve(self, key, suffix=""):
        """Returns (account_name, gl_code) for the logical account `key`."""

        mapped = self.mapping(key)
        base = mapped.gl_name if mapped else ACCOUNTS[key]
        name = f"{base} - {suffix}" if suffix else base
        return name, (mapped.gl_code if mapped else "")


def unmapped_accounts(tenant_id, pool):
    """Logical accounts the pool's operating model posts to that have no mapping yet."""

    resolver = ChartResolver(tenant_id, pool)
    required = REQUIRED_BY_MODEL.get(pool.product.operating_model, [])
    return [key for key in required if resolver.mapping(key) is None]
