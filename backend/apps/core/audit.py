from .models import AuditLog


def _client_ip_from(request):
    if request is None:
        return None

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


def log_action(tenant, actor, action, model_name, object_id, changes=None, reason=None, request=None):
    """
    Creates an AuditLog entry. Intended to be called from business
    modules (BE-007+) whenever an action worth auditing happens, e.g.:

        log_action(
            tenant=pool.tenant,
            actor=request.user,
            action="approve",
            model_name="AllocationRun",
            object_id=str(allocation_run.id),
            changes={"status": {"before": "pending", "after": "approved"}},
            reason="Variance within tolerance",
            request=request,
        )
    """

    return AuditLog.objects.create(
        tenant=tenant,
        actor=actor,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        changes=changes,
        reason=reason,
        ip_address=_client_ip_from(request),
    )
