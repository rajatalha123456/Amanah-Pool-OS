from rest_framework import exceptions as drf_exceptions
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsPlatformSuperAdmin, IsShariahBoard
from apps.core.audit import log_action
from apps.core.exceptions import ServiceUnavailable

from .services import shariah_copilot_client as copilot
from .models import AIModelRegistry, AIModelStatus, AIRecommendation, is_ai_feature_allowed, is_ai_model_enabled
from .recording import Timer, dispose, metrics, record_ai_output


AI_MODEL_NAME = "shariah_copilot"


def _ensure_copilot_enabled():
    if not is_ai_model_enabled(AI_MODEL_NAME):
        raise ServiceUnavailable("This AI feature is currently disabled.")


class AIModelRegistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModelRegistry
        fields = (
            "id",
            "model_name",
            "version",
            "status",
            "disabled_reason",
            "disabled_by",
            "disabled_at",
            "owner",
            "purpose",
            "provenance",
            "validation_status",
            "validated_on",
            "validation_reference",
            "retirement_date",
        )
        read_only_fields = ("id", "model_name", "version", "disabled_by", "disabled_at")


class AIModelRegistryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AIModelRegistrySerializer

    def get_queryset(self):
        return AIModelRegistry.objects.all().order_by("model_name")

    def get_permissions(self):
        if self.action in ("update", "partial_update"):
            return [IsPlatformSuperAdmin()]
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        registry = self.get_object()
        previous_status = registry.status
        new_status = serializer.validated_data.get("status", previous_status)
        if new_status == AIModelStatus.DISABLED:
            registry = serializer.save(disabled_by=self.request.user, disabled_at=timezone.now())
        else:
            registry = serializer.save(disabled_by=None, disabled_at=None, disabled_reason=None)

        log_action(
            tenant=None,
            actor=self.request.user,
            action="disable" if new_status == AIModelStatus.DISABLED else "enable",
            model_name="AIModelRegistry",
            object_id=str(registry.id),
            changes={"status": {"before": previous_status, "after": registry.status}},
            reason=registry.disabled_reason,
            request=self.request,
        )


def _forward_copilot_error(exc: copilot.ShariahCopilotError):
    """
    Re-raise a ShariahCopilotError as a DRF APIException carrying its
    original status code and detail, so apps.core.exceptions.custom_exception_handler
    formats it into our standard {"error": {...}} shape.
    """

    class _ForwardedError(drf_exceptions.APIException):
        status_code = exc.status_code
        default_detail = exc.detail
        default_code = "shariah_copilot_error"

    raise _ForwardedError()


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasAnyRole(["shariah_board", "shariah_secretariat", "platform_super_admin"])])
def upload_document(request):
    _ensure_copilot_enabled()
    file = request.FILES.get("file")
    if not file:
        raise drf_exceptions.ValidationError({"file": ["This field is required."]})

    metadata = {key: value for key, value in request.data.items() if key != "file"}

    try:
        result = copilot.upload_document(request.user, request.user.tenant.code, file, metadata)
    except copilot.ShariahCopilotUnavailableError as exc:
        raise ServiceUnavailable(str(exc)) from exc
    except copilot.ShariahCopilotError as exc:
        _forward_copilot_error(exc)

    log_action(
        tenant=request.user.tenant,
        actor=request.user,
        action="create",
        model_name="ShariahCopilotDocument",
        object_id=str(result.get("id")),
        changes={"document_name": metadata.get("document_name"), "document_type": metadata.get("document_type")},
        request=request,
    )
    return Response(result, status=201)


@api_view(["GET"])
@permission_classes(
    [IsAuthenticated, HasAnyRole(["shariah_board", "shariah_secretariat", "product_manager", "risk_compliance", "platform_super_admin"])]
)
def list_documents(request):
    _ensure_copilot_enabled()
    params = request.query_params.dict()

    try:
        result = copilot.list_documents(request.user, request.user.tenant.code, params)
    except copilot.ShariahCopilotUnavailableError as exc:
        raise ServiceUnavailable(str(exc)) from exc
    except copilot.ShariahCopilotError as exc:
        _forward_copilot_error(exc)

    return Response(result)


