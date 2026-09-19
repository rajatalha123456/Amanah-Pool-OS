from rest_framework import exceptions as drf_exceptions
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsPlatformSuperAdmin, IsShariahBoard
from apps.core.audit import log_action
from apps.core.exceptions import ServiceUnavailable

from .services import shariah_copilot_client as copilot
from .models import AIModelRegistry, AIModelStatus, is_ai_model_enabled


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
@permission_classes([IsAuthenticated, HasAnyRole(["shariah_board", "shariah_secretariat"])])
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
    [IsAuthenticated, HasAnyRole(["shariah_board", "shariah_secretariat", "product_manager", "risk_compliance"])]
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
    [IsAuthenticated, HasAnyRole(["shariah_board", "shariah_secretariat", "product_manager", "risk_compliance"])]
)
def ask(request):
    _ensure_copilot_enabled()
    question = request.data.get("question")
    if not question:
        raise drf_exceptions.ValidationError({"question": ["This field is required."]})
    filters = request.data.get("filters", {})

    try:
        result = copilot.ask_question(request.user, request.user.tenant.code, question, filters)
    except copilot.ShariahCopilotUnavailableError as exc:
        raise ServiceUnavailable(str(exc)) from exc
    except copilot.ShariahCopilotError as exc:
        _forward_copilot_error(exc)

    return Response(result)


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
