"""
Period close (BRD 6.2 / 7.3, UI Catalogue Screen 16).

A pool period is closed in three controlled steps:

1. **Gates** are computed server-side from the records - they can never be ticked by hand:
   - Gate 1  inputs present: balances (bank pool) / a published NAV (investment pool) for the period, and no
             balance-import batch in exception;
   - Gate 2  economics approved: an approved profit-sharing ratio (and, for bank pools, approved weightages)
             in force for the period;
   - Gate 3  no open high/critical exception for the pool;
   - Gate 4  the period's profit run is signed (allocation run / investment distribution);
   - Gate 5  that run's journal batch is posted and balanced.
   Community circles have no profit run; gates 1, 2, 4 and 5 do not apply to them.
2. **Sign-off** by three different people in their own roles: the pool manager, a Shariah reviewer
   (Secretariat or Board) and a finance checker. Sign-off is only possible while every gate passes.
3. **Lock** by a finance checker or authorized signatory once certified; the gates are re-checked at that moment.
   A locked period accepts no new data (`period_lock`); corrections go through a restatement.
"""

import hashlib
import json

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.audit import log_action

from .models import BalanceImportBatch, DailyBalance, PeriodCloseStatus

SIGN_OFF_ROLES = {
    "pool_manager": {"pool_manager"},
    "shariah_reviewer": {"shariah_secretariat", "shariah_board"},
    "cfo_checker": {"finance_checker"},
}
LOCK_ROLES = {"finance_checker", "authorized_signatory"}


def _gate(passed, label, details, applicable=True):
    return {"passed": bool(passed), "applicable": applicable, "label": label, "details": details}


def _signed_run(pool, start, end):
    """The signed profit run that covers the period, and its journal batch (or None)."""
    model = pool.product.operating_model
    if model == "bank_pool":
        from apps.allocation.models import AllocationRun, AllocationRunStatus

        run = (
            AllocationRun._base_manager.filter(
                tenant_id=pool.tenant_id, pool=pool, status=AllocationRunStatus.SIGNED,
                value_date__gte=start, value_date__lte=end,
            )
            .order_by("-value_date")
            .first()
        )
        batch = getattr(run, "journal_batch", None) if run else None
        return run, batch
    if model == "investment_pool":
        from apps.accounting.models import JournalBatch
        from apps.investments.models import DistributionRunStatus, InvestmentDistributionRun

        run = (
            InvestmentDistributionRun._base_manager.filter(
                tenant_id=pool.tenant_id, pool=pool, status=DistributionRunStatus.SIGNED,
                period_end__gte=start, period_end__lte=end,
            )
            .order_by("-period_end")
            .first()
        )
        batch = JournalBatch._base_manager.filter(investment_run=run).first() if run else None
        return run, batch
    return None, None


def compute_gates(period_close):
    pool = period_close.pool
    start, end = period_close.period_start, period_close.period_end
    model = pool.product.operating_model
    is_circle = model == "community_circle"
    gates = {}

    # Gate 1 - inputs present
    exception_batches = BalanceImportBatch._base_manager.filter(
        pool=pool, value_date__gte=start, value_date__lte=end, status="exception"
    ).count()
    if model == "investment_pool":
        from apps.investments.models import NAVSnapshot, NAVSnapshotStatus

        has_inputs = NAVSnapshot._base_manager.filter(
            pool=pool, status=NAVSnapshotStatus.PUBLISHED, valuation_date__gte=start, valuation_date__lte=end
        ).exists()
        what = "a published NAV in the period"
    else:
        has_inputs = DailyBalance._base_manager.filter(pool=pool, value_date__gte=start, value_date__lte=end).exists()
        what = "balances for the period"
    gates["reconciled"] = _gate(
        is_circle or (has_inputs and exception_batches == 0),
        "Gate 1: Period inputs complete and reconciled",
        "Not applicable to a community circle." if is_circle else (
            f"Missing {what}." if not has_inputs else
            f"{exception_batches} balance import batch(es) in exception." if exception_batches else
            f"{what.capitalize()} recorded; no import batch in exception."
        ),
        applicable=not is_circle,
    )

    # Gate 2 - economics approved for the whole period
    if is_circle:
        gates["shariah_parameters_sealed"] = _gate(True, "Gate 2: Economics approved", "Not applicable.", False)
    else:
        from apps.allocation.models import PSRStatus, ProfitSharingRatio, WeightageBand, WeightageBandStatus

        def covering(qs, day):
            return qs.filter(effective_from__lte=day).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=day))

        psr = ProfitSharingRatio._base_manager.filter(pool=pool, status=PSRStatus.APPROVED)
        psr_ok = covering(psr, start).exists() and covering(psr, end).exists()
        bands_ok = True
        if model == "bank_pool":
            bands = WeightageBand._base_manager.filter(pool=pool, status=WeightageBandStatus.APPROVED)
            bands_ok = covering(bands, start).exists() and covering(bands, end).exists()
        gates["shariah_parameters_sealed"] = _gate(
            psr_ok and bands_ok,
            "Gate 2: Economics approved for the period",
            "Approved PSR" + (" and weightages" if model == "bank_pool" else "") + " in force for the whole period."
            if psr_ok and bands_ok else
            "No approved PSR covers the whole period." if not psr_ok else "No approved weightages cover the whole period.",
        )

    # Gate 3 - exceptions
    from apps.governance.models import ExceptionCase

    open_exceptions = ExceptionCase._base_manager.filter(
        pool=pool, status__in=["open", "investigating"], severity__in=["high", "critical"]
    ).count()
    gates["exceptions_cleared"] = _gate(
        open_exceptions == 0,
        "Gate 3: No open high/critical exceptions",
        "None open." if open_exceptions == 0 else f"{open_exceptions} high/critical exception(s) still open.",
    )

    # Gates 4 and 5 - signed run and its balanced journal
    run, batch = _signed_run(pool, start, end)
    gates["allocation_signed"] = _gate(
        is_circle or run is not None,
        "Gate 4: Profit run for the period signed",
        "Not applicable to a community circle." if is_circle else (
            f"Signed run {str(run.id)[:8]}." if run else "No signed profit run ends inside this period."
        ),
        applicable=not is_circle,
    )
    balanced = batch is not None and batch.total_debit == batch.total_credit
    gates["journals_posted"] = _gate(
        is_circle or balanced,
        "Gate 5: Run journal posted and balanced",
        "Not applicable to a community circle." if is_circle else (
            f"Journal {str(batch.id)[:8]} balanced at {batch.total_debit}." if balanced else
            "The signed run has no balanced journal batch." if run else "No signed run, so no journal."
        ),
        applicable=not is_circle,
    )
    return gates, run


