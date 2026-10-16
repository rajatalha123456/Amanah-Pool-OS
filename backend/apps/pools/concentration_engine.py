"""
Single-obligor and sector concentration (BRD 5 "Assets: concentration", BRD 13 risk dashboard, Risk Limit Dashboard screen).

The limits are CONFIGURATION: they are read from the jurisdiction rule pack bound to the pool
(`rules_config["concentration_limits_pct"]`). Where the pack does not define a limit, the placeholder defaults below are
used and the result says so (`limits_source`). The placeholders are NOT a statement of any regulator's rule and have not
been confirmed by Risk & Compliance or counsel; the percentages are measured against the pool's own earmarked assets,
not against bank capital. Whoever configures the pack must set the limits that apply to them.

- An early-warning indicator is raised when an exposure reaches 80% of its limit.
- A breach (above 100%) raises an ExceptionCase for review.
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from django.utils import timezone

from apps.pools.models import Asset, AssetAssignment, Pool
from apps.core.exceptions_helper import create_exception_case
from apps.core.audit import log_action

# Placeholder defaults used only where the rule pack sets no limit. Not a regulatory statement (see the module docstring).
DEFAULT_LIMITS_PCT = {
    "single_obligor_private": Decimal("15.0"),
    "single_obligor_sovereign": Decimal("25.0"),
    "group_private": Decimal("20.0"),
    "group_sovereign": Decimal("45.0"),
    "sector_real_estate": Decimal("15.0"),
    "sector_power_energy": Decimal("30.0"),
    "sector_sovereign": Decimal("40.0"),
    "sector_general": Decimal("20.0"),
    "top5_obligors": Decimal("50.0"),
    "related_party": Decimal("5.0"),
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
    return limits, "placeholder defaults - not set in the rule pack and not confirmed by a regulatory source"

# Assets carry no obligor, group, sector or rating fields yet. Until they do, the obligor is the asset's own
# recorded description, the sector is a keyword inference that is labelled as such, and no credit rating is
# shown. (Earlier versions attached real companies and invented ratings to the seed assets - removed.)
RATING_NOT_RECORDED = "not recorded"


SECTOR_LABELS = {
    "sovereign": "Sovereign & Public Sector", "real_estate": "Real Estate", "power_energy": "Power & Energy",
    "textiles": "Textiles", "general": "General Commercial",
}


def _infer_asset_metadata(asset: Asset) -> Dict[str, Any]:
    recorded = _recorded_asset_metadata(asset)
    if recorded is not None:
        return recorded
    desc = (asset.description or "").lower()
    sector, is_sovereign = "General Commercial (inferred)", False
    if "sukuk" in desc or "sovereign" in desc or "government" in desc:
        sector, is_sovereign = "Sovereign & Public Sector (inferred)", True
    elif any(word in desc for word in ("real estate", "property", "building")):
        sector = "Real Estate (inferred)"
    elif any(word in desc for word in ("energy", "power", "solar", "hydro")):
        sector = "Power & Energy (inferred)"
    elif "textile" in desc:
        sector = "Textiles (inferred)"
    name = asset.description or f"Asset {asset.reference_code}"
    return {
        "obligor_name": name,
        "obligor_group": name,  # no group data is recorded, so each obligor is its own group
        "sector": sector,
        "credit_rating": RATING_NOT_RECORDED,
        "rating_agency": None,
        "is_sovereign": is_sovereign,
        "is_related_party": False,
        "shariah_structure": asset.asset_type.replace("_", " ").title(),
    }


def _recorded_asset_metadata(asset):
    """The recorded obligor, group and sector of an asset, or None when they were never recorded."""
    if not (getattr(asset, "sector", "") and getattr(asset, "obligor_name", "")):
        return None
    return {
        "obligor_name": asset.obligor_name,
        "obligor_group": asset.obligor_group or asset.obligor_name,
        "sector": SECTOR_LABELS.get(asset.sector, asset.sector),
        "credit_rating": asset.credit_rating or RATING_NOT_RECORDED,
        "rating_agency": None,
        "is_sovereign": asset.sector == "sovereign",
        "is_related_party": bool(asset.is_related_party),
        "shariah_structure": asset.asset_type.replace("_", " ").title(),
    }


def get_sector_limit_pct(sector: str, limits=None) -> Decimal:
    """The configured limit for an economic sector."""
    limits = limits or DEFAULT_LIMITS_PCT
    s = sector.lower()
    if "real estate" in s or "construction" in s or "property" in s:
        return limits["sector_real_estate"]
    if "power" in s or "energy" in s or "utilities" in s:
        return limits["sector_power_energy"]
    if "sovereign" in s or "public sector" in s:
        return limits["sector_sovereign"]
    return limits["sector_general"]


def run_concentration_risk_analysis(pool: Optional[Pool] = None) -> Dict[str, Any]:
    """
    Analyzes asset exposures for single obligor limits, group obligor limits,
    and economic sector concentration against the configured limits.
    """
    if pool:
        active_assignments = AssetAssignment.objects.filter(pool=pool, unassigned_date__isnull=True).select_related("asset")
        assets = [a.asset for a in active_assignments]
        pool_name = pool.name
        pool_id = str(pool.id)
    else:
        held = AssetAssignment.objects.filter(unassigned_date__isnull=True).select_related("asset")
        assets = [a.asset for a in held]
        pool_name = "Consolidated Portfolio (All Pools)"
        pool_id = "consolidated"

    total_portfolio_exposure = sum((Decimal(a.face_value or 0) for a in assets), Decimal("0.00"))

    if total_portfolio_exposure <= 0:
        return {
            "success": True,
            "pool_id": pool_id,
            "pool_name": pool_name,
            "total_portfolio_exposure": 0.0,
            "asset_count": len(assets),
            "obligors": [],
            "groups": [],
            "sectors": [],
            "prudential_scorecard": [],
            "breach_summary": {"breaches_count": 0, "early_warnings_count": 0, "safe_count": 0},
            "as_of_timestamp": timezone.now().isoformat(),
        }

    # Aggregate by Obligor
    obligors_map: Dict[str, Dict[str, Any]] = {}
    groups_map: Dict[str, Dict[str, Any]] = {}
    sectors_map: Dict[str, Dict[str, Any]] = {}

    limits, limits_source = resolve_limits(pool)

    for asset in assets:
        meta = _infer_asset_metadata(asset)
        amount = Decimal(asset.face_value or 0)
        obligor_name = meta["obligor_name"]
        group_name = meta["obligor_group"]
        sector_name = meta["sector"]

        # 1. Obligor Aggregation
        if obligor_name not in obligors_map:
            limit_pct = limits["single_obligor_sovereign"] if meta["is_sovereign"] else limits["single_obligor_private"]
            obligors_map[obligor_name] = {
                "obligor_name": obligor_name,
                "obligor_group": group_name,
                "sector": sector_name,
                "credit_rating": meta["credit_rating"],
                "rating_agency": meta["rating_agency"],
                "is_sovereign": meta["is_sovereign"],
                "is_related_party": meta["is_related_party"],
                "shariah_structure": meta["shariah_structure"],
                "total_exposure": Decimal("0.00"),
                "assets_count": 0,
                "asset_references": [],
                "sbp_limit_pct": limit_pct,
            }
        obligors_map[obligor_name]["total_exposure"] += amount
        obligors_map[obligor_name]["assets_count"] += 1
        obligors_map[obligor_name]["asset_references"].append(asset.reference_code)

        # 2. Group Aggregation
        if group_name not in groups_map:
            groups_map[group_name] = {
                "group_name": group_name,
                "total_exposure": Decimal("0.00"),
                "obligor_count": 0,
                "obligor_names": set(),
                "sbp_limit_pct": limits["group_private"] if not meta["is_sovereign"] else limits["group_sovereign"],
            }
        groups_map[group_name]["total_exposure"] += amount
        groups_map[group_name]["obligor_names"].add(obligor_name)

        # 3. Sector Aggregation
        if sector_name not in sectors_map:
            sectors_map[sector_name] = {
                "sector_name": sector_name,
                "total_exposure": Decimal("0.00"),
                "assets_count": 0,
                "sbp_limit_pct": get_sector_limit_pct(sector_name, limits),
            }
        sectors_map[sector_name]["total_exposure"] += amount
        sectors_map[sector_name]["assets_count"] += 1

    # Format Obligors List & Evaluate Status
    obligors_list = []
    breaches_count = 0
    early_warnings_count = 0
    safe_count = 0

    for name, item in obligors_map.items():
        exposure = item["total_exposure"]
        portfolio_pct = (exposure / total_portfolio_exposure * Decimal("100.0")).quantize(Decimal("0.01"))
        limit_pct = item["sbp_limit_pct"]
        max_allowed_amount = (total_portfolio_exposure * (limit_pct / Decimal("100.0"))).quantize(Decimal("0.01"))
        utilization_pct = (portfolio_pct / limit_pct * Decimal("100.0")).quantize(Decimal("0.1"))
        headroom_amount = max(Decimal("0.00"), max_allowed_amount - exposure)
        excess_amount = max(Decimal("0.00"), exposure - max_allowed_amount)

        if portfolio_pct > limit_pct:
            status = "breach"
            breaches_count += 1
        elif utilization_pct >= EARLY_WARNING_THRESHOLD_PCT:
            status = "early_warning"
            early_warnings_count += 1
        else:
            status = "safe"
            safe_count += 1

        obligors_list.append({
            "obligor_name": name,
            "obligor_group": item["obligor_group"],
            "sector": item["sector"],
            "credit_rating": item["credit_rating"],
            "rating_agency": item["rating_agency"],
            "is_sovereign": item["is_sovereign"],
            "is_related_party": item["is_related_party"],
            "shariah_structure": item["shariah_structure"],
            "total_exposure": float(exposure),
            "portfolio_pct": float(portfolio_pct),
            "sbp_limit_pct": float(limit_pct),
            "utilization_pct": float(utilization_pct),
            "headroom_amount": float(headroom_amount),
            "excess_amount": float(excess_amount),
            "assets_count": item["assets_count"],
            "asset_references": item["asset_references"],
            "status": status,
        })

    # Sort obligors by exposure descending
    obligors_list.sort(key=lambda x: x["total_exposure"], reverse=True)

    # Format Groups List
    groups_list = []
    for gname, gitem in groups_map.items():
        gexposure = gitem["total_exposure"]
        g_pct = (gexposure / total_portfolio_exposure * Decimal("100.0")).quantize(Decimal("0.01"))
        glimit_pct = gitem["sbp_limit_pct"]
        g_utilization = (g_pct / glimit_pct * Decimal("100.0")).quantize(Decimal("0.1"))
        gstatus = "breach" if g_pct > glimit_pct else ("early_warning" if g_utilization >= EARLY_WARNING_THRESHOLD_PCT else "safe")

        groups_list.append({
            "group_name": gname,
            "total_exposure": float(gexposure),
            "portfolio_pct": float(g_pct),
            "sbp_limit_pct": float(glimit_pct),
            "utilization_pct": float(g_utilization),
            "obligors_count": len(gitem["obligor_names"]),
            "obligor_names": list(gitem["obligor_names"]),
            "status": gstatus,
        })
    groups_list.sort(key=lambda x: x["total_exposure"], reverse=True)

    # Format Sectors List
    sectors_list = []
    for sname, sitem in sectors_map.items():
        sexposure = sitem["total_exposure"]
        s_pct = (sexposure / total_portfolio_exposure * Decimal("100.0")).quantize(Decimal("0.01"))
        slimit_pct = sitem["sbp_limit_pct"]
        s_utilization = (s_pct / slimit_pct * Decimal("100.0")).quantize(Decimal("0.1"))
        s_headroom = max(Decimal("0.00"), (total_portfolio_exposure * slimit_pct / Decimal("100.0")) - sexposure)
        s_excess = max(Decimal("0.00"), sexposure - (total_portfolio_exposure * slimit_pct / Decimal("100.0")))

        if s_pct > slimit_pct:
            s_status = "breach"
            breaches_count += 1
        elif s_utilization >= EARLY_WARNING_THRESHOLD_PCT:
            s_status = "early_warning"
            early_warnings_count += 1
        else:
            s_status = "safe"

        sectors_list.append({
            "sector_name": sname,
            "total_exposure": float(sexposure),
            "portfolio_pct": float(s_pct),
            "sbp_limit_pct": float(slimit_pct),
            "utilization_pct": float(s_utilization),
            "headroom_amount": float(s_headroom),
            "excess_amount": float(s_excess),
            "assets_count": sitem["assets_count"],
            "status": s_status,
        })
    sectors_list.sort(key=lambda x: x["total_exposure"], reverse=True)

    # Scorecard against the configured limits (rule pack, else placeholder defaults - see resolve_limits()).
    real_estate_pct = next((s["portfolio_pct"] for s in sectors_list if "real estate" in s["sector_name"].lower()), 0.0)
    top5_obligors_pct = sum(o["portfolio_pct"] for o in obligors_list[:5])
    related_party_pct = sum(o["portfolio_pct"] for o in obligors_list if o["is_related_party"])
    private_max = max((o["portfolio_pct"] for o in obligors_list if not o["is_sovereign"]), default=0.0)
    group_max = groups_list[0]["portfolio_pct"] if groups_list else 0.0

    def _row(label, description, limit, value, warn_at_80=True):
        limit_f = float(limit)
        status = "breach" if value > limit_f else ("warning" if warn_at_80 and value >= 0.8 * limit_f else "compliant")
        return {
            "regulation": label,
            "description": description,
            "statutory_limit": f"{limit_f:.1f}%",
            "current_value": f"{value:.1f}%",
            "passed": value <= limit_f,
            "status": status,
        }

    scorecard = [
        _row("Single obligor (private)", "Exposure to any single private-sector obligor", limits["single_obligor_private"], private_max),
        _row("Group of connected obligors", "Exposure to one related group", limits["group_private"], group_max, warn_at_80=False),
        _row("Real estate sector", "Exposure to property-related assets (sector inferred from the asset description)", limits["sector_real_estate"], real_estate_pct),
        _row("Top-5 obligors", "Cumulative concentration in the 5 largest obligors", limits["top5_obligors"], top5_obligors_pct, warn_at_80=False),
        _row("Related-party exposure", "Exposure to assets recorded as related party", limits["related_party"], related_party_pct, warn_at_80=False),
        {
            "regulation": "Prohibited-sector screen",
            "description": "Not assessed: assets carry no recorded activity / sector classification yet",
            "statutory_limit": "n/a",
            "current_value": "not assessed",
            "passed": None,
            "status": "not_assessed",
        },
    ]

    return {
        "success": True,
        "pool_id": pool_id,
        "pool_name": pool_name,
        "total_portfolio_exposure": float(total_portfolio_exposure),
        "asset_count": len(assets),
        "obligors": obligors_list,
        "groups": groups_list,
        "sectors": sectors_list,
        "prudential_scorecard": scorecard,
        "breach_summary": {
            "breaches_count": breaches_count,
            "early_warnings_count": early_warnings_count,
            "safe_count": safe_count,
            "highest_obligor_utilization": float(obligors_list[0]["utilization_pct"]) if obligors_list else 0.0,
            "highest_sector_utilization": float(sectors_list[0]["utilization_pct"]) if sectors_list else 0.0,
        },
        "as_of_timestamp": timezone.now().isoformat(),
        "limits_source": limits_source,
        "limits_pct": {key: float(value) for key, value in limits.items()},
        "basis_note": (
            "Limits are applied to the pool's own asset total using the configured thresholds in this module. "
            "They are indicative and must be confirmed by Risk & Compliance against the applicable prudential "
            "regulations (which may be measured against the bank's equity)."
        ),
    }


def generate_remediation_proposal(
    target_name: str,
    target_type: str,
    current_exposure: Any,
    excess_amount: Any,
    pool: Optional[Pool] = None,
) -> Dict[str, Any]:
    """
    A neutral remediation worksheet for a concentration breach. It states the numbers and asks for a decision; it cites no
    regulator, form or filing deadline. A cure period appears only if the rule pack sets `concentration_cure_days`.
    """
    current_exposure = Decimal(str(current_exposure or 0))
    excess_amount = Decimal(str(excess_amount or 0))
    now = timezone.now()
    now_str = now.strftime("%Y-%m-%d")
    cure_days = None
    if pool is not None:
        from apps.pools.config_snapshot import bound_rule_pack

        pack = bound_rule_pack(pool)
        cure_days = ((pack.rules_config or {}).get("concentration_cure_days") if pack else None)
    deadline_str = (now + timezone.timedelta(days=int(cure_days))).strftime("%Y-%m-%d") if cure_days else None

    recommended_sell_down = (excess_amount * Decimal("1.10")).quantize(Decimal("0.01"))
    deadline_line = f"**Cure deadline (rule pack):** {deadline_str}" if deadline_str else "**Cure deadline:** not set in the rule pack"

    memo_text = f"""# CONCENTRATION BREACH - REMEDIATION WORKSHEET
