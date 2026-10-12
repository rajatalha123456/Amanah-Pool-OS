"""Circle rules, verifiable draws and closure endpoints (BRD 6.5)."""

from decimal import Decimal, InvalidOperation

from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole
from apps.core.audit import log_action
from apps.pools.models import Pool

from . import closure as closure_service
from . import rotation, rules as rules_service
from .models import CircleClosure, CircleDraw, CircleMember, CircleRules, DrawStatus

STAFF_READ = ["pool_manager", "finance_maker", "finance_checker", "risk_compliance", "auditor",
              "shariah_board", "shariah_secretariat", "platform_super_admin"]


def _pool(value):
    pool = Pool.objects.select_related("product").filter(id=value).first() if value else None
    if pool is None:
        raise ValidationError({"pool": ["A valid circle pool is required."]})
    return pool


class CircleRulesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CircleRules
        fields = ("id", "pool", "version", "contribution_amount", "cycle_days", "schedule_note",
                  "order_policy", "hardship_policy", "content_hash", "created_at")
        read_only_fields = fields


class CircleRulesViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = CircleRulesSerializer

    def get_queryset(self):
        queryset = CircleRules.objects.all()
        pool_id = self.request.query_params.get("pool")
        return queryset.filter(pool_id=pool_id) if pool_id else queryset

    def get_permissions(self):
        if self.action == "publish":
            return [IsAuthenticated(), HasAnyRole(["pool_manager"])()]
        return [IsAuthenticated(), HasAnyRole(STAFF_READ)()]

    @action(detail=False, methods=["post"])
    def publish(self, request):
        pool = _pool(request.data.get("pool"))
        try:
            amount = Decimal(str(request.data.get("contribution_amount")))
            cycle_days = int(request.data.get("cycle_days"))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("A valid contribution amount and cycle length (days) are required.")
        rules = rules_service.publish_rules(
            pool=pool, user=request.user, contribution_amount=amount, cycle_days=cycle_days,
            order_policy=str(request.data.get("order_policy") or ""),
            hardship_policy=str(request.data.get("hardship_policy") or ""),
            schedule_note=str(request.data.get("schedule_note") or ""),
        )
        log_action(
            tenant=pool.tenant, actor=request.user, action="circle_rules_published", model_name="CircleRules",
            object_id=str(rules.id), changes={"version": rules.version, "hash": rules.content_hash}, request=request,
        )
        return Response(self.get_serializer(rules).data, status=201)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Current rules plus how many active members have accepted them."""
        pool = _pool(request.query_params.get("pool"))
        data = rules_service.acceptance_summary(pool)
        rules = data.pop("rules")
        return Response({"rules": self.get_serializer(rules).data if rules else None, **data})

    @action(detail=False, methods=["post"], url_path="accept")
    def accept(self, request):
        """Record one member's acceptance of the current rules (organizer or compliance records it)."""
        if request.user.role not in ("pool_manager", "risk_compliance"):
            raise ValidationError("Only the organizer or compliance can record an acceptance.")
        member = CircleMember.objects.select_related("pool__product").filter(id=request.data.get("member")).first()
        if member is None:
            raise ValidationError({"member": ["A valid member is required."]})
        acceptance = rules_service.record_acceptance(
            member=member, user=request.user, method=str(request.data.get("method") or ""),
            evidence_reference=str(request.data.get("evidence_reference") or ""),
        )
        log_action(
            tenant=member.tenant, actor=request.user, action="circle_rules_accepted", model_name="RulesAcceptance",
            object_id=str(acceptance.id),
            changes={"member": member.member_reference, "rules_version": acceptance.rules.version,
                     "method": acceptance.method}, request=request,
        )
        return Response({"member": member.member_reference, "rules_version": acceptance.rules.version}, status=201)