def auto_verify_period_gates(period_close, user=None):
    if period_close.status == PeriodCloseStatus.LOCKED:
        raise ValidationError("A locked period is not re-verified.")
    gates, _run = compute_gates(period_close)
    all_passed = all(g["passed"] for g in gates.values())
    data = dict(period_close.checklist_data or {})
    data.update({key: g["passed"] for key, g in gates.items()})
    data["gate_telemetry"] = gates
    data["last_auto_verified_at"] = timezone.now().isoformat()
    data["all_gates_passed"] = all_passed
    period_close.checklist_data = data
    period_close.save(update_fields=["checklist_data", "updated_at"])
    return {"success": True, "period_close_id": str(period_close.id), "all_passed": all_passed, "gates": gates}


def sign_off_period_role(period_close, user, role, notes="", fatwa_ref=""):
    if role not in SIGN_OFF_ROLES:
        raise ValidationError(f"Unknown sign-off role '{role}'. Allowed: {sorted(SIGN_OFF_ROLES)}.")
    if user.role not in SIGN_OFF_ROLES[role]:
        raise PermissionDenied(f"Signing as '{role}' needs one of these roles: {sorted(SIGN_OFF_ROLES[role])}.")
    if period_close.status in (PeriodCloseStatus.CERTIFIED, PeriodCloseStatus.LOCKED):
        raise ValidationError(f"The period is already {period_close.status}.")

    gates, _run = compute_gates(period_close)
    failing = [g["label"] for g in gates.values() if not g["passed"]]
    if failing:
        raise ValidationError({"gates": failing})

    data = dict(period_close.checklist_data or {})
    signoffs = dict(data.get("multi_role_signoffs") or {})
    if role != "pool_manager" and not signoffs.get("pool_manager", {}).get("signed"):
        raise ValidationError("The pool manager signs first.")
    if signoffs.get(role, {}).get("signed"):
        raise ValidationError(f"'{role}' has already signed this period.")
    if any(entry.get("user_id") == str(user.id) for entry in signoffs.values() if entry.get("signed")):
        raise ValidationError("Each sign-off must be given by a different person.")
    if role == "shariah_reviewer" and not fatwa_ref.strip():
        raise ValidationError({"fatwa_ref": ["The Shariah reviewer cites the ruling the period was reviewed against."]})

    signoffs[role] = {
        "signed": True, "user_id": str(user.id), "user_name": user.full_name, "user_role": user.role,
        "signed_at": timezone.now().isoformat(), "notes": notes, "fatwa_ref": fatwa_ref if role == "shariah_reviewer" else None,
    }
    data["multi_role_signoffs"] = signoffs
    data["gate_telemetry"] = gates
    period_close.checklist_data = data

    if role == "pool_manager":
        period_close.status = PeriodCloseStatus.IN_REVIEW
    if all(signoffs.get(r, {}).get("signed") for r in SIGN_OFF_ROLES):
        period_close.status = PeriodCloseStatus.CERTIFIED
        period_close.certified_by = user
        period_close.certified_at = timezone.now()
        period_close.decision_note = notes or "Certified by pool manager, Shariah reviewer and finance checker."
    period_close.save(update_fields=["status", "checklist_data", "certified_by", "certified_at", "decision_note", "updated_at"])

    log_action(
        tenant=period_close.tenant, actor=user, action="period_sign_off", model_name="PeriodCloseChecklist",
        object_id=str(period_close.id), changes={"role": role, "status": period_close.status}, reason=notes or None,
    )
    return {"success": True, "period_close_id": str(period_close.id), "role": role, "status": period_close.status,
            "signoffs": signoffs}