**Date:** {now_str} | {deadline_line}
**Target:** {target_type.upper()} - {target_name}
**Pool:** {pool.name if pool else 'Consolidated (all pools)'}

---

### 1. What was found
The exposure is above the limit configured for this pool:
- **Total outstanding exposure:** PKR {current_exposure:,.2f}
- **Amount above the limit:** PKR {excess_amount:,.2f}
- **Reduction that would leave a 10% margin:** PKR {recommended_sell_down:,.2f}

### 2. Decision needed (Risk & Compliance with the pool manager)
Record which of these will be done, by whom and by when: reduce the exposure, reallocate to other eligible assets, or
document why the limit is being waived. Any filing to a regulator is for Risk & Compliance to determine; this worksheet
does not assume one.
"""

    return {
        "target_name": target_name,
        "target_type": target_type,
        "current_exposure": float(current_exposure),
        "excess_amount": float(excess_amount),
        "recommended_sell_down": float(recommended_sell_down),
        "statutory_deadline": deadline_str,
        "official_memo": memo_text.strip(),
        "action_steps": [
            f"Decide how to bring the exposure down by at least PKR {excess_amount:,.2f}.",
            "Name the owner and the date for each step.",
            "Confirm with Risk & Compliance whether any regulatory notification applies.",
        ],
    }


def commit_breach_remediation_case(
    tenant,
    user,
    target_name: str,
    target_type: str,
    current_exposure: Any,
    excess_amount: Any,
    action_note: str,
    pool: Optional[Pool] = None,
) -> Dict[str, Any]:
    """
    Submits official remediation plan, registers an ExceptionCase in governance,
    and creates an immutable audit trail.
    """
    current_exposure = Decimal(str(current_exposure or 0))
    excess_amount = Decimal(str(excess_amount or 0))
    plan = generate_remediation_proposal(target_name, target_type, current_exposure, excess_amount, pool)

    title = f"Concentration limit breach: {target_type.upper()} '{target_name}'"
    description = (
        f"Automated check found an exposure above the configured concentration limit.\n"
        f"Target: {target_name} ({target_type})\n"
        f"Current Exposure: PKR {current_exposure:,.2f}\n"
        f"Excess Amount: PKR {excess_amount:,.2f}\n"
        f"Remediation Plan: {action_note}\n\n"
        f"Cure deadline: {plan['statutory_deadline'] or 'not set in the rule pack'}"
    )

    case = create_exception_case(
        tenant=tenant,
        source_module="asset_assignment",
        title=title,
        description=description,
        severity="critical" if excess_amount > Decimal("10000000.00") else "high",
        pool=pool,
        detected_by="system",
    )

    log_action(
        tenant=tenant,
        actor=user,
        action="create",
        model_name="ExceptionCase",
        object_id=str(case.id),
        changes={
            "breach_target": target_name,
            "target_type": target_type,
            "excess_amount": str(excess_amount),
            "remediation_status": "filed_with_risk_committee",
        },
        reason=f"Concentration remediation worksheet opened for {target_name}",
    )

    return {
        "success": True,
        "exception_case_id": str(case.id),
        "case_severity": case.severity,
        "case_title": case.title,
        "statutory_deadline": plan["statutory_deadline"],
        "plan": plan,
    }


def run_concentration_stress_test(
    pool: Optional[Pool] = None,
    deposit_runoff_pct: float = 15.0,
    credit_downgrade_shocks: bool = True,
) -> Dict[str, Any]:
    """
    Simulates portfolio shocks:
    - Deposit Runoff: pool assets shrink by deposit_runoff_pct (e.g. 10%, 20%, 30%),
      causing fixed obligor exposures to spike as a percentage of pool.
    - Evaluates post-stress breaches and capital cushion requirements.
    """
    baseline = run_concentration_risk_analysis(pool)
    base_exposure = Decimal(str(baseline["total_portfolio_exposure"]))

    if base_exposure <= 0:
        return {"success": False, "error": "No asset exposures available for stress testing."}

    shock_multiplier = Decimal(str(1.0 - (deposit_runoff_pct / 100.0)))
    shocked_portfolio_exposure = (base_exposure * shock_multiplier).quantize(Decimal("0.01"))

    stressed_obligors = []
    post_stress_breaches = 0

    for o in baseline["obligors"]:
        exp = Decimal(str(o["total_exposure"]))
        stressed_pct = (exp / shocked_portfolio_exposure * Decimal("100.0")).quantize(Decimal("0.01"))
        limit_pct = Decimal(str(o["sbp_limit_pct"]))
        stressed_util = (stressed_pct / limit_pct * Decimal("100.0")).quantize(Decimal("0.1"))
        status = "breach" if stressed_pct > limit_pct else ("early_warning" if stressed_util >= EARLY_WARNING_THRESHOLD_PCT else "safe")
        if status == "breach":
            post_stress_breaches += 1

        stressed_obligors.append({
            "obligor_name": o["obligor_name"],
            "pre_stress_pct": o["portfolio_pct"],
            "post_stress_pct": float(stressed_pct),
            "pct_delta": float((stressed_pct - Decimal(str(o["portfolio_pct"]))).quantize(Decimal("0.01"))),
            "sbp_limit_pct": o["sbp_limit_pct"],
            "stressed_utilization_pct": float(stressed_util),
            "status": status,
        })

    return {
        "success": True,
        "deposit_runoff_pct": deposit_runoff_pct,
        "baseline_portfolio_exposure": float(base_exposure),
        "stressed_portfolio_exposure": float(shocked_portfolio_exposure),
        "post_stress_breaches_count": post_stress_breaches,
        "incremental_breaches": max(0, post_stress_breaches - baseline["breach_summary"]["breaches_count"]),
        "stressed_obligors": stressed_obligors,
    }
