from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import ApprovalMatrixViewSet

from .views import (
    AccountMappingViewSet,
    IncomeExpenseEventViewSet,
    JournalBatchViewSet,
    ReconciliationBatchViewSet,
    gl_export,
)

router = DefaultRouter()
router.register("journal-batches", JournalBatchViewSet, basename="journal-batch")
router.register("account-mappings", AccountMappingViewSet, basename="account-mapping")
# Tenant-scoped control config: must live outside the tenant-exempt /auth/ prefix.
router.register("approval-matrix", ApprovalMatrixViewSet, basename="approval-matrix")
router.register("income-expense-events", IncomeExpenseEventViewSet, basename="income-expense-event")
router.register("reconciliation-batches", ReconciliationBatchViewSet, basename="reconciliation-batch")
router.register("reconciliations", ReconciliationBatchViewSet, basename="reconciliation")

urlpatterns = [
    path("journal-batches/gl-export/", gl_export, name="journal-batch-gl-export"),
] + router.urls
