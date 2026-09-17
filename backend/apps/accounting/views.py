from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasAnyRole
from apps.core.audit import log_action
from apps.pools.models import Pool

from .exports import generate_gl_csv
from .models import JournalBatch
from .serializers import JournalBatchSerializer


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
