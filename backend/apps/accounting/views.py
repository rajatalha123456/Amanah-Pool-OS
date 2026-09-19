from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, IsFinanceChecker, IsFinanceMaker
from apps.core.audit import log_action
from apps.pools.models import Pool

from .exports import generate_gl_csv
from .models import IncomeExpenseEvent, IncomeExpenseEventStatus, JournalBatch
from .serializers import IncomeExpenseEventSerializer, JournalBatchSerializer


class JournalBatchViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = JournalBatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # See apps/products/views.py etc. for why this must be a method
        # rather than a class-level `queryset = Model.objects.all()`
        # attribute (TenantScopedManager + import-time evaluation bug).
        queryset = JournalBatch.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset


class IncomeExpenseEventViewSet(viewsets.ModelViewSet):
    serializer_class = IncomeExpenseEventSerializer

    def get_queryset(self):
        # See apps/products/views.py etc. for why this must be a method
        # rather than a class-level `queryset = Model.objects.all()`
        # attribute (TenantScopedManager + import-time evaluation bug).
        queryset = IncomeExpenseEvent.objects.all()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            queryset = queryset.filter(pool_id=pool_id)
        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsFinanceMaker()]
        if self.action == "post_event":
            return [IsAuthenticated(), IsFinanceChecker()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save(tenant=self.request.user.tenant, created_by=self.request.user)
        log_action(
            tenant=instance.tenant,
            actor=self.request.user,
            action="create",
            model_name="IncomeExpenseEvent",
            object_id=str(instance.id),
            changes={
                "event_type": instance.event_type,
                "category": instance.category,
                "amount": str(instance.amount),
                "pool": str(instance.pool_id),
            },
            request=self.request,
        )

    @action(detail=True, methods=["post"], url_path="post")
    def post_event(self, request, pk=None):
        event = self.get_object()

        if event.status != IncomeExpenseEventStatus.PENDING:
            raise ValidationError(
                f"IncomeExpenseEvent must be in '{IncomeExpenseEventStatus.PENDING}' status to "
                f"post (current status: '{event.status}')."
            )

        previous_status = event.status
        event.status = IncomeExpenseEventStatus.POSTED
        event.posted_by = request.user
        event.posted_at = timezone.now()
        event.save(update_fields=["status", "posted_by", "posted_at", "updated_at"])

        log_action(
            tenant=event.tenant,
            actor=request.user,
            action="post",
            model_name="IncomeExpenseEvent",
            object_id=str(event.id),
            changes={"status": {"before": previous_status, "after": event.status}},
            request=request,
        )
        return Response(self.get_serializer(event).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, HasAnyRole(["finance_maker", "finance_checker"])])
def gl_export(request):
    pool_id = request.query_params.get("pool")
    pool = get_object_or_404(Pool, id=pool_id)

    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    csv_content = generate_gl_csv(pool, date_from=date_from, date_to=date_to)
    row_count = max(csv_content.count("\n") - 1, 0)

    log_action(
        tenant=pool.tenant,
        actor=request.user,
        action="gl_export",
        model_name="Pool",
        object_id=str(pool.id),
        changes={"pool": pool.code, "row_count": row_count, "date_from": date_from, "date_to": date_to},
        request=request,
    )

    filename = f"gl_export_{pool.code}_{date_from or 'all'}_{date_to or 'all'}.csv"
    response = HttpResponse(csv_content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
