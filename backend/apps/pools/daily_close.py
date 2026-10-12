"""
Daily close of a pool (BRD 6.2). The maker prepares it (the server computes the gates); an independent checker
signs it. A signed day refuses new balance imports and income / expense events dated on it.
"""

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import ConflictError

from .models import DailyBalance, DailyBalanceStatus, DailyClose, DailyCloseStatus, PoolStatus
from .period_lock import assert_period_open

ACTIVE = (PoolStatus.OPEN, PoolStatus.ALLOCATION, PoolStatus.FROZEN)


def _gate(key, label, passed, detail=""):
    return {"key": key, "label": label, "passed": bool(passed), "detail": detail}


def compute_gates(pool, day):
    from apps.accounting.models import ReconciliationBatch, ReconciliationStatus
    from apps.governance.models import ExceptionCase, ExceptionSeverity, ExceptionStatus

    model = pool.product.operating_model
    gates = []

    if model == "bank_pool":
        validated = DailyBalance._base_manager.filter(pool=pool, value_date=day, status=DailyBalanceStatus.VALIDATED).count()
        gates.append(_gate("balances_imported", "End-of-day balances imported and validated", validated > 0,
                           f"{validated} validated balance row(s) for {day}."))
        flagged = DailyBalance._base_manager.filter(pool=pool, value_date=day).filter(status=DailyBalanceStatus.PENDING).count()
        gates.append(_gate("no_unvalidated_balances", "No balance row left pending", flagged == 0,
                           f"{flagged} row(s) still pending." if flagged else ""))
    open_serious = ExceptionCase._base_manager.filter(
        pool=pool, status__in=[ExceptionStatus.OPEN, ExceptionStatus.INVESTIGATING],
        severity__in=[ExceptionSeverity.HIGH, ExceptionSeverity.CRITICAL],
    ).count()
    gates.append(_gate("exceptions_resolved", "No high / critical exception left open", open_serious == 0,
                       f"{open_serious} open." if open_serious else ""))
    unresolved = ReconciliationBatch._base_manager.filter(
        pool=pool, reconciliation_date=day, status=ReconciliationStatus.VARIANCE_FLAGGED
    ).count()
    gates.append(_gate("reconciliation_clear", "No unresolved reconciliation variance for the day", unresolved == 0,
                       f"{unresolved} batch(es) with a flagged variance." if unresolved else ""))
    return gates


def prepare(pool, day, user, notes=""):
    if pool.status not in ACTIVE:
        raise ValidationError(f"Only an active pool can be closed for the day (status: '{pool.status}').")
    assert_period_open(pool, day, what="a daily close")
    existing = DailyClose._base_manager.filter(pool=pool, value_date=day).first()
    if existing and existing.status == DailyCloseStatus.SIGNED:
        raise ConflictError("This day is already signed off.")
    gates = compute_gates(pool, day)
    status = DailyCloseStatus.PREPARED if all(g["passed"] for g in gates) else DailyCloseStatus.OPEN
    values = {
        "gates": gates, "status": status, "notes": notes, "prepared_by": user, "prepared_at": timezone.now(),
    }
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        existing.save()
        return existing
    return DailyClose.objects.create(tenant=pool.tenant, pool=pool, value_date=day, **values)


def sign(close, user):
    if close.status == DailyCloseStatus.SIGNED:
        raise ConflictError("This day is already signed off.")
    if close.prepared_by_id == user.id:
        raise ValidationError("The daily close must be signed by a different person than the one who prepared it.")
    gates = compute_gates(close.pool, close.value_date)  # re-derived: things may have changed since preparation
    failed = [g for g in gates if not g["passed"]]
    if failed:
        close.gates, close.status = gates, DailyCloseStatus.OPEN
        close.save(update_fields=["gates", "status", "updated_at"])
        raise ValidationError({"gates": [f"{g['label']}: {g['detail']}".rstrip(": ") for g in failed]})
    close.gates, close.status = gates, DailyCloseStatus.SIGNED
    close.signed_by, close.signed_at = user, timezone.now()
    close.save()
    return close


def assert_day_open(pool, day, what="a record"):
    """Inputs dated on a signed day are refused; corrections need an approved restatement."""
    if DailyClose._base_manager.filter(pool=pool, value_date=day, status=DailyCloseStatus.SIGNED).exists():
        raise ValidationError(
            f"Cannot post {what} dated {day}: the day was signed off in the daily close for pool '{pool.code}'. "
            "Back-dated changes require an approved restatement."
        )
