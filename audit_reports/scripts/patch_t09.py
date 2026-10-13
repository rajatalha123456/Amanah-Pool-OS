ROOT = "backend/apps/"


def rd(p):
    return open(ROOT + p, encoding="utf-8").read()


def wr(p, s):
    open(ROOT + p, "w", encoding="utf-8").write(s)


def sub(s, old, new, count=1):
    assert old in s, old[:90]
    return s.replace(old, new, count)


p = "pools/concentration_engine.py"
s = rd(p)
s = sub(s, '''"""
SBP Statutory Single-Obligor & Sector Concentration Risk Engine (BRD Module 12 / Screen 31 - Risk Limit Dashboard)

Implements State Bank of Pakistan (SBP) Prudential Regulations:
- Regulation R-1: Limit on Exposure to a Single Person / Obligor (Fund-based & Non-fund based) <= 15% of Capital/Pool
- Regulation R-1: Limit on Exposure to a Group of Connected Borrowers <= 20%
- Regulation R-6: Exposure to Economic Sectors (Real Estate, Power/Energy, Textiles, Fertilizer, etc.) <= 15% - 25%
- SBP BPRD & AAOIFI FAS-30: Mandatory Shariah Ring-Fencing (0% prohibited sectors)
- Automated Early Warning Indicator (EWI) trigger when exposure reaches >= 80% of limit
- Breach Detection (>= 100%) with automated ExceptionCase logging and remediation proposal
"""''', '''"""
Single-obligor and sector concentration (BRD 5 "Assets: concentration", BRD 13 risk dashboard, Risk Limit Dashboard screen).

The limits are CONFIGURATION: they are read from the jurisdiction rule pack bound to the pool
(`rules_config["concentration_limits_pct"]`). Where the pack does not define a limit, the placeholder defaults below are
used and the result says so (`limits_source`). The placeholders are NOT a statement of any regulator's rule and have not
been confirmed by Risk & Compliance or counsel; the percentages are measured against the pool's own earmarked assets,
not against bank capital. Whoever configures the pack must set the limits that apply to them.

- An early-warning indicator is raised when an exposure reaches 80% of its limit.
- A breach (above 100%) raises an ExceptionCase for review.
"""''')
s = sub(s, '''# SBP Statutory PR Limits Defaults
SBP_SINGLE_OBLIGOR_PRIVATE_LIMIT_PCT = Decimal("15.0")
SBP_SINGLE_OBLIGOR_SOVEREIGN_LIMIT_PCT = Decimal("25.0")
SBP_GROUP_OBLIGOR_LIMIT_PCT = Decimal("20.0")
SBP_REAL_ESTATE_SECTOR_LIMIT_PCT = Decimal("15.0")
SBP_POWER_ENERGY_SECTOR_LIMIT_PCT = Decimal("30.0")
SBP_GENERAL_SECTOR_LIMIT_PCT = Decimal("20.0")
EARLY_WARNING_THRESHOLD_PCT = Decimal("80.0")''', '''# Placeholder defaults used only where the rule pack sets no limit. Not a regulatory statement (see the module docstring).
DEFAULT_LIMITS_PCT = {
    "single_obligor_private": Decimal("15.0"),
    "single_obligor_sovereign": Decimal("25.0"),
    "group_private": Decimal("20.0"),
    "group_sovereign": Decimal("45.0"),
    "sector_real_estate": Decimal("15.0"),
    "sector_power_energy": Decimal("30.0"),
    "sector_sovereign": Decimal("40.0"),
    "sector_general": Decimal("20.0"),
}
EARLY_WARNING_THRESHOLD_PCT = Decimal("80.0")


def resolve_limits(pool: Optional[Pool]):
    """(limits, source): the pool's rule-pack limits, falling back to the placeholder defaults per key."""
    limits, configured = dict(DEFAULT_LIMITS_PCT), False
    if pool is not None:
        from apps.pools.config_snapshot import bound_rule_pack

        pack = bound_rule_pack(pool)
        custom = ((pack.rules_config or {}).get("concentration_limits_pct") or {}) if pack else {}
        for key, value in custom.items():
            if key in limits:
                limits[key], configured = Decimal(str(value)), True
        if configured:
            return limits, f"rule pack {pack.code} (keys not set there use placeholder defaults)"
    return limits, "placeholder defaults - not set in the rule pack and not confirmed by a regulatory source"''')
s = sub(s, '''def get_sector_limit_pct(sector: str) -> Decimal:
    """Returns statutory SBP limit for a given economic sector."""
    s = sector.lower()
    if "real estate" in s or "construction" in s or "property" in s:
        return SBP_REAL_ESTATE_SECTOR_LIMIT_PCT
    if "power" in s or "energy" in s or "utilities" in s:
        return SBP_POWER_ENERGY_SECTOR_LIMIT_PCT
    if "sovereign" in s or "public sector" in s:
        return Decimal("40.0")  # SBP sovereign exposure carveout
    return SBP_GENERAL_SECTOR_LIMIT_PCT''', '''def get_sector_limit_pct(sector: str, limits=None) -> Decimal:
    """The configured limit for an economic sector."""
    limits = limits or DEFAULT_LIMITS_PCT
    s = sector.lower()
    if "real estate" in s or "construction" in s or "property" in s:
        return limits["sector_real_estate"]
    if "power" in s or "energy" in s or "utilities" in s:
        return limits["sector_power_energy"]
    if "sovereign" in s or "public sector" in s:
        return limits["sector_sovereign"]
    return limits["sector_general"]''')
s = sub(s, '''    for asset in assets:
        meta = _infer_asset_metadata(asset)''', '''    limits, limits_source = resolve_limits(pool)

    for asset in assets:
        meta = _infer_asset_metadata(asset)''')
s = sub(s, "limit_pct = SBP_SINGLE_OBLIGOR_SOVEREIGN_LIMIT_PCT if meta[\"is_sovereign\"] else SBP_SINGLE_OBLIGOR_PRIVATE_LIMIT_PCT",
        "limit_pct = limits[\"single_obligor_sovereign\"] if meta[\"is_sovereign\"] else limits[\"single_obligor_private\"]")
s = sub(s, "\"sbp_limit_pct\": SBP_GROUP_OBLIGOR_LIMIT_PCT if not meta[\"is_sovereign\"] else Decimal(\"45.0\"),",
        "\"sbp_limit_pct\": limits[\"group_private\"] if not meta[\"is_sovereign\"] else limits[\"group_sovereign\"],")
s = sub(s, "\"sbp_limit_pct\": get_sector_limit_pct(sector_name),", "\"sbp_limit_pct\": get_sector_limit_pct(sector_name, limits),")
wr(p, s)
print("ok")
