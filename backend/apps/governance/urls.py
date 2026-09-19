from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ExceptionCaseViewSet,
    PurificationEntryViewSet,
    RelatedPartyTransactionViewSet,
    shariah_dashboard,
)

router = DefaultRouter()
router.register("exceptions", ExceptionCaseViewSet, basename="exception-case")
router.register("purification-entries", PurificationEntryViewSet, basename="purification-entry")
router.register("related-party-transactions", RelatedPartyTransactionViewSet, basename="related-party-transaction")

urlpatterns = [
    path("shariah-dashboard/", shariah_dashboard, name="shariah-dashboard"),
] + router.urls
