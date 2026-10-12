"""Shared guards for configuration viewsets: no hard delete, and edits only while a record is still a draft."""

from rest_framework.exceptions import ValidationError

from .audit import log_action

NO_DELETE = ["get", "post", "put", "patch", "head", "options"]
READ_AND_POST = ["get", "post", "head", "options"]

# Roles that may read tenant business data. The Platform Super Admin is deliberately absent: BRD section 3 says it
# "cannot view tenant financial data by default" (it provisions tenants, users and configuration only).
STAFF_ROLES = [
    "product_manager", "pool_manager", "finance_maker", "finance_checker",
    "shariah_secretariat", "shariah_board", "risk_compliance", "authorized_signatory", "auditor",
]


class EditableWhileDraftMixin:
    """
    Approved / governed records are immutable: changing them goes through a new version or a new draft that
    is approved again (BR-001/BR-002/BR-003). Only records whose status is in `editable_statuses` may be
    updated, and every update is audited with the fields that changed.
    """

    editable_statuses = ("draft",)
    status_field = "status"

    def perform_update(self, serializer):
        instance = serializer.instance
        current = getattr(instance, self.status_field)
        if current not in self.editable_statuses:
            raise ValidationError(
                f"A record in status '{current}' cannot be edited; create a new draft or version instead."
            )
        before = {field: str(getattr(instance, field, "")) for field in serializer.validated_data}
        saved = serializer.save()
        log_action(
            tenant=getattr(saved, "tenant", None),
            actor=self.request.user,
            action="update",
            model_name=saved.__class__.__name__,
            object_id=str(saved.pk),
            changes={field: {"before": before[field], "after": str(getattr(saved, field, ""))} for field in before},
            request=self.request,
        )
