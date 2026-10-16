"""
Rule-based (v1) anomaly detection for AllocationRun, run when the maker submits the run for checking (BRD 6.2 step 12:
before anyone approves it) and again when it is signed. Compares the
just-signed run's profit margin and per-participant-class allocation ratios
against the trailing 5-run average for the same pool; flags a deviation of
40% or more as an ExceptionCase for Risk & Compliance to triage.

This is intentionally simple (a moving average + percentage threshold), not
a statistical or ML model - see the README's "Allocation Anomaly Detector"
section for why, and for how this differs from Mizan (the team's separate,
general-purpose anomaly detection tool).
"""

from decimal import Decimal

from apps.core.exceptions_helper import create_exception_case
from apps.ai_agents.models import is_ai_model_enabled

from .models import AllocationRun, AllocationRunStatus

BASELINE_RUN_COUNT = 5
DEVIATION_THRESHOLD = Decimal("0.40")
HIGH_SEVERITY_THRESHOLD = Decimal("0.60")


def _profit_margin(run: AllocationRun) -> Decimal:
    if run.gross_income == 0:
        return Decimal("0")
    return run.distributable_amount / run.gross_income


def _deviation(current: Decimal, average: Decimal) -> Decimal | None:
    """Relative deviation of `current` from `average`, or None if `average` is 0 (can't compute a ratio)."""
    if average == 0:
        return None
    return abs(current - average) / abs(average)


def check_for_anomalies(allocation_run: AllocationRun, user=None) -> bool:
    """
    Compares `allocation_run` against the trailing BASELINE_RUN_COUNT signed
    runs for the same pool. Raises one ExceptionCase (the first metric found
    to deviate by >= DEVIATION_THRESHOLD) if an anomaly is found.

    Returns True if an anomaly was detected (and an ExceptionCase created),
    False otherwise - including when there isn't enough history yet to form
    a baseline, in which case no check is performed at all.
    """

    if not is_ai_model_enabled("allocation_anomaly_detector"):
        return False

    # Already flagged at submission: one case per run, not one per stage.
    from apps.governance.models import ExceptionCase

    if ExceptionCase._base_manager.filter(
        source_module="allocation", source_object_id=str(allocation_run.id), title__startswith="Unusual allocation pattern"
    ).exists():
        return True

    baseline_runs = list(
        AllocationRun.objects.filter(
            pool=allocation_run.pool,
            status=AllocationRunStatus.SIGNED,
        )
        .exclude(id=allocation_run.id)
        .order_by("-value_date")[:BASELINE_RUN_COUNT]
    )

    if len(baseline_runs) < BASELINE_RUN_COUNT:
        return False

    # --- Metric 1: profit margin (distributable_amount / gross_income) ---
    current_margin = _profit_margin(allocation_run)
    baseline_margins = [_profit_margin(run) for run in baseline_runs]
    average_margin = sum(baseline_margins) / len(baseline_margins)

    margin_deviation = _deviation(current_margin, average_margin)
    if margin_deviation is not None and margin_deviation >= DEVIATION_THRESHOLD:
        _raise_anomaly(
            allocation_run,
            metric_label="Profit margin",
            current_value=current_margin,
            average_value=average_margin,
            deviation=margin_deviation,
            user=user,
        )
        return True

    # --- Metric 2: per-participant-class allocated_amount / daily_funds ratio ---
    baseline_lines_by_class: dict[str, list[Decimal]] = {}
    for run in baseline_runs:
        for line in run.lines.all():
            if line.daily_funds == 0:
                continue
            ratio = line.allocated_amount / line.daily_funds
            baseline_lines_by_class.setdefault(line.participant_class, []).append(ratio)

    for line in allocation_run.lines.all():
        if line.daily_funds == 0:
            continue
        current_ratio = line.allocated_amount / line.daily_funds

        class_baseline = baseline_lines_by_class.get(line.participant_class)
        if not class_baseline:
            continue

        average_ratio = sum(class_baseline) / len(class_baseline)
        ratio_deviation = _deviation(current_ratio, average_ratio)
        if ratio_deviation is not None and ratio_deviation >= DEVIATION_THRESHOLD:
            _raise_anomaly(
                allocation_run,
                metric_label=f"Allocation ratio for '{line.participant_class}'",
                current_value=current_ratio,
                average_value=average_ratio,
                deviation=ratio_deviation,
                user=user,
            )
            return True

    return False


def _raise_anomaly(
    allocation_run: AllocationRun,
    metric_label: str,
    current_value: Decimal,
    average_value: Decimal,
    deviation: Decimal,
    user=None,
) -> None:
    severity = "high" if deviation >= HIGH_SEVERITY_THRESHOLD else "medium"

    current_pct = current_value * 100
    average_pct = average_value * 100
    deviation_pct = deviation * 100

    description = (
        f"{metric_label} {current_pct:.2f}% is {deviation_pct:.2f}% different from the "
        f"{BASELINE_RUN_COUNT}-run average of {average_pct:.2f}%."
    )
    case = create_exception_case(
        tenant=allocation_run.tenant,
        source_module="allocation",
        source_object_id=str(allocation_run.id),
        pool=allocation_run.pool,
        severity=severity,
        title=f"Unusual allocation pattern detected on {allocation_run.pool.code} for {allocation_run.value_date}",
        description=description,
        detected_by="system",
    )
    _record(allocation_run, user or allocation_run.released_by, case, metric_label, current_value, average_value, deviation, severity, description)


def _record(run, user, case, metric_label, current_value, average_value, deviation, severity, description):
    """BR-009: the output shows its source, confidence, reason and a human disposition (advisory only, reason codes visible)."""
    if user is None:
        return
    from apps.ai_agents.recording import record_ai_output

    record_ai_output(
        user=user, feature="allocation_anomaly", model_name="allocation_anomaly_detector",
        prompt={"run": str(run.id), "pool": run.pool.code, "baseline_runs": BASELINE_RUN_COUNT},
        output={
            "reason_code": "DEVIATION_FROM_BASELINE", "metric": metric_label, "current": str(current_value),
            "baseline_average": str(average_value), "deviation": str(deviation), "threshold": str(DEVIATION_THRESHOLD),
            "severity": severity, "exception_case_id": str(case.id),
        },
        sources=[{"type": "allocation_runs", "detail": f"trailing {BASELINE_RUN_COUNT} signed runs of {run.pool.code}"}],
        confidence=None, reason=description, requires_review=True, subject_type="AllocationRun", subject_id=str(run.id),
    )
