from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole
from apps.core.audit import log_action
from apps.notifications import events

from .models import NegligenceCase, NegligenceCaseStatus

# The auditor reads cases but does not open or work them: it stays independent of operational decisions.
RAISE_ROLES = ["risk_compliance", "pool_manager", "shariah_board"]
NOTE_ROLES = RAISE_ROLES + ["shariah_secretariat"]
READ_ROLES = NOTE_ROLES + ["finance_maker", "finance_checker", "auditor"]


class NegligenceCaseSerializer(serializers.ModelSerializer):
    raised_by_name = serializers.CharField(source="raised_by.full_name", read_only=True, default=None)
    determined_by_name = serializers.CharField(source="determined_by.full_name", read_only=True, default=None)
    pool_code = serializers.CharField(source="pool.code", read_only=True)

    class Meta:
        model = NegligenceCase
        fields = (
            "id", "pool", "pool_code", "title", "allegation", "period_start", "period_end", "status",
            "raised_by", "raised_by_name", "notes", "determination_note", "liability_amount",
            "determined_by", "determined_by_name", "determined_at", "applied_run", "created_at",
        )
        read_only_fields = (
            "id", "status", "raised_by", "notes", "determination_note", "liability_amount",
            "determined_by", "determined_at", "applied_run", "created_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.pools.models import Pool

        self.fields["pool"] = serializers.PrimaryKeyRelatedField(queryset=Pool.objects.all())

    def validate(self, attrs):
        if attrs["period_start"] > attrs["period_end"]:
            raise serializers.ValidationError({"period_start": "period_start cannot be after period_end."})
        pool = attrs["pool"]
        if pool.product.operating_model != "investment_pool":
            raise serializers.ValidationError({"pool": "Negligence cases apply to investment pools."})
        return attrs


class NegligenceCaseViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    serializer_class = NegligenceCaseSerializer

    def get_queryset(self):
        queryset = NegligenceCase.objects.select_related("pool", "raised_by", "determined_by")
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), HasAnyRole(RAISE_ROLES)()]
        if self.action == "add_note":
            return [IsAuthenticated(), HasAnyRole(NOTE_ROLES)()]
        if self.action == "determine":
            # Only the Shariah Board can find the manager liable or clear them.
            return [IsAuthenticated(), HasAnyRole(["shariah_board"])()]
        return [IsAuthenticated(), HasAnyRole(READ_ROLES)()]

    def perform_create(self, serializer):
        case = serializer.save(tenant=self.request.user.tenant, raised_by=self.request.user)
        log_action(
            tenant=case.tenant, actor=self.request.user, action="negligence_case_opened",
            model_name="NegligenceCase", object_id=str(case.id),
            changes={"pool": str(case.pool_id), "period": f"{case.period_start}..{case.period_end}"},
            reason=case.allegation, request=self.request,
        )
        events.negligence_opened(case, self.request.user)

    @action(detail=True, methods=["post"], url_path="add-note")
    def add_note(self, request, pk=None):
        case = self.get_object()
        if case.status != NegligenceCaseStatus.OPEN:
            raise ValidationError("A determined case is closed to further investigation notes.")
        note = (request.data.get("note") or "").strip()
        if not note:
            raise ValidationError({"note": ["This field is required."]})
        case.notes = [*case.notes, {"at": timezone.now().isoformat(), "by": request.user.full_name, "note": note}]
        case.save(update_fields=["notes", "updated_at"])
        log_action(
            tenant=case.tenant, actor=request.user, action="negligence_note_added", model_name="NegligenceCase",
            object_id=str(case.id), reason=note, request=request,
        )
        return Response(self.get_serializer(case).data)

    @action(detail=True, methods=["post"])
    def determine(self, request, pk=None):
        case = self.get_object()
        if case.status != NegligenceCaseStatus.OPEN:
            raise ValidationError(f"This case is already determined ({case.status}).")

        outcome = request.data.get("outcome")
        if outcome not in (NegligenceCaseStatus.LIABLE, NegligenceCaseStatus.CLEARED):
            raise ValidationError({"outcome": ["Must be 'liable' or 'cleared'."]})
        note = (request.data.get("determination_note") or "").strip()
        if not note:
            raise ValidationError({"determination_note": ["The reasoning for the determination is required."]})

        amount = None
        if outcome == NegligenceCaseStatus.LIABLE:
            try:
                amount = serializers.DecimalField(max_digits=18, decimal_places=2).to_internal_value(
                    request.data.get("liability_amount")
                )
            except serializers.ValidationError:
                raise ValidationError({"liability_amount": ["A valid liability amount is required."]})
            if amount <= 0:
                raise ValidationError({"liability_amount": ["The liability amount must be positive."]})

        case.status = outcome
        case.determination_note = note
        case.liability_amount = amount
        case.determined_by = request.user
        case.determined_at = timezone.now()
        case.save()
        log_action(
            tenant=case.tenant, actor=request.user, action=f"negligence_{outcome}", model_name="NegligenceCase",
            object_id=str(case.id), changes={"liability_amount": str(amount) if amount is not None else None},
            reason=note, request=request,
        )
        events.negligence_determined(case, request.user)
        return Response(self.get_serializer(case).data)
