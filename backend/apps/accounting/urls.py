from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import IncomeExpenseEventViewSet, JournalBatchViewSet, gl_export

router = DefaultRouter()
router.register("journal-batches", JournalBatchViewSet, basename="journal-batch")
router.register("income-expense-events", IncomeExpenseEventViewSet, basename="income-expense-event")

urlpatterns = [
    path("journal-batches/gl-export/", gl_export, name="journal-batch-gl-export"),
] + router.urls
