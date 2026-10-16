"""
Signed calculation manifest (BRD 7 engine principle, 14 auditability). The calculation hash seals the run's inputs, rule
versions, amounts and lines when it is created. At signing, a second hash seals the evidence around it: that calculation
hash, the people who prepared, checked, reviewed and released it, every daily balance row of the period, and every line of
the journal it posted. Recomputing it later shows whether any of that evidence changed.
"""

import hashlib
import json

from apps.pools.models import DailyBalance


def evidence_payload(run):
    balances = (
        DailyBalance._base_manager.filter(pool_id=run.pool_id, value_date__gte=run.effective_period_start, value_date__lte=run.value_date)
        .exclude(status="rejected").order_by("value_date", "participant_class", "account_id", "id")
    )
    batch = getattr(run, "journal_batch", None)
    entries = sorted(
        ((e.account_key, e.gl_code, e.entry_type, str(e.amount)) for e in batch.entries.all()) if batch else [],
    )
    return {
        "calculation_hash": run.calculation_hash,
        "approvers": {
            "prepared_by": run.created_by_id, "checked_by": run.checked_by_id,
            "shariah_reviewed_by": run.shariah_signed_off_by_id, "released_by": run.released_by_id,
        },
        "balances": [
            [str(b.value_date), b.participant_class, str(b.account_id) if b.account_id else None, str(b.balance_amount)]
            for b in balances
        ],
        "journal": [list(e) for e in entries],
    }


def compute_evidence_hash(run):
    return hashlib.sha256(json.dumps(evidence_payload(run), sort_keys=True, default=str).encode()).hexdigest()
