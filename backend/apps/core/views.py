import csv

from django.http import HttpResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsAuditor

from .models import AuditLog
from .serializers import AuditLogSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok"})


def _filtered_audit_log_queryset(request):
    # AuditLog is deliberately not a TenantScopedModel (see its
    # docstring), so there's no TenantScopedManager auto-filtering -
    # every non-super-admin caller must be scoped to their own tenant
    # explicitly here, same as UserManagementViewSet.get_queryset().
    queryset = AuditLog.objects.all()
    user = request.user
    if user.role == "platform_super_admin":
        tenant_id = request.query_params.get("tenant")
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
    else:
        queryset = queryset.filter(tenant=user.tenant)

    model_name = request.query_params.get("model_name")
    if model_name:
        queryset = queryset.filter(model_name=model_name)

    date_from = request.query_params.get("date_from")
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)

    date_to = request.query_params.get("date_to")
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    return queryset


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Read-only. AuditLog rows are only ever created via
    apps.core.audit.log_action() from normal business actions -
    deliberately never logged here, to avoid a recursive/noisy trail of
    the audit log auditing itself.
    """

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, HasAnyRole(["auditor", "platform_super_admin"])]

    def get_queryset(self):
        return _filtered_audit_log_queryset(self.request)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAuditor])
def audit_log_export(request):
    queryset = _filtered_audit_log_queryset(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="audit_log_export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        ["id", "created_at", "tenant", "actor_email", "action", "model_name", "object_id", "changes", "reason", "ip_address"]
    )
    for entry in queryset.select_related("actor", "tenant"):
        writer.writerow(
            [
                str(entry.id),
                entry.created_at.isoformat(),
                entry.tenant.code if entry.tenant else "",
                entry.actor.email if entry.actor else "",
                entry.action,
                entry.model_name,
                entry.object_id,
                entry.changes,
                entry.reason or "",
                entry.ip_address or "",
            ]
        )

    return response