class CircleDrawSerializer(serializers.ModelSerializer):
    server_seed = serializers.SerializerMethodField()

    class Meta:
        model = CircleDraw
        fields = ("id", "pool", "sequence", "commitment", "server_seed", "client_seed", "status",
                  "participants", "assignments", "result_hash", "executed_at", "created_at")
        read_only_fields = fields

    def get_server_seed(self, draw):
        # The secret stays hidden until the draw has been executed.
        return draw.server_seed if draw.status == DrawStatus.EXECUTED else None


class CircleDrawViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = CircleDrawSerializer

    def get_queryset(self):
        queryset = CircleDraw.objects.select_related("pool")
        pool_id = self.request.query_params.get("pool")
        return queryset.filter(pool_id=pool_id) if pool_id else queryset

    def get_permissions(self):
        if self.action in ("commit", "execute"):
            return [IsAuthenticated(), HasAnyRole(["pool_manager"])()]
        return [IsAuthenticated(), HasAnyRole(STAFF_READ)()]

    @action(detail=False, methods=["post"])
    def commit(self, request):
        pool = _pool(request.data.get("pool"))
        draw = rotation.commit_draw(pool, request.user)
        log_action(
            tenant=pool.tenant, actor=request.user, action="circle_draw_committed", model_name="CircleDraw",
            object_id=str(draw.id), changes={"commitment": draw.commitment, "participants": draw.participants},
            request=request,
        )
        return Response(self.get_serializer(draw).data, status=201)

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        draw = rotation.execute_draw(self.get_object(), request.data.get("client_seed"), request.user)
        log_action(
            tenant=draw.tenant, actor=request.user, action="circle_draw_executed", model_name="CircleDraw",
            object_id=str(draw.id), changes={"result_hash": draw.result_hash, "assignments": draw.assignments},
            request=request,
        )
        return Response(self.get_serializer(draw).data)

    @action(detail=True, methods=["get"])
    def verify(self, request, pk=None):
        return Response(rotation.verify_draw(self.get_object()))


class CircleClosureSerializer(serializers.ModelSerializer):
    class Meta:
        model = CircleClosure
        fields = ("id", "pool", "status", "total_collected", "total_disbursed", "difference", "snapshot",
                  "resolution_note", "prepared_by", "closed_by", "closed_at", "created_at")
        read_only_fields = fields


class CircleClosureViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = CircleClosureSerializer

    def get_queryset(self):
        return CircleClosure.objects.all()

    def get_permissions(self):
        if self.action == "prepare":
            return [IsAuthenticated(), HasAnyRole(["pool_manager", "finance_maker"])()]
        if self.action == "close":
            return [IsAuthenticated(), HasAnyRole(["finance_checker"])()]
        return [IsAuthenticated(), HasAnyRole(STAFF_READ)()]

    @action(detail=False, methods=["get"])
    def preview(self, request):
        result = closure_service.reconcile(_pool(request.query_params.get("pool")))
        return Response({k: (str(v) if isinstance(v, Decimal) else v) for k, v in result.items()})

    @action(detail=False, methods=["post"])
    def prepare(self, request):
        pool = _pool(request.data.get("pool"))
        closure = closure_service.prepare_closure(pool, request.user, str(request.data.get("resolution_note") or ""))
        log_action(
            tenant=pool.tenant, actor=request.user, action="circle_closure_prepared", model_name="CircleClosure",
            object_id=str(closure.id), changes={"difference": str(closure.difference)},
            reason=closure.resolution_note, request=request,
        )
        return Response(self.get_serializer(closure).data, status=201)

    @action(detail=False, methods=["post"])
    def close(self, request):
        pool = _pool(request.data.get("pool"))
        closure = closure_service.close_circle(pool, request.user)
        log_action(
            tenant=pool.tenant, actor=request.user, action="circle_closed", model_name="CircleClosure",
            object_id=str(closure.id), changes={"difference": str(closure.difference)}, request=request,
        )
        return Response(self.get_serializer(closure).data)
