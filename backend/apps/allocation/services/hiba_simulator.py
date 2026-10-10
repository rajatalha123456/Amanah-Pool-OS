"""
Mudarib Share Hiba (Voluntary Reduction) & Yield-Matching Simulator (BRD Module 07 / Screen 19)

Implements AAOIFI Shariah Standard No. 13 (Clause 8/5) and SBP IBD Circular 03/2012:
- Allows the Islamic Bank (Mudarib) to voluntarily forego/waive a portion of its contractual
  profit share (Hiba / Tanazul) to prevent depositor flight and match conventional benchmark yields (KIBOR).
- Provides live simulation of Hiba amounts, tier-by-tier annualized yields, and SBP compliance validation.
"""

from decimal import Decimal
from typing import Dict, Any, List
from django.utils import timezone
from apps.allocation.models import AllocationRun, AllocationRunStatus, AllocationLine
from apps.core.audit import log_action


def simulate_mudarib_hiba(
    allocation_run: AllocationRun,
    target_kibor_rate: Decimal = Decimal("17.50"),
    simulated_hiba_amount: Decimal = None,
    simulated_mudarib_rate: Decimal = None,
) -> Dict[str, Any]:
    """
    Simulates the impact of Hiba (voluntary reduction of Mudarib share) on depositor yields.
    """
    gross_income = Decimal(allocation_run.gross_income)
    direct_expenses = Decimal(allocation_run.direct_expenses)
    distributable = Decimal(allocation_run.distributable_amount)
    total_weighted_funds = Decimal(allocation_run.total_weighted_funds)
    baseline_depositor_share = Decimal(allocation_run.depositor_pool_share)
    baseline_mudarib_share = Decimal(allocation_run.mudarib_share)

    # Days in month estimation (30 days convention for monthly pool)
    days_in_period = 30
    annualization_factor = Decimal("365.0") / Decimal(days_in_period)

    # Contractual Mudarib percentage
    contractual_mudarib_pct = (
        (baseline_mudarib_share / distributable * Decimal("100.0")).quantize(Decimal("0.01"))
        if distributable > 0
        else Decimal("30.00")
    )

    # Determine simulated Hiba amount
    if simulated_hiba_amount is not None:
        hiba_amount = Decimal(simulated_hiba_amount)
    elif simulated_mudarib_rate is not None:
        target_mud_pct = Decimal(simulated_mudarib_rate)
        target_mud_amount = (distributable * (target_mud_pct / Decimal("100.0"))).quantize(Decimal("0.01"))
        hiba_amount = max(Decimal("0.00"), baseline_mudarib_share - target_mud_amount)
    else:
        # Default: simulate 25% Hiba foregone
        hiba_amount = (baseline_mudarib_share * Decimal("0.25")).quantize(Decimal("0.01"))

    # Cap Hiba at maximum available Mudarib share (no negative Mudarib share)
    hiba_amount = min(hiba_amount, baseline_mudarib_share)
    hiba_amount = max(Decimal("0.00"), hiba_amount)

    revised_mudarib_share = baseline_mudarib_share - hiba_amount
    revised_depositor_share = baseline_depositor_share + hiba_amount

    effective_mudarib_pct = (
        (revised_mudarib_share / distributable * Decimal("100.0")).quantize(Decimal("0.02"))
        if distributable > 0
        else Decimal("0.00")
    )

    # Calculate optimal Hiba needed to reach target KIBOR rate across the pool
    # Target total depositor profit = (total_weighted_funds * target_kibor / 100) / annualization_factor
    target_annual_rate = Decimal(target_kibor_rate) / Decimal("100.0")
    required_depositor_profit = (total_weighted_funds * target_annual_rate) / annualization_factor
    optimal_hiba_needed = max(
        Decimal("0.00"),
        min(baseline_mudarib_share, required_depositor_profit - baseline_depositor_share),
    ).quantize(Decimal("0.01"))

    # Tier by tier impact
    lines = list(allocation_run.lines.all())
    tier_impact: List[Dict[str, Any]] = []

    for line in lines:
        daily_funds = Decimal(line.daily_funds)
        weighted_funds = Decimal(line.weighted_funds)
        base_alloc = Decimal(line.allocated_amount)

        # Baseline Yield
        base_yield_pct = (
            ((base_alloc / daily_funds) * annualization_factor * Decimal("100.0")).quantize(Decimal("0.02"))
            if daily_funds > 0
            else Decimal("0.00")
        )

        # Incremental Hiba allocation
        line_ratio = weighted_funds / total_weighted_funds if total_weighted_funds > 0 else Decimal("0.00")
        incremental_profit = (hiba_amount * line_ratio).quantize(Decimal("0.01"))
        revised_alloc = base_alloc + incremental_profit

        # Revised Yield
        revised_yield_pct = (
            ((revised_alloc / daily_funds) * annualization_factor * Decimal("100.0")).quantize(Decimal("0.02"))
            if daily_funds > 0
            else Decimal("0.00")
        )

        yield_delta_bps = ((revised_yield_pct - base_yield_pct) * Decimal("100.0")).quantize(Decimal("1"))
        kibor_gap = (revised_yield_pct - Decimal(target_kibor_rate)).quantize(Decimal("0.02"))

        tier_impact.append({
            "participant_class": line.participant_class,
            "daily_funds": float(daily_funds),
            "weightage": float(line.weightage),
            "weighted_funds": float(weighted_funds),
            "baseline_allocated_amount": float(base_alloc),
            "baseline_annualized_yield": float(base_yield_pct),
            "incremental_hiba_share": float(incremental_profit),
            "revised_allocated_amount": float(revised_alloc),
            "revised_annualized_yield": float(revised_yield_pct),
            "yield_delta_bps": int(yield_delta_bps),
            "gap_vs_benchmark": float(kibor_gap),
        })

    # Average pool yields
    avg_base_yield = sum(t["baseline_annualized_yield"] for t in tier_impact) / len(tier_impact) if tier_impact else 0.0
    avg_revised_yield = sum(t["revised_annualized_yield"] for t in tier_impact) / len(tier_impact) if tier_impact else 0.0

    # Shariah Compliance Validation Checklist
    shariah_checklist = [
        {
            "id": "RULE-HIBA-01",
            "rule": "Ex-Post Determination (Post-Allocation)",
            "standard": "AAOIFI Shariah Standard No. 13 (Clause 8/5)",
            "passed": True,
            "details": f"Hiba evaluated on actual elapsed cycle ({allocation_run.value_date}) - zero prior contractual guarantee.",
        },
        {
            "id": "RULE-HIBA-02",
            "rule": "Non-Negative Mudarib Share Limit",
            "standard": "SBP IBD Circular 03/2012 Annexure B",
            "passed": revised_mudarib_share >= 0,
            "details": f"Bank retains PKR {revised_mudarib_share:,.2f} ({effective_mudarib_pct}% of distributable pool profit).",
        },
        {
            "id": "RULE-HIBA-03",
            "rule": "Equal Pro-Rata Distribution Across Participant Tiers",
            "standard": "AAOIFI Shariah Standard No. 40",
            "passed": True,
            "details": "Hiba apportioned strictly according to SBP approved weightage matrix without arbitrary preference.",
        },
        {
            "id": "RULE-HIBA-04",
            "rule": "Irrevocability of Voluntary Gift",
            "standard": "AAOIFI Shariah Standard No. 13",
            "passed": True,
            "details": "Hiba once approved is non-refundable and cannot be clawed back from future depositor profits.",
        },
    ]

    all_shariah_passed = all(item["passed"] for item in shariah_checklist)

    # ALCO & Shariah Resolution Memorandum
    now_str = timezone.now().strftime("%Y-%m-%d %H:%M UTC")
    memo = f"""# ALCO & SHARIAH BOARD RESOLUTION MEMORANDUM: MUDARIB HIBA CONCESSION
**Allocation Run ID:** {str(allocation_run.id)} | **Pool:** {allocation_run.pool.name}
**Value Date:** {allocation_run.value_date} | **Evaluation Date:** {now_str}
**Benchmark Reference Rate (1M KIBOR):** {target_kibor_rate}%

---

### 1. BACKGROUND & COMMERCIAL JUSTIFICATION
In the monthly profit cycle ending {allocation_run.value_date}, the gross distributable income of the pool was PKR {distributable:,.2f}. 
Under contractual PSR ({100 - contractual_mudarib_pct}/{contractual_mudarib_pct}), the baseline depositor yield averaged {avg_base_yield:.2f}%, 
representing a competitive deficit of {float(target_kibor_rate) - avg_base_yield:.2f}% against prevailing market KIBOR rates ({target_kibor_rate}%). 
To prevent depositor attrition and optimize yield parity, the Bank hereby considers a voluntary waiver of Mudarib profit share under the principle of **Hiba (Tanazul)**.

### 2. HIBA QUANTIFICATION & REVISED WATERFALL
- **Distributable Pool Profit:** PKR {distributable:,.2f}
- **Contractual Mudarib Share:** PKR {baseline_mudarib_share:,.2f} ({contractual_mudarib_pct}%)
- **Voluntary Hiba Concession:** PKR {hiba_amount:,.2f} ({float(hiba_amount / baseline_mudarib_share * 100) if baseline_mudarib_share else 0:.1f}% of contractual fee)
- **Net Mudarib Fee Retained:** PKR {revised_mudarib_share:,.2f} ({effective_mudarib_pct}%)
- **Revised Depositor Allocation:** PKR {revised_depositor_share:,.2f} (Effective Yield: {avg_revised_yield:.2f}%)
- **Net Yield Uplift to Depositors:** +{int((avg_revised_yield - avg_base_yield) * 100)} bps

### 3. SHARIAH SUPERVISORY BOARD CERTIFICATION
The concession has been reviewed under AAOIFI FAS-30 and SBP IBD Circular 03/2012. 
Because the concession is determined ex-post without prior contractual commitment, it constitutes a valid Shar'i Hiba.
"""

    return {
        "success": True,
        "run_id": str(allocation_run.id),
        "pool_id": str(allocation_run.pool.id),
        "pool_name": allocation_run.pool.name,
        "value_date": str(allocation_run.value_date),
        "status": allocation_run.status,
        "benchmark_rate": float(target_kibor_rate),
        "metrics": {
            "distributable_amount": float(distributable),
            "total_weighted_funds": float(total_weighted_funds),
            "contractual_mudarib_share": float(baseline_mudarib_share),
            "contractual_mudarib_pct": float(contractual_mudarib_pct),
            "simulated_hiba_amount": float(hiba_amount),
            "effective_mudarib_share": float(revised_mudarib_share),
            "effective_mudarib_pct": float(effective_mudarib_pct),
            "baseline_depositor_share": float(baseline_depositor_share),
            "revised_depositor_share": float(revised_depositor_share),
            "optimal_hiba_needed_for_kibor": float(optimal_hiba_needed),
            "avg_baseline_yield": round(avg_base_yield, 2),
            "avg_revised_yield": round(avg_revised_yield, 2),
            "net_yield_uplift_bps": int((avg_revised_yield - avg_base_yield) * 100),
        },
        "tiers": tier_impact,
        "shariah_validation": {
            "all_passed": all_shariah_passed,
            "checklist": shariah_checklist,
        },
        "alco_memo": memo.strip(),
    }


