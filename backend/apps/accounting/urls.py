from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    IncomeExpenseEventViewSet,
    JournalBatchViewSet,
    ReconciliationBatchViewSet,
    gl_export,
)

router = DefaultRouter()
router.register("journal-batches", JournalBatchViewSet, basename="journal-batch")
router.register("income-expense-events", IncomeExpenseEventViewSet, basename="income-expense-event")
router.register("reconciliation-batches", ReconciliationBatchViewSet, basename="reconciliation-batch")
router.register("reconciliations", ReconciliationBatchViewSet, basename="reconciliation")

urlpatterns = [
    path("journal-batches/gl-export/", gl_export, name="journal-batch-gl-export"),
] + router.urls
