"""
AI Audit Sampling & Risk Ranker Engine (BRD Section 9 / Screen 33 & Screen 40).
Calculates tenant-wide composite Shariah & financial risk scores, identifies
anomalies, and extracts stratified risk-weighted sample sets for SBP inspection.
"""

import logging
from decimal import Decimal
from django.utils import timezone
from apps.allocation.models import AllocationRun
from apps.governance.models import ExceptionCase, PurificationEntry, RelatedPartyTransaction
from apps.pools.models import Pool

logger = logging.getLogger("apps")


def perform_audit_sampling_analysis(tenant) -> dict:
    """
    Scans all institutional activity for the given tenant, computes
    risk weighting across Fiqh, financial variance, and governance parameters,
    and returns a stratified sample set with AI audit recommendations.
    """
    # 1. Gather live records
    allocation_runs = list(AllocationRun.objects.filter(tenant=tenant).order_by("-created_at")[:20])
    exceptions = list(ExceptionCase.objects.filter(tenant=tenant).order_by("-created_at"))
    purifications = list(PurificationEntry.objects.filter(tenant=tenant).order_by("-created_at"))
    related_parties = list(RelatedPartyTransaction.objects.filter(tenant=tenant).order_by("-created_at"))
    pools = list(Pool.objects.filter(tenant=tenant))

    # 2. Risk Evaluation Metrics
    unpurified_entries = [p for p in purifications if p.status == "identified"]
    critical_exceptions = [e for e in exceptions if e.status != "resolved" and e.severity == "critical"]
    high_exceptions = [e for e in exceptions if e.status != "resolved" and e.severity == "high"]
    restated_runs = [r for r in allocation_runs if r.is_restatement or r.replaces_run_id is not None]
    flagged_rp = [rp for rp in related_parties if rp.disclosure_status in ["flagged", "pending_review"]]

    # Calculate sub-scores (0-100 scale)
    shariah_risk = min(100, (len(unpurified_entries) * 35) + (len(flagged_rp) * 15) + (5 if any(p.status != "active" for p in pools) else 0))
    financial_variance_risk = min(100, (len(restated_runs) * 40) + (len(critical_exceptions) * 25) + (len(high_exceptions) * 15))
    operational_governance_risk = min(100, (len(exceptions) * 8) + 12)

    composite_score = int(round((shariah_risk * 0.40) + (financial_variance_risk * 0.35) + (operational_governance_risk * 0.25)))
    composite_score = max(0, min(composite_score, 100))
    # A ranking aid for choosing what to look at first - NOT an audit opinion or a compliance conclusion.
    if composite_score <= 25:
        risk_tier = "LOW"
    elif composite_score <= 50:
        risk_tier = "MODERATE"
    elif composite_score <= 75:
        risk_tier = "ELEVATED"
    else:
        risk_tier = "HIGH"
    opinion = "No opinion is expressed: this is a rule-based ranking of items to inspect."

    # 3. Build Stratified Risk Samples
    sample_items = []

    # Check unpurified entries
    for p in unpurified_entries[:2]:
        sample_items.append({
            "entity_type": "PurificationEntry",
            "entity_id": str(p.id),
            "reference_code": f"PUR-{str(p.id)[:8].upper()}",
            "risk_score": 92,
            "severity": "CRITICAL",
            "title": f"Unpurified Impermissible Income (PKR {p.amount:,.2f})",
            "anomaly_reason": f"Non-halal income source '{p.source_description}' has been identified but not yet disbursed to verified charity, posing Shariah non-compliance risk.",
            "suggested_audit_procedure": "Inspect original transaction bank advice, review Shariah Board fatwa, and verify charitable payout disbursement voucher.",
        })

    # Check critical / high exceptions
    for exc in (critical_exceptions + high_exceptions)[:3]:
        sample_items.append({
            "entity_type": "ExceptionCase",
            "entity_id": str(exc.id),
            "reference_code": f"EXC-{str(exc.id)[:8].upper()}",
            "risk_score": 85 if exc.severity == "critical" else 72,
            "severity": exc.severity.upper(),
            "title": exc.title,
            "anomaly_reason": f"Module '{exc.source_module}' raised anomaly: '{exc.description[:120]}'. Requires independent maker-checker clearance.",
            "suggested_audit_procedure": "Cross-reference CBS raw balance feed with general ledger batch and review treatment plan sign-offs.",
        })

    # Check restated allocation runs or latest allocation run
    for run in allocation_runs[:2]:
        is_restated = run.is_restatement or run.replaces_run_id is not None
        val_date_str = run.value_date.strftime('%Y%m') if getattr(run, "value_date", None) else "202609"
        sample_items.append({
            "entity_type": "AllocationRun",
            "entity_id": str(run.id),
            "reference_code": f"RUN-{val_date_str}-{str(run.id)[:6].upper()}",
            "risk_score": 88 if is_restated else 45,
            "severity": "CRITICAL" if is_restated else "MEDIUM",
            "title": f"Profit Allocation Run ({run.pool.name})",
            "anomaly_reason": "Run experienced historical restatement; requires verification of contra-GL postings." if is_restated else f"Routine allocation cycle with distributable profit of PKR {run.distributable_amount:,.2f} and SHA-256 hash manifest verification.",
            "suggested_audit_procedure": "Verify immutable calculation hash, recalculate PER/IRR deductions against SBP guidelines, and verify subledger journal postings.",
        })

    # Check related party transactions
    for rp in flagged_rp[:2]:
        sample_items.append({
            "entity_type": "RelatedPartyTransaction",
            "entity_id": str(rp.id),
            "reference_code": f"RPT-{str(rp.id)[:8].upper()}",
            "risk_score": 68,
            "severity": "HIGH",
            "title": f"Related Party Exposure - {rp.related_party_name}",
            "anomaly_reason": f"Transaction of PKR {rp.amount:,.2f} involving {rp.relationship_type} currently under status '{rp.disclosure_status}'. Requires arm's length verification.",
            "suggested_audit_procedure": "Verify board audit committee resolution, check transfer pricing benchmark, and evaluate potential conflict of interest disclosures.",
        })

    # Assign ranks
    sample_items.sort(key=lambda x: x["risk_score"], reverse=True)
    for index, item in enumerate(sample_items, start=1):
        item["rank"] = index

    # 4. Generate AI Workpaper Memorandum
    total_samples = len(sample_items)
    memo_date = timezone.now().strftime("%d %B %Y")
    audit_memo = (
        f"AUDIT SAMPLING WORKING NOTE (rule-based, for the auditor's use)\n"
        f"========================================================================\n"
        f"Generated At          : {memo_date}\n"
        f"Institution           : {tenant.name}\n"
        f"Risk ranking score    : {composite_score} / 100 ({risk_tier})\n"
        f"Opinion               : {opinion}\n"
        f"========================================================================\n\n"
        f"1. EXECUTIVE OVERVIEW:\n"
        f"The AI Audit Sampling Engine performed an automated comprehensive scan across {len(allocation_runs)} "
        f"profit allocation runs, {len(exceptions)} operational exceptions, {len(purifications)} purification "
        f"entries, and {len(related_parties)} related-party disclosures.\n\n"
        f"2. RISK DECOMPOSITION:\n"
        f" - Shariah Non-Compliance Risk Index : {shariah_risk}/100\n"
        f" - Financial & Allocation Variance    : {financial_variance_risk}/100\n"
        f" - Operational & Control Integrity   : {operational_governance_risk}/100\n\n"
        f"3. STRATIFIED AUDIT SAMPLE RECOMMENDATION:\n"
        f"{total_samples} items were selected by fixed rules (unpurified income, open high/critical exceptions, "
        f"restated or latest runs, flagged related-party transactions). The selection is a risk-ranked starting "
        f"point, not a statistically derived sample, and carries no confidence level. The auditor decides the "
        f"actual sample and procedures.\n"
    )

    return {
        "success": True,
        "composite_risk_score": composite_score,
        "risk_tier": risk_tier,
        "compliance_opinion": opinion,
        "metrics": {
            "shariah_risk": shariah_risk,
            "financial_variance_risk": financial_variance_risk,
            "operational_governance_risk": operational_governance_risk,
            "total_pools_audited": len(pools),
            "unpurified_count": len(unpurified_entries),
            "critical_exceptions_count": len(critical_exceptions),
            "allocation_runs_audited": len(allocation_runs),
        },
        "sample_items": sample_items,
        "memorandum": audit_memo,
        "generated_at": timezone.now().isoformat(),
    }
