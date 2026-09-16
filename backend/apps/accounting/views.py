from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

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