@api_view(["POST"])
@permission_classes(
    [IsAuthenticated, HasAnyRole(["shariah_board", "shariah_secretariat", "product_manager", "risk_compliance", "platform_super_admin"])]
)
def ask(request):
    _ensure_copilot_enabled()
    question = request.data.get("question")
    if not question:
        raise drf_exceptions.ValidationError({"question": ["This field is required."]})
    filters = request.data.get("filters", {})

    timer = Timer()
    try:
        result = copilot.ask_question(request.user, request.user.tenant.code, question, filters)
    except copilot.ShariahCopilotUnavailableError as exc:
        raise ServiceUnavailable(str(exc)) from exc
    except copilot.ShariahCopilotError as exc:
        _forward_copilot_error(exc)

    payload = result if isinstance(result, dict) else {"result": result}
    sources = payload.get("citations") or payload.get("sources") or []
    recommendation_id = record_ai_output(
        user=request.user, feature="shariah_copilot_ask", model_name=AI_MODEL_NAME,
        prompt={"question": question, "filters": filters}, output=payload, sources=sources,
        confidence=payload.get("confidence"), reason="Answer drawn from the approved Shariah source library.",
        requires_review=True, latency_ms=timer.ms,
    )
    return Response({**payload, "recommendation_id": recommendation_id})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsShariahBoard])
def review(request, evidence_pack_id):
    _ensure_copilot_enabled()
    approve = request.data.get("approve")
    if approve is None:
        raise drf_exceptions.ValidationError({"approve": ["This field is required."]})

    try:
        result = copilot.submit_review(request.user, request.user.tenant.code, evidence_pack_id, approve)
    except copilot.ShariahCopilotUnavailableError as exc:
        raise ServiceUnavailable(str(exc)) from exc
    except copilot.ShariahCopilotError as exc:
        _forward_copilot_error(exc)

    log_action(
        tenant=request.user.tenant,
        actor=request.user,
        action="approve" if approve else "reject",
        model_name="ShariahCopilotEvidencePack",
        object_id=str(evidence_pack_id),
        changes={"approve": approve},
        request=request,
    )
    return Response(result)


from .services.contract_analyzer import analyze_contract_text


@api_view(["POST"])
@permission_classes([IsAuthenticated, HasAnyRole(["shariah_board", "shariah_secretariat", "product_manager", "platform_super_admin"])])
def analyze_contract(request):
    text = request.data.get("contract_text", "").strip()
    if not text:
        raise drf_exceptions.ValidationError({"contract_text": ["This field is required."]})

    if not is_ai_feature_allowed("contract_analyzer"):
        raise ServiceUnavailable("This AI feature is currently disabled.")
    timer = Timer()
    result = analyze_contract_text(text, request.user.tenant.code, str(request.user.id), request.user.role)
    recommendation_id = record_ai_output(
        user=request.user, feature="contract_analyzer", model_name="contract_analyzer", prompt=text, output=result,
        sources=[result.get("source", "")], confidence=result.get("confidence_score"),
        reason="Clause screening of the supplied contract text.",
        requires_review=bool(result.get("requires_human_review", True)),
        is_fallback=result.get("source") != "shariah_copilot_llm", latency_ms=timer.ms,
    )
    return Response({**result, "recommendation_id": recommendation_id})


from .services.audit_sampler import perform_audit_sampling_analysis


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated, HasAnyRole(["auditor", "risk_compliance", "shariah_board", "platform_super_admin"])])
def run_audit_sampling(request):
    """
    Executes the AI Audit Sampling & Risk Ranker Engine for the current tenant.
    """
    tenant = request.user.tenant
    if not tenant:
        raise drf_exceptions.PermissionDenied("User must belong to a tenant.")

    if not is_ai_feature_allowed("audit_sampler"):
        raise ServiceUnavailable("This AI feature is currently disabled.")
    timer = Timer()
    result = perform_audit_sampling_analysis(tenant)
    recommendation_id = record_ai_output(
        user=request.user, feature="audit_sampler", model_name="audit_sampler", prompt={"tenant": tenant.code},
        output=result, sources=["rule_based_engine"], reason="Risk-ranked sample for auditor review; not a finding.",
        is_fallback=True, latency_ms=timer.ms,
    )
    return Response({**result, "recommendation_id": recommendation_id})


