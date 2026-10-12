import hashlib
import json


def compute_snapshot_hash(snapshot_dict):
    """Computes deterministic SHA-256 hash for a pool version snapshot."""
    raw = json.dumps(snapshot_dict, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _pack_label(pack):
    return f"{pack.get('code')} v{pack.get('version')}" if pack else None


def _matrix_label(rules):
    if not rules:
        return None
    return "; ".join(
        f"{rule['role']} <= {rule['max_amount'] or 'unlimited'}" for rule in sorted(rules, key=lambda r: r["role"])
    )


def _mapping_label(mapping):
    if not mapping:
        return None
    return "; ".join(f"{key}={value['code'] or value['name']}" for key, value in sorted(mapping.items()))


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

    # 2. Profit sharing (PSR) - from the approved ProfitSharingRatio that was in force
    psr1 = snap1.get("psr") or {}
    psr2 = snap2.get("psr") or {}
    add_diff_item("PSR & Economics", "investor_share_pct", "Investor / Depositor Share", psr1.get("investor_share_pct"), psr2.get("investor_share_pct"), "%", "percentage")
    add_diff_item("PSR & Economics", "manager_share_pct", "Manager (Mudarib) Share", psr1.get("manager_share_pct"), psr2.get("manager_share_pct"), "%", "percentage")
    add_diff_item("PSR & Economics", "wakalah_fee_pct", "Wakalah Agency Fee (p.a.)", psr1.get("wakalah_fee_pct"), psr2.get("wakalah_fee_pct"), "%", "percentage")

    # 3. Reserve policies
    res1 = snap1.get("reserve_policy") or {}
    res2 = snap2.get("reserve_policy") or {}
    for kind, label in (("per", "PER"), ("irr", "IRR")):
        r1 = res1.get(kind) or {}
        r2 = res2.get(kind) or {}
        add_diff_item("Prudential Reserves", f"{kind}_rate_pct", f"{label} Appropriation Rate", r1.get("rate_pct"), r2.get("rate_pct"), "%", "percentage")
        add_diff_item("Prudential Reserves", f"{kind}_cap_pct", f"{label} Cap (% of funds)", r1.get("cap_pct"), r2.get("cap_pct"), "%", "percentage")

    # 4. Rule pack and Shariah decision
    pack1 = snap1.get("rule_pack") or {}
    pack2 = snap2.get("rule_pack") or {}
    add_diff_item("Governance & Compliance", "rule_pack", "Jurisdiction Rule Pack", _pack_label(pack1), _pack_label(pack2))
    dec1 = snap1.get("shariah_decision") or {}
    dec2 = snap2.get("shariah_decision") or {}
    add_diff_item("Governance & Compliance", "shariah_decision", "Shariah Decision", dec1.get("decision_code"), dec2.get("decision_code"))
    add_diff_item("Governance & Compliance", "shariah_status", "Shariah Decision Status", dec1.get("status"), dec2.get("status"))

    # 5. Controls: approval matrix and accounting mapping
    add_diff_item("Controls", "approval_matrix", "Approval Matrix", _matrix_label(snap1.get("approval_matrix")), _matrix_label(snap2.get("approval_matrix")))
    add_diff_item("Controls", "account_mapping", "Accounting Mapping", _mapping_label(snap1.get("account_mapping")), _mapping_label(snap2.get("account_mapping")))

    # 6. Version metadata
    gov1 = snap1.get("governance") or {}
    gov2 = snap2.get("governance") or {}
    add_diff_item("Governance & Compliance", "approving_scholar", "Decision Approved By", gov1.get("approving_scholar"), gov2.get("approving_scholar"))
    add_diff_item("Governance & Compliance", "effective_value_date", "Effective Value Date", gov1.get("effective_value_date"), gov2.get("effective_value_date"))
    add_diff_item("Governance & Compliance", "change_rationale", "Change Rationale", gov1.get("change_rationale"), gov2.get("change_rationale"))

    # 7. Weightage tiers diff
    tiers1 = snap1.get("weightage_bands") or []
    tiers2 = snap2.get("weightage_bands") or []

    tiers_diff = []
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
            "v1_tenor_days": None,
            "v2_tenor_days": None,
            "is_changed": changed,
            "delta": delta,
            "change_type": "modified" if changed and t1 and t2 else "unchanged" if (t1 and t2) else ("added" if t2 else "removed"),
        })

    # Summary analysis
    total_field_changes = sum(1 for item in diff_matrix if item["is_changed"])
    total_tier_changes = sum(1 for item in tiers_diff if item["is_changed"])
    total_changes = total_field_changes + total_tier_changes

    risk_level = "LOW"
    if total_changes > 4 or any(item["key"] in ("manager_share_pct", "investor_share_pct", "wakalah_fee_pct", "per_rate_pct", "irr_rate_pct", "per_cap_pct", "irr_cap_pct") and item["is_changed"] for item in diff_matrix):
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
            "created_by": v1.created_by.full_name if v1.created_by else None,
            "snapshot_hash": hash1,
            "shariah_resolution": gov1.get("shariah_resolution_code"),
        },
        "v2": {
            "id": str(v2.id),
            "version_number": v2.version_number,
            "is_current": v2.is_current,
            "created_at": v2.created_at.isoformat() if v2.created_at else None,
            "created_by": v2.created_by.full_name if v2.created_by else None,
            "snapshot_hash": hash2,
            "shariah_resolution": gov2.get("shariah_resolution_code"),
        },
        "summary": {
            "total_changes": total_changes,
            "field_changes_count": total_field_changes,
            "tier_changes_count": total_tier_changes,
            "risk_impact": risk_level,
            "shariah_quorum_attested": bool(dec2.get("in_force")),
            "requires_regulatory_filing": risk_level in ("HIGH", "CRITICAL"),
        },
        "diff_matrix": diff_matrix,
        "tiers_diff": tiers_diff,
    }