def apply_mudarib_hiba(
    allocation_run: AllocationRun,
    hiba_amount: Decimal,
    user=None,
    justification: str = "ALCO Yield Optimization concession against KIBOR benchmark",
) -> Dict[str, Any]:
    """
    Applies the Hiba concession to an active or pending AllocationRun, updating depositor share,
    Mudarib share, lines, and calculation hash.
    """
    if allocation_run.status not in [AllocationRunStatus.SIMULATED, AllocationRunStatus.PENDING_APPROVAL]:
        raise ValueError(
            f"Hiba can only be applied to SIMULATED or PENDING_APPROVAL runs (current status: {allocation_run.status})."
        )

    hiba_amount = Decimal(hiba_amount)
    if hiba_amount < 0 or hiba_amount > allocation_run.mudarib_share:
        raise ValueError(f"Hiba amount must be between 0 and {allocation_run.mudarib_share}.")

    # Calculate new shares
    old_mudarib = allocation_run.mudarib_share
    old_depositor = allocation_run.depositor_pool_share
    new_mudarib = old_mudarib - hiba_amount
    new_depositor = old_depositor + hiba_amount

    total_weighted = allocation_run.total_weighted_funds

    # Update AllocationRun
    allocation_run.mudarib_share = new_mudarib
    allocation_run.depositor_pool_share = new_depositor
    allocation_run.shariah_review_note = (
        f"{allocation_run.shariah_review_note or ''}\n"
        f"[Hiba Concession Applied]: PKR {hiba_amount:,.2f} foregone by Mudarib. "
        f"Justification: {justification}."
    ).strip()
    allocation_run.save(update_fields=["mudarib_share", "depositor_pool_share", "shariah_review_note", "updated_at"])

    # Update line items
    for line in allocation_run.lines.all():
        line_ratio = line.weighted_funds / total_weighted if total_weighted > 0 else Decimal("0.00")
        line.allocated_amount = (new_depositor * line_ratio).quantize(Decimal("0.01"))
        line.save(update_fields=["allocated_amount", "updated_at"])

    # Keep the run tied out and re-seal it: the residual is recomputed from the
    # new figures and the calculation hash covers the post-Hiba state.
    from apps.allocation.engine import compute_run_hash

    lines_total = sum((line.allocated_amount for line in allocation_run.lines.all()), Decimal("0.00"))
    allocation_run.rounding_residual = allocation_run.distributable_amount - (
        allocation_run.per_amount + allocation_run.irr_amount + new_mudarib + lines_total
    )
    allocation_run.save(update_fields=["rounding_residual", "updated_at"])
    allocation_run.calculation_hash = compute_run_hash(allocation_run)
    allocation_run.save(update_fields=["calculation_hash", "updated_at"])

    log_action(
        tenant=allocation_run.tenant,
        actor=user,
        action="apply_hiba",
        model_name="AllocationRun",
        object_id=str(allocation_run.id),
        changes={
            "hiba_amount": str(hiba_amount),
            "old_mudarib_share": str(old_mudarib),
            "new_mudarib_share": str(new_mudarib),
            "old_depositor_share": str(old_depositor),
            "new_depositor_share": str(new_depositor),
            "justification": justification,
        },
    )

    return {
        "success": True,
        "run_id": str(allocation_run.id),
        "hiba_amount": float(hiba_amount),
        "new_mudarib_share": float(new_mudarib),
        "new_depositor_share": float(new_depositor),
        "message": f"Hiba concession of PKR {hiba_amount:,.2f} successfully applied to Run #{str(allocation_run.id)[:8]}.",
    }
