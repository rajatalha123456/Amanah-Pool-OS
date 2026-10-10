import csv

from django.core.exceptions import ValidationError as DjangoValidationError

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

        qs = AuditLog.objects.filter(tenant=request.tenant)  # whole chain: continuity can only be checked unfiltered
        result = MerkleAuditEngine.verify_merkle_chain(qs)
        return Response(result)

    @action(detail=False, methods=["post"], url_path="simulate-tamper")
    def simulate_tamper(self, request):
        """
        Screen 38: SBP Regulatory Tamper-Evident Simulation.
        Proves mathematical breakdown upon unauthorized database manipulation.
        """
        from .merkle_engine import MerkleAuditEngine

        qs = AuditLog.objects.filter(tenant=request.tenant)
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


EVIDENCE_ROLES = ["auditor", "pool_manager", "finance_checker", "risk_compliance", "shariah_board"]


def _compile_bundle_for(request, params):
    """Shared by the JSON and ZIP endpoints. The pool must belong to the caller's tenant."""
    from django.utils import timezone

    from rest_framework.exceptions import ValidationError

    from .evidence_bundle_engine import EvidenceBundleEngine

    pool_id = params.get("pool_id")
    if not pool_id:
        raise ValidationError({"pool_id": ["This field is required."]})
    try:
        bundle = EvidenceBundleEngine.compile_bundle(
            pool_id=pool_id,
            period_date=params.get("period_date") or timezone.localdate().isoformat(),
            audit_type=params.get("audit_type") or "Regulatory inspection",
            user=request.user,
            tenant=request.tenant,
        )
    except (ValueError, DjangoValidationError) as exc:
        raise ValidationError(str(getattr(exc, "message", None) or exc)) from exc
    return EvidenceBundleEngine, bundle


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasAnyRole(EVIDENCE_ROLES)])
def compile_evidence_bundle(request):
    """
    BRD AI & Assurance Screen 7 / 39: Evidence Bundle Builder.
    Seals recorded evidence (decision, period close, signed run, journals, payout batch,
    risk, reconciliation, audit chain) for one of the caller's pools; missing evidence is
    reported as unavailable, never invented.
    """
    _, bundle = _compile_bundle_for(request, request.data)
    log_action(
        tenant=request.tenant, actor=request.user, action="compile_evidence_bundle", model_name="EvidenceBundle",
        object_id=bundle["bundle_id"], changes={"master_bundle_seal": bundle["master_bundle_seal"],
                                                "all_verified": bundle["all_verified"]},
        request=request,
    )
    return Response(bundle)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, HasAnyRole(EVIDENCE_ROLES)])
def download_evidence_bundle_zip(request):
    """Downloads the evidence bundle as a ZIP archive."""
    params = request.query_params if request.method == "GET" else request.data
    engine, bundle = _compile_bundle_for(request, params)
    zip_bytes = engine.generate_zip_archive(bundle, tenant=request.tenant)

    response = HttpResponse(zip_bytes, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{bundle["bundle_id"]}.zip"'
    return response
