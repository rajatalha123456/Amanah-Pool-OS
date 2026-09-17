def create_exception_case(
    tenant,
    source_module,
    title,
    description,
    severity="medium",
    pool=None,
    source_object_id=None,
    detected_by="system",
):
    """
    Helper any module can call when it detects an anomaly (a control
    total mismatch, a duplicate record, a suspicious variance, etc.).
    Creates an ExceptionCase for the Risk & Compliance team to triage.

    Deliberately imports apps.governance.models lazily (inside the
    function body) to avoid import-time coupling between apps -
    callers like apps.pools just need this one function, not a direct
    dependency on the governance app's models module.
    """

    from apps.governance.models import ExceptionCase

    return ExceptionCase.objects.create(
        tenant=tenant,
        source_module=source_module,
        source_object_id=source_object_id,
        pool=pool,
        severity=severity,
        title=title,
        description=description,
        detected_by=detected_by,
    )
