ROOT = "backend/apps/"
p = ROOT + "pools/concentration_engine.py"
s = open(p, encoding="utf-8").read()

# ---- defaults: two more configurable limits ----------------------------------------------------
old = '''    "sector_general": Decimal("20.0"),
}'''
new = '''    "sector_general": Decimal("20.0"),
    "top5_obligors": Decimal("50.0"),
    "related_party": Decimal("5.0"),
}'''
assert old in s
s = s.replace(old, new, 1)

# ---- scorecard: configured limits, neutral labels ----------------------------------------------
a = s.index("    # SBP Prudential Regulations Scorecard Matrix")
b = s.index("    return {", a)
score = '''    # Scorecard against the configured limits (rule pack, else placeholder defaults - see resolve_limits()).
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
        _row("Related-party exposure", "Exposure flagged as related party (no asset is flagged yet: the field is not recorded)", limits["related_party"], related_party_pct, warn_at_80=False),
        {
            "regulation": "Prohibited-sector screen",
            "description": "Not assessed: assets carry no recorded activity / sector classification yet",
            "statutory_limit": "n/a",
            "current_value": "not assessed",
            "passed": None,
            "status": "not_assessed",
        },
    ]

'''
s = s[:a] + score + s[b:]

# ---- return: say where the limits came from ----------------------------------------------------
old = '''        "as_of_timestamp": timezone.now().isoformat(),
        "basis_note": ('''
new = '''        "as_of_timestamp": timezone.now().isoformat(),
        "limits_source": limits_source,
        "basis_note": ('''
assert old in s
s = s.replace(old, new, 1)

# ---- remediation memo: no invented regulator citations, deadlines or filings --------------------
a = s.index("def generate_remediation_proposal(")
b = s.index("def commit_breach_remediation_case(")
memo = '''def generate_remediation_proposal(
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


'''
s = s[:a] + memo + s[b:]

old = '''    title = f"SBP Concentration Breach: {target_type.upper()} '{target_name}' Exceeds Statutory Cap"
    description = (
        f"Automated risk detection identified statutory limit breach under SBP PR R-1/R-6.\\n"'''
new = '''    title = f"Concentration limit breach: {target_type.upper()} '{target_name}'"
    description = (
        f"Automated check found an exposure above the configured concentration limit.\\n"'''
assert old in s, "title"
s = s.replace(old, new, 1)
old = '''        f"Statutory Cure Deadline: {plan['statutory_deadline']}"'''
new = '''        f"Cure deadline: {plan['statutory_deadline'] or 'not set in the rule pack'}"'''
assert old in s
s = s.replace(old, new, 1)
s = s.replace('reason=f"SBP Statutory Concentration Remediation Plan initiated for {target_name}"',
              'reason=f"Concentration remediation worksheet opened for {target_name}"')
s = s.replace("and economic sector concentration under SBP PR R-1 & R-6.", "and economic sector concentration against the configured limits.")
open(p, "w", encoding="utf-8").write(s)
print("ok")
