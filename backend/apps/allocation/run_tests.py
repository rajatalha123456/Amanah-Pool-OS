"""
Pre-approval tests of an allocation run (BRD 6.3 step 19): tolerance, fairness, negative yield and the comparison with the
previous period. They are computed from the run's own stored figures, shown on the run, and a failing tolerance or
fairness test stops the independent check. Negative yield and the prior-period comparison are information for the
checker and the Shariah reviewer: the BRD sets no threshold for them, so none is invented here.
"""

from decimal import Decimal

CENT = Decimal("0.01")


def _yield(run):
    total = Decimal(run.total_weighted_funds or 0)
    return (Decimal(run.distributable_amount) / total) if total else None


def run_tests(run):
    lines = list(run.lines.all())
    results = []

    tolerance = CENT * (len(lines) + 3)
    residual = abs(Decimal(run.rounding_residual))
    results.append({
        "key": "tolerance", "label": "Rounding within tolerance", "status": "pass" if residual <= tolerance else "fail",
        "detail": f"residual {residual} against a tolerance of {tolerance}",
    })

    # A profit is shared by weighted funds; a loss falls on capital, i.e. on the funds themselves (BRD 7.1).
    basis = (lambda l: Decimal(l.daily_funds)) if run.is_loss else (lambda l: Decimal(l.weighted_funds))
    allocated = sum((Decimal(l.allocated_amount) for l in lines), Decimal("0"))
    total = sum((basis(l) for l in lines), Decimal("0"))
    worst = Decimal("0")
    if total:
        for line in lines:
            fair = allocated * basis(line) / total
            worst = max(worst, abs(Decimal(line.allocated_amount) - fair))
    label = "Each loss share follows capital" if run.is_loss else "Each share follows weighted funds"
    results.append({
        "key": "fairness", "label": label, "status": "pass" if worst <= CENT else "fail",
        "detail": f"largest difference from the proportional share: {worst.quantize(CENT)}",
    })

    results.append({
        "key": "negative_yield", "label": "Negative yield",
        "status": "warning" if run.is_loss else "pass",
        "detail": "the period is a loss: capital providers bear it unless negligence is established" if run.is_loss else "the period made a profit",
    })

    from .models import AllocationRun

    previous = (
        AllocationRun._base_manager.filter(pool=run.pool, status="signed", value_date__lt=run.effective_period_start)
        .exclude(pk=run.pk).order_by("-value_date").first()
    )
    now, before = _yield(run), (_yield(previous) if previous else None)
    if previous is None or now is None or before is None:
        results.append({"key": "prior_period", "label": "Compared with the previous period", "status": "info",
                        "detail": "no earlier signed run to compare with"})
    else:
        change = ((now - before) / before * 100) if before else None
        detail = f"yield on weighted funds {now * 100:.4f}% against {before * 100:.4f}% for the run ending {previous.value_date}"
        if change is not None:
            detail += f" ({change:+.1f}%)"
        results.append({"key": "prior_period", "label": "Compared with the previous period", "status": "info", "detail": detail})
    return results


def failing(run):
    return [r["label"] for r in run_tests(run) if r["status"] == "fail"]
