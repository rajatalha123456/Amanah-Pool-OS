"""
Annual Shariah audit report (BRD section 8 "Shariah audit": risk-based plan, samples, findings, management responses,
remediation and annual report). Built only from the recorded plans and findings of the year; sealed with SHA-256.
"""

import hashlib
import json
from collections import Counter

from django.utils import timezone

from .models import ShariahAuditFinding, ShariahAuditPlan


def build_annual_report(tenant, year):
    plans = list(ShariahAuditPlan._base_manager.filter(tenant=tenant, plan_year=year).order_by("created_at"))
    findings = list(
        ShariahAuditFinding._base_manager.filter(tenant=tenant, audit_plan__plan_year=year)
        .select_related("pool", "audit_plan").order_by("created_at")
    )
    today = timezone.localdate()
    open_findings = [f for f in findings if f.status not in ("resolved", "closed", "remediated")]
    with_response = [f for f in findings if (f.management_response or "").strip()]
    body = {
        "tenant": tenant.code,
        "year": year,
        "plans": [
            {
                "title": p.title, "scope": p.scope, "frequency": p.frequency, "status": p.status,
                "target_samples": p.target_samples_count, "tested_samples": p.tested_samples_count,
                "coverage_pct": round(p.tested_samples_count / p.target_samples_count * 100, 1) if p.target_samples_count else None,
                "approved": p.approved_by_id is not None,
            }
            for p in plans
        ],
        "findings": {
            "total": len(findings),
            "by_severity": dict(Counter(f.severity for f in findings)),
            "by_status": dict(Counter(f.status for f in findings)),
            "open": len(open_findings),
            "with_management_response": len(with_response),
            "response_rate_pct": round(len(with_response) / len(findings) * 100, 1) if findings else None,
            "oldest_open_age_days": max(((today - f.created_at.date()).days for f in open_findings), default=None),
            "items": [
                {
                    "title": f.title, "severity": f.severity, "status": f.status, "pool": f.pool.code if f.pool_id else None,
                    "observation": f.observation, "management_response": f.management_response or "",
                    "age_days": (today - f.created_at.date()).days,
                }
                for f in findings
            ],
        },
        "basis": (
            "Built from the Shariah audit plans and findings recorded for the year. A figure with no source is null. "
            "This is the platform's record; the formal annual report is signed by the Shariah Board."
        ),
    }
    seal = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    return {**body, "generated_at": timezone.now().isoformat(), "content_hash": seal}
