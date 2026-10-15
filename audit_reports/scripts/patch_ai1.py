ROOT = "backend/apps/"


def edit(path, pairs):
    s = open(ROOT + path, encoding="utf-8").read()
    for old, new in pairs:
        assert old in s, (path, old[:100])
        s = s.replace(old, new, 1)
    open(ROOT + path, "w", encoding="utf-8").write(s)


# ---- anomaly detector: every finding is recorded with its source, reason and disposition (BR-009) -----------------------
edit("allocation/anomaly_detector.py", [
    ("def check_for_anomalies(allocation_run: AllocationRun) -> bool:", "def check_for_anomalies(allocation_run: AllocationRun, user=None) -> bool:"),
    ('''            _raise_anomaly(
                allocation_run,
                metric_label=f"Allocation ratio for '{line.participant_class}'",
                current_value=current_ratio,
                average_value=average_ratio,
                deviation=ratio_deviation,
            )
            return True''', '''            _raise_anomaly(
                allocation_run,
                metric_label=f"Allocation ratio for '{line.participant_class}'",
                current_value=current_ratio,
                average_value=average_ratio,
                deviation=ratio_deviation,
                user=user,
            )
            return True'''),
    ('''    average_value: Decimal,
    deviation: Decimal,
) -> None:
    severity = "high" if deviation >= HIGH_SEVERITY_THRESHOLD else "medium"''', '''    average_value: Decimal,
    deviation: Decimal,
    user=None,
) -> None:
    severity = "high" if deviation >= HIGH_SEVERITY_THRESHOLD else "medium"'''),
    ('''    create_exception_case(
        tenant=allocation_run.tenant,
        source_module="allocation",
        source_object_id=str(allocation_run.id),
        pool=allocation_run.pool,
        severity=severity,
        title=f"Unusual allocation pattern detected on {allocation_run.pool.code} for {allocation_run.value_date}",
        description=(
            f"{metric_label} {current_pct:.2f}% is {deviation_pct:.2f}% different from the "
            f"{BASELINE_RUN_COUNT}-run average of {average_pct:.2f}%."
        ),
        detected_by="system",
    )''', '''    description = (
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
    )'''),
])
edit("allocation/views.py", [("            check_for_anomalies(run)\n", "            check_for_anomalies(run, request.user)\n")])

# ---- reconciliation copilot ---------------------------------------------------------------------------------------
edit("accounting/reconciliation.py", [
    ('''    create_exception_case(
        tenant=journal_batch.tenant,
        source_module="accounting",
        source_object_id=str(journal_batch.id),
        pool=journal_batch.pool,
        severity="high",
        title=f"GL / sub-ledger mismatch on {journal_batch.pool.code} for {run.value_date}",
        description=(
            f"Depositor payable posted to the GL: {gl_net_credit}; participant sub-ledger (allocation lines): "
            f"{subledger_total}; difference {difference}."
        ),
        detected_by="system",
    )
    return True''', '''    description = (
        f"Depositor payable posted to the GL: {gl_net_credit}; participant sub-ledger (allocation lines): "
        f"{subledger_total}; difference {difference}."
    )
    case = create_exception_case(
        tenant=journal_batch.tenant,
        source_module="accounting",
        source_object_id=str(journal_batch.id),
        pool=journal_batch.pool,
        severity="high",
        title=f"GL / sub-ledger mismatch on {journal_batch.pool.code} for {run.value_date}",
        description=description,
        detected_by="system",
    )
    if journal_batch.posted_by is not None:
        from apps.ai_agents.recording import record_ai_output

        # BR-009 and BRD 9: the reconciliation copilot only proposes; it cannot post or write off. Its finding is recorded
        # with its source, reason and a human disposition.
        record_ai_output(
            user=journal_batch.posted_by, feature="reconciliation", model_name="reconciliation_copilot",
            prompt={"journal_batch": str(journal_batch.id), "run": str(run.id)},
            output={
                "reason_code": "GL_SUBLEDGER_MISMATCH", "gl_net_credit": str(gl_net_credit),
                "subledger_total": str(subledger_total), "difference": str(difference), "exception_case_id": str(case.id),
                "proposed_action": "Investigate; nothing was posted or written off.",
            },
            sources=[{"type": "journal_batch", "detail": str(journal_batch.id)}, {"type": "allocation_lines", "detail": str(run.id)}],
            confidence=None, reason=description, requires_review=True, subject_type="JournalBatch",
            subject_id=str(journal_batch.id),
        )
    return True'''),
])
print("ok")
