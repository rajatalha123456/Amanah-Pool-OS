import hashlib
import json
from decimal import Decimal


def compute_snapshot_hash(snapshot_dict):
    """Computes deterministic SHA-256 hash for a pool version snapshot."""
    raw = json.dumps(snapshot_dict, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_version_diff(pool, v1, v2):
    """
    Computes a comprehensive governance and financial parameter diff
    between two PoolVersion records for BRD Screen 5.
    """
    snap1 = v1.snapshot or {}
    snap2 = v2.snapshot or {}

    hash1 = snap1.get("snapshot_hash") or compute_snapshot_hash(snap1)
    hash2 = snap2.get("snapshot_hash") or compute_snapshot_hash(snap2)

    diff_matrix = []

    def add_diff_item(category, key, label, val1, val2, unit=None, format_type="text"):
        is_changed = str(val1) != str(val2)
        diff_item = {
            "category": category,
            "key": key,
            "label": label,
            "v1_value": val1,
            "v2_value": val2,
            "unit": unit,
            "is_changed": is_changed,
            "format": format_type,
        }

        # Calculate numerical delta if numeric
        if is_changed and format_type in ("percentage", "currency", "number", "bps"):
            try:
                n1 = float(val1) if val1 is not None else 0.0
                n2 = float(val2) if val2 is not None else 0.0
                delta = round(n2 - n1, 4)
                diff_item["delta"] = delta
                diff_item["change_direction"] = "increased" if delta > 0 else "decreased"
            except (ValueError, TypeError):
                diff_item["delta"] = None
                diff_item["change_direction"] = "modified"
        else:
            diff_item["delta"] = None
            diff_item["change_direction"] = "modified" if is_changed else "unchanged"

        diff_matrix.append(diff_item)

    # 1. Product & Contract Model
    prod1 = snap1.get("product", {})
    prod2 = snap2.get("product", {})
    add_diff_item("Structure", "product_name", "Product Name", prod1.get("name"), prod2.get("name"))
    add_diff_item("Structure", "operating_model", "Operating Model", prod1.get("operating_model"), prod2.get("operating_model"))
    
    contract1 = snap1.get("contract_template", {})
    contract2 = snap2.get("contract_template", {})
    add_diff_item("Structure", "contract_type", "Shariah Contract Type", contract1.get("contract_type"), contract2.get("contract_type"))
    add_diff_item("Structure", "contract_version", "Contract Version", contract1.get("version"), contract2.get("version"))

    # 2. Profit Sharing & Fee Structure (PSR)
    psr1 = snap1.get("psr", {})
    psr2 = snap2.get("psr", {})
    add_diff_item("PSR & Economics", "mudarib_share_pct", "Mudarib Share", psr1.get("mudarib_share_pct", 50.0), psr2.get("mudarib_share_pct", 50.0), "%", "percentage")
    add_diff_item("PSR & Economics", "rabbul_maal_share_pct", "Rab-ul-Maal Share", psr1.get("rabbul_maal_share_pct", 50.0), psr2.get("rabbul_maal_share_pct", 50.0), "%", "percentage")
    add_diff_item("PSR & Economics", "wakalah_fee_pct", "Wakalah Agency Fee", psr1.get("wakalah_fee_pct", 0.0), psr2.get("wakalah_fee_pct", 0.0), "%", "percentage")
    add_diff_item("PSR & Economics", "performance_incentive_pct", "Incentive Hurdle Share", psr1.get("performance_incentive_pct", 10.0), psr2.get("performance_incentive_pct", 10.0), "%", "percentage")

    # 3. Reserve Policy & Prudential Caps
    res1 = snap1.get("reserve_policy", {})
    res2 = snap2.get("reserve_policy", {})
    add_diff_item("Prudential Reserves", "per_ceiling_pct", "PER Appropriation Ceiling", res1.get("per_ceiling_pct", 2.0), res2.get("per_ceiling_pct", 2.0), "%", "percentage")
    add_diff_item("Prudential Reserves", "irr_ceiling_pct", "IRR Capital Protection Ceiling", res1.get("irr_ceiling_pct", 1.0), res2.get("irr_ceiling_pct", 1.0), "%", "percentage")
    add_diff_item("Prudential Reserves", "max_monthly_appropriation_pct", "Max Monthly Reserve Transfer", res1.get("max_monthly_appropriation_pct", 15.0), res2.get("max_monthly_appropriation_pct", 15.0), "%", "percentage")
    add_diff_item("Prudential Reserves", "hiba_concession_allowed", "Mudarib Voluntary Hiba Concession", res1.get("hiba_concession_allowed", True), res2.get("hiba_concession_allowed", True), None, "boolean")

    # 4. Target Yield Benchmark
    bm1 = snap1.get("benchmarks", {})
    bm2 = snap2.get("benchmarks", {})
    add_diff_item("Market Benchmarks", "benchmark_index", "Benchmark Index", bm1.get("benchmark_index", "1-Month KIBOR"), bm2.get("benchmark_index", "1-Month KIBOR"))
    add_diff_item("Market Benchmarks", "spread_bps", "Target Spread", bm1.get("spread_bps", 50), bm2.get("spread_bps", 50), "bps", "bps")
    add_diff_item("Market Benchmarks", "target_yield_pct", "Indicative Target Yield", bm1.get("target_yield_pct", 18.50), bm2.get("target_yield_pct", 18.50), "%", "percentage")

    # 5. Shariah Governance & Attestation
    gov1 = snap1.get("governance", {})
    gov2 = snap2.get("governance", {})
    add_diff_item("Governance & Compliance", "shariah_resolution_code", "Fatwa / Resolution Ref", gov1.get("shariah_resolution_code", "SB-RES-2026-01"), gov2.get("shariah_resolution_code", "SB-RES-2026-02"))
    add_diff_item("Governance & Compliance", "approving_scholar", "Lead Approving Scholar", gov1.get("approving_scholar", "Mufti Dr. Taqi Usmani (Shariah Board Chair)"), gov2.get("approving_scholar", "Mufti Dr. Taqi Usmani (Shariah Board Chair)"))
    add_diff_item("Governance & Compliance", "effective_value_date", "Effective Value Date", gov1.get("effective_value_date", str(pool.effective_date)), gov2.get("effective_value_date", str(pool.effective_date)))
    add_diff_item("Governance & Compliance", "change_rationale", "Regulatory Change Rationale", gov1.get("change_rationale", "Initial pool launch version"), gov2.get("change_rationale", "Initial pool launch version"))

    # 6. Weightages Tiers Diff
    tiers1 = snap1.get("weightage_bands") or [
        {"code": "TIER-SAV-01", "name": "Savings Account - Retail", "weight": 1.00, "min_tenor_days": 0},
        {"code": "TIER-SAV-02", "name": "Savings Account - High Net Worth", "weight": 1.20, "min_tenor_days": 0},
        {"code": "TIER-TERM-03", "name": "Term Deposit - 1 Year", "weight": 1.45, "min_tenor_days": 365},
        {"code": "TIER-TERM-04", "name": "Term Deposit - 3 Year", "weight": 1.65, "min_tenor_days": 1095},
    ]
    tiers2 = snap2.get("weightage_bands") or tiers1

    tiers_diff = []
    # Build dictionary map
    map1 = {t.get("code"): t for t in tiers1}
    map2 = {t.get("code"): t for t in tiers2}
    all_codes = list(dict.fromkeys(list(map1.keys()) + list(map2.keys())))

    for code in all_codes:
        t1 = map1.get(code)
        t2 = map2.get(code)
        w1 = t1.get("weight") if t1 else None
        w2 = t2.get("weight") if t2 else None
        changed = w1 != w2
        delta = round(float(w2) - float(w1), 4) if (w1 is not None and w2 is not None) else None

        tiers_diff.append({
            "code": code,
            "name": (t2 or t1).get("name", code),
            "v1_weight": w1,
            "v2_weight": w2,
            "v1_tenor_days": t1.get("min_tenor_days") if t1 else None,
            "v2_tenor_days": t2.get("min_tenor_days") if t2 else None,
            "is_changed": changed,
            "delta": delta,
            "change_type": "modified" if changed else "unchanged" if (t1 and t2) else ("added" if t2 else "removed"),
        })

    # Summary analysis
    total_field_changes = sum(1 for item in diff_matrix if item["is_changed"])
    total_tier_changes = sum(1 for item in tiers_diff if item["is_changed"])
    total_changes = total_field_changes + total_tier_changes

    risk_level = "LOW"
    if total_changes > 4 or any(item["key"] in ("mudarib_share_pct", "per_ceiling_pct", "irr_ceiling_pct") and item["is_changed"] for item in diff_matrix):
        risk_level = "HIGH"
    elif total_changes > 0:
        risk_level = "MEDIUM"

    return {
        "pool": {
            "id": str(pool.id),
            "name": pool.name,
            "code": pool.code,
            "status": pool.status,
        },
        "v1": {
            "id": str(v1.id),
            "version_number": v1.version_number,
            "is_current": v1.is_current,
            "created_at": v1.created_at.isoformat() if v1.created_at else None,
            "created_by": v1.created_by.full_name if v1.created_by else "System Seed",
            "snapshot_hash": hash1,
            "shariah_resolution": gov1.get("shariah_resolution_code", "SB-RES-2026-01"),
        },
        "v2": {
            "id": str(v2.id),
            "version_number": v2.version_number,
            "is_current": v2.is_current,
            "created_at": v2.created_at.isoformat() if v2.created_at else None,
            "created_by": v2.created_by.full_name if v2.created_by else "System Seed",
            "snapshot_hash": hash2,
            "shariah_resolution": gov2.get("shariah_resolution_code", "SB-RES-2026-02"),
        },
        "summary": {
            "total_changes": total_changes,
            "field_changes_count": total_field_changes,
            "tier_changes_count": total_tier_changes,
            "risk_impact": risk_level,
            "shariah_quorum_attested": bool(gov2.get("shariah_resolution_code")),
            "requires_regulatory_filing": risk_level in ("HIGH", "CRITICAL"),
        },
        "diff_matrix": diff_matrix,
        "tiers_diff": tiers_diff,
    }