def execute_cryptographic_lock_ceremony(period_close, user, lock_note=""):
    if user.role not in LOCK_ROLES:
        raise PermissionDenied("Only a finance checker or an authorized signatory locks a period.")
    if period_close.status != PeriodCloseStatus.CERTIFIED:
        raise ValidationError(f"Only a certified period can be locked (this one is {period_close.status}).")
    gates, run = compute_gates(period_close)
    failing = [g["label"] for g in gates.values() if not g["passed"]]
    if failing:
        raise ValidationError({"gates": failing})

    data = dict(period_close.checklist_data or {})
    payload = {
        "tenant_id": str(period_close.tenant_id), "pool_id": str(period_close.pool_id),
        "period_start": str(period_close.period_start), "period_end": str(period_close.period_end),
        "run_id": str(run.id) if run else None, "run_hash": getattr(run, "calculation_hash", None),
        "signoffs": data.get("multi_role_signoffs"), "locked_by": str(user.id),
    }
    seal = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest().upper()
    now = timezone.now()
    package = build_close_certificate(period_close, run, seal=seal, locked_by=user.full_name, locked_at=now)

    data.update({"cryptographic_seal": seal, "sha256_hash": seal, "locked_at": now.isoformat(),
                 "locked_by": user.full_name, "sbp_filing_package": package, "lock_note": lock_note, "gate_telemetry": gates})
    period_close.status = PeriodCloseStatus.LOCKED
    period_close.checklist_data = data
    period_close.save(update_fields=["status", "checklist_data", "updated_at"])
    log_action(
        tenant=period_close.tenant, actor=user, action="lock", model_name="PeriodCloseChecklist",
        object_id=str(period_close.id),
        changes={"status": {"before": PeriodCloseStatus.CERTIFIED, "after": PeriodCloseStatus.LOCKED}, "seal": seal},
        reason=lock_note or None,
    )
    return {"success": True, "period_close_id": str(period_close.id), "status": PeriodCloseStatus.LOCKED,
            "cryptographic_seal": seal, "locked_at": now.isoformat(), "locked_by": user.full_name, "sbp_package": package}


def build_close_certificate(period_close, run, seal=None, locked_by=None, locked_at=None):
    """A factual close summary from recorded data. It is an internal record, not a regulatory filing."""
    signoffs = (period_close.checklist_data or {}).get("multi_role_signoffs") or {}
    summary = None
    if run is not None and hasattr(run, "depositor_pool_share"):  # bank-pool allocation run
        summary = {
            "gross_income_pkr": str(run.gross_income), "direct_expenses_pkr": str(run.direct_expenses),
            "distributable_profit_pkr": str(run.distributable_amount), "mudarib_share_pkr": str(run.mudarib_share),
            "depositor_pool_share_pkr": str(run.depositor_pool_share),
        }
    elif run is not None:  # investment distribution run
        summary = {
            "gross_income_pkr": str(run.gross_income), "direct_expenses_pkr": str(run.direct_expenses),
            "distributable_profit_pkr": str(run.distributable_amount), "manager_share_pkr": str(run.manager_share),
            "investor_share_pkr": str(run.investor_share),
        }
    return {
        "certificate_id": f"CLOSE-{period_close.pool.code}-{period_close.period_end:%Y%m}",
        "pool_name": period_close.pool.name,
        "pool_code": period_close.pool.code,
        "period_range": f"{period_close.period_start} to {period_close.period_end}",
        "status": period_close.status,
        "is_locked": period_close.status == PeriodCloseStatus.LOCKED,
        "cryptographic_seal": seal or "NOT LOCKED",
        "run_id": str(run.id) if run else None,
        "financial_summary": summary,
        "signatories": {role: entry.get("user_name") for role, entry in signoffs.items() if entry.get("signed")},
        "locked_by": locked_by,
        "locked_at": locked_at.isoformat() if locked_at else None,
        "statement": (
            "Generated by Amanah Pool OS from the recorded gates, sign-offs and the signed run of this period. "
            "It is an internal close record, not a regulatory filing."
        ),
    }


def get_sbp_filing_certificate(period_close):
    data = period_close.checklist_data or {}
    if data.get("sbp_filing_package"):
        return data["sbp_filing_package"]
    _gates, run = compute_gates(period_close)
    return build_close_certificate(period_close, run)
