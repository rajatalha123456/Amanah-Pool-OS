"""
Maker-checker for governance configuration (BRD 6.1: Risk validates limits, Finance validates mappings).

The approval matrix and the account mapping decide who may release money and where it is posted, so a
change to either is never applied by the person who proposes it. The endpoints that used to write directly
now create a `ConfigChangeRequest`; a different, authorised user approves it, and only then is the change
applied (after re-validating it against the current data). Pending changes are visible to everyone with
read access, and every step is audited.
"""

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.audit import log_action

from .models import ConfigChangeKind, ConfigChangeOperation, ConfigChangeRequest, ConfigChangeStatus

# kind -> who may approve (the proposing roles are enforced by each configuration endpoint)
APPROVER_ROLES = {
    ConfigChangeKind.APPROVAL_MATRIX: ["finance_checker", "platform_super_admin"],
    ConfigChangeKind.ACCOUNT_MAPPING: ["finance_checker", "platform_super_admin"],
}


def _binding(kind):
    """(model, serializer class) of the configuration object behind a change kind."""
    if kind == ConfigChangeKind.APPROVAL_MATRIX:
        from apps.accounts.models import ApprovalMatrixRule
        from apps.accounts.serializers import ApprovalMatrixRuleSerializer

        return ApprovalMatrixRule, ApprovalMatrixRuleSerializer
    from apps.accounting.models import AccountMapping
    from apps.accounting.serializers import AccountMappingSerializer

    return AccountMapping, AccountMappingSerializer


def _writable(serializer):
    return [name for name, field in serializer.fields.items() if not field.read_only]


def _plain(value):
    return None if value is None else str(value)


def submit_change(*, kind, serializer, request, instance=None):
    """Called by a configuration endpoint after its serializer validated the proposal."""
    reason = str(request.data.get("change_reason") or "").strip()
    if not reason:
        raise ValidationError({"change_reason": ["Explain why this change is needed."]})

    fields = _writable(serializer)
    payload = {name: _plain(request.data[name]) for name in fields if name in request.data}
    if instance is None:
        operation, target_id, before = ConfigChangeOperation.CREATE, "", {}
    else:
        operation, target_id = ConfigChangeOperation.UPDATE, str(instance.pk)
        before = {name: _plain(getattr(instance, name if name != "pool" else "pool_id", None)) for name in payload}
        if ConfigChangeRequest.objects.filter(
            kind=kind, target_id=target_id, status=ConfigChangeStatus.PENDING
        ).exists():
            raise ValidationError("A change to this item is already awaiting approval.")

    change = ConfigChangeRequest.objects.create(
        tenant=request.user.tenant, kind=kind, operation=operation, target_id=target_id, payload=payload,
        before=before, reason=reason, requested_by=request.user,
    )
    log_action(
        tenant=change.tenant, actor=request.user, action="config_change_requested", model_name="ConfigChangeRequest",
        object_id=str(change.id), changes={"kind": kind, "operation": operation, "payload": payload},
        reason=reason, request=request,
    )
    try:
        from apps.notifications import events

        events.config_change_submitted(change, request.user)
    except Exception:  # noqa: BLE001 - notification failure never blocks the business action
        pass
    return change


def approve_change(change, user, request):
    if change.status != ConfigChangeStatus.PENDING:
        raise ValidationError(f"This change is already {change.status}.")
    if user.role not in APPROVER_ROLES[change.kind]:
        raise PermissionDenied("Your role cannot approve this kind of change.")
    if change.requested_by_id == user.id:
        raise ValidationError("Four-eyes rule: the person who proposed a change cannot approve it.")

    model, serializer_class = _binding(change.kind)
    context = {"request": request}
    if change.operation == ConfigChangeOperation.CREATE:
        serializer = serializer_class(data=change.payload, context=context)
    else:
        instance = model.objects.filter(pk=change.target_id).first()
        if instance is None:
            raise ValidationError("The item this change targets no longer exists.")
        for name, old in change.before.items():
            current = _plain(getattr(instance, name if name != "pool" else "pool_id", None))
            if current != old:
                raise ValidationError(f"'{name}' changed since this proposal was made; propose it again.")
        serializer = serializer_class(instance, data=change.payload, partial=True, context=context)
    serializer.is_valid(raise_exception=True)
    saved = serializer.save(tenant=user.tenant) if change.operation == ConfigChangeOperation.CREATE else serializer.save()

    change.status = ConfigChangeStatus.APPROVED
    change.decided_by = user
    change.decided_at = timezone.now()
    change.applied_id = str(saved.pk)
    change.save()
    log_action(
        tenant=change.tenant, actor=user, action="config_change_approved", model_name=model.__name__,
        object_id=str(saved.pk), changes={"before": change.before, "after": change.payload},
        reason=change.reason, request=request,
    )
    return change


def reject_change(change, user, reason, request):
    if change.status != ConfigChangeStatus.PENDING:
        raise ValidationError(f"This change is already {change.status}.")
    if user.role not in APPROVER_ROLES[change.kind]:
        raise PermissionDenied("Your role cannot decide this kind of change.")
    if not reason.strip():
        raise ValidationError({"reason": ["A rejection reason is required."]})
    change.status = ConfigChangeStatus.REJECTED
    change.decided_by = user
    change.decided_at = timezone.now()
    change.decision_note = reason
    change.save()
    log_action(
        tenant=change.tenant, actor=user, action="config_change_rejected", model_name="ConfigChangeRequest",
        object_id=str(change.id), reason=reason, request=request,
    )
    return change
