import csv

from django.http import HttpResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated

from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsAuditor

from .models import AuditLog
from .serializers import AuditLogSerializer
from .audit import log_action


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

    @action(detail=False, methods=["get", "post"], url_path="verify-merkle")
    def verify_merkle(self, request):
        """
        Screen 38: Cryptographic Merkle Tree Hash Chain Verification.
        Recalculates rolling SHA-256 chain from Genesis to tip.
        """
        from .merkle_engine import MerkleAuditEngine

        qs = self.get_queryset()
        result = MerkleAuditEngine.verify_merkle_chain(qs)
        return Response(result)

    @action(detail=False, methods=["post"], url_path="simulate-tamper")
    def simulate_tamper(self, request):
        """
        Screen 38: SBP Regulatory Tamper-Evident Simulation.
        Proves mathematical breakdown upon unauthorized database manipulation.
        """
        from .merkle_engine import MerkleAuditEngine

        qs = self.get_queryset()
        target_height = request.data.get("target_height")
        if target_height is not None:
            try:
                target_height = int(target_height)
            except (ValueError, TypeError):
                target_height = None

        result = MerkleAuditEngine.simulate_tamper_detection(qs, target_height=target_height)
        return Response(result)



@api_view(["GET"])
@permission_classes([IsAuthenticated, HasAnyRole(["auditor", "platform_super_admin"])])
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


from .banking_switch import execute_banking_settlement


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasAnyRole(["finance_checker"])])
def process_banking_settlement(request):
    """
    Executes a simulated real-time settlement across SBP Raast / 1LINK rails.
    """
    data = request.data
    amount = data.get("amount")
    if not amount:
        return Response({"error": "amount is required."}, status=400)

    source_title = data.get("source_title", "Account Holder")
    source_iban = data.get("source_iban", "PK12MEZN0001928172601")
    destination_title = data.get("destination_title")
    destination_iban = data.get("destination_iban")
    channel = data.get("channel", "RAAST_P2M")
    purpose = data.get("purpose", "Pool Settlement")
    simulate_failure = data.get("simulate_failure_code")

    try:
        settlement_result = execute_banking_settlement(
            amount=amount,
            source_title=source_title,
            source_iban=source_iban,
            destination_title=destination_title,
            destination_iban=destination_iban,
            channel=channel,
            purpose=purpose,
            simulate_failure_code=simulate_failure,
        )
    except ValueError as e:
        return Response({"error": str(e)}, status=400)

    log_action(
        tenant=request.user.tenant,
        actor=request.user,
        action="banking_settlement",
        model_name="BankingSettlement",
        object_id=settlement_result.get("rrn", ""),
        changes={
            "rrn": settlement_result.get("rrn"),
            "stan": settlement_result.get("stan"),
            "e2e_id": settlement_result.get("e2e_id"),
            "channel": channel,
            "amount": str(amount),
            "response_code": settlement_result.get("response_code"),
        },
        request=request,
    )

    return Response(settlement_result)


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasAnyRole(["auditor", "platform_super_admin", "pool_manager", "finance_checker", "shariah_board"])])
def compile_evidence_bundle(request):
    """
    BRD AI & Assurance Screen 7 / Screen 39: Evidence Bundle Builder.
    Assembles cryptographic, Shariah, GL, and clearing attestations into a unified SBP dossier.
    """
    from .evidence_bundle_engine import EvidenceBundleEngine
    from apps.pools.models import Pool

    pool_id = request.data.get("pool_id")
    period_date = request.data.get("period_date", "2026-09-30")
    audit_type = request.data.get("audit_type", "SBP Comprehensive Inspection")

    if not pool_id:
        pool = Pool._base_manager.first()
        pool_id = str(pool.id) if pool else None

    if not pool_id:
        return Response({"error": "No pool found for evidence compilation."}, status=400)

    bundle = EvidenceBundleEngine.compile_bundle(
        pool_id=pool_id,
        period_date=period_date,
        audit_type=audit_type,
        user=request.user,
        tenant=request.user.tenant,
    )
    return Response(bundle)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, HasAnyRole(["auditor", "platform_super_admin", "pool_manager", "finance_checker", "shariah_board"])])
def download_evidence_bundle_zip(request):
    """
    Downloads the unified SBP Regulatory Evidence Bundle ZIP archive.
    """
    from .evidence_bundle_engine import EvidenceBundleEngine
    from apps.pools.models import Pool

    pool_id = request.query_params.get("pool_id") or request.data.get("pool_id")
    period_date = request.query_params.get("period_date") or request.data.get("period_date", "2026-09-30")
    audit_type = request.query_params.get("audit_type") or request.data.get("audit_type", "SBP Inspection")

    if not pool_id:
        pool = Pool._base_manager.first()
        pool_id = str(pool.id) if pool else None

    bundle = EvidenceBundleEngine.compile_bundle(
        pool_id=pool_id,
        period_date=period_date,
        audit_type=audit_type,
        user=request.user,
        tenant=request.user.tenant,
    )
    zip_bytes = EvidenceBundleEngine.generate_zip_archive(bundle)

    response = HttpResponse(zip_bytes, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{bundle["bundle_id"]}.zip"'
    return response