from .services.hardship_predictor import analyze_pool_member_hardship
from apps.pools.models import Pool


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated, HasAnyRole(["risk_compliance", "pool_manager", "shariah_board", "shariah_secretariat"])])
def predict_circle_hardship(request, pool_id):
    """
    Executes the AI Member Hardship & Default Predictor for a given Circle pool.
    """
    try:
        pool = Pool.objects.get(id=pool_id)
    except Pool.DoesNotExist:
        return Response({"error": "Pool not found."}, status=404)

    if not is_ai_feature_allowed("hardship_predictor"):
        raise ServiceUnavailable("This AI feature is currently disabled.")
    timer = Timer()
    result = analyze_pool_member_hardship(pool)
    recommendation_id = record_ai_output(
        user=request.user, feature="hardship_predictor", model_name="hardship_predictor",
        prompt={"pool": str(pool.id)}, output=result, sources=["rule_based_engine"],
        reason="Early-warning indicator for supportive outreach; never grounds for penalty.",
        is_fallback=True, latency_ms=timer.ms, subject_type="Pool", subject_id=pool.id,
    )
    return Response({**result, "recommendation_id": recommendation_id})


from .services.collusion_detector import detect_fraud_and_collusion_network


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated, HasAnyRole(["risk_compliance", "auditor"])])
def detect_collusion_network(request):
    """
    Executes AI Fraud & Collusion Graph Network analysis for circles/pools.
    Accepts optional ?pool_id=<uuid> query parameter or JSON body.
    """
    tenant = request.user.tenant
    if not tenant:
        raise drf_exceptions.PermissionDenied("User must belong to a tenant.")

    pool_id = request.query_params.get("pool_id") or request.data.get("pool_id")
    if not is_ai_feature_allowed("collusion_detector"):
        raise ServiceUnavailable("This AI feature is currently disabled.")
    timer = Timer()
    result = detect_fraud_and_collusion_network(tenant=tenant, pool_id=pool_id)
    recommendation_id = record_ai_output(
        user=request.user, feature="collusion_detector", model_name="collusion_detector",
        prompt={"pool_id": str(pool_id or "")}, output=result, sources=["rule_based_engine"],
        reason="Link analysis over recorded member data; indicates, does not accuse.",
        is_fallback=True, latency_ms=timer.ms, subject_type="Pool", subject_id=pool_id or "",
    )
    return Response({**result, "recommendation_id": recommendation_id})






REVIEWER_ROLES = [
    "shariah_board", "shariah_secretariat", "risk_compliance", "pool_manager", "product_manager", "auditor",
    "platform_super_admin",
]


class AIRecommendationSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.full_name", read_only=True, default=None)
    disposed_by_name = serializers.CharField(source="disposed_by.full_name", read_only=True, default=None)

    class Meta:
        model = AIRecommendation
        fields = (
            "id", "feature", "model_name", "model_version", "requested_by", "requested_by_name", "subject_type",
            "subject_id", "prompt_hash", "prompt_text", "output", "sources", "confidence", "reason",
            "requires_human_review", "is_fallback", "latency_ms", "disposition", "disposed_by",
            "disposed_by_name", "disposed_at", "disposition_note", "created_at",
        )
        read_only_fields = fields


class AIRecommendationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AIRecommendationSerializer

    def get_permissions(self):
        if self.action == "dispose":
            # The human decision on an AI output belongs to the people who own the subject matter; the auditor
            # reads the record but stays independent of the decision (BRD section 3).
            return [IsAuthenticated(), HasAnyRole([r for r in REVIEWER_ROLES if r not in ("auditor", "platform_super_admin")])()]
        return [IsAuthenticated(), HasAnyRole(REVIEWER_ROLES)()]

    def get_queryset(self):
        queryset = AIRecommendation.objects.select_related("requested_by", "disposed_by")
        for param, field in (("feature", "feature"), ("disposition", "disposition"), ("model", "model_name")):
            value = self.request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset

    @action(detail=True, methods=["post"])
    def dispose(self, request, pk=None):
        recommendation = dispose(
            self.get_object(), request.user, str(request.data.get("disposition") or ""),
            str(request.data.get("note") or ""),
        )
        log_action(
            tenant=recommendation.tenant, actor=request.user, action=f"ai_{recommendation.disposition}",
            model_name="AIRecommendation", object_id=str(recommendation.id),
            changes={"feature": recommendation.feature}, reason=recommendation.disposition_note, request=request,
        )
        return Response(self.get_serializer(recommendation).data)

    @action(detail=False, methods=["get"])
    def metrics(self, request):
        """Model-governance metrics: volume, acceptance/override, fallback and confidence per model."""
        return Response(metrics())
