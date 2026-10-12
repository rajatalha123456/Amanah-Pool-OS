from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ConfigChangeRequestViewSet,
    ExceptionCaseViewSet,
    PurificationEntryViewSet,
    RelatedPartyTransactionViewSet,
    RetentionPolicyViewSet,
    ShariahAuditFindingViewSet,
    ShariahAuditPlanViewSet,
    SupportRequestViewSet,
    shariah_dashboard,
)

router = DefaultRouter()
router.register("retention-policies", RetentionPolicyViewSet, basename="retention-policy")
router.register("config-changes", ConfigChangeRequestViewSet, basename="config-change")
router.register("exceptions", ExceptionCaseViewSet, basename="exception-case")
router.register("purification-entries", PurificationEntryViewSet, basename="purification-entry")
router.register("related-party-transactions", RelatedPartyTransactionViewSet, basename="related-party-transaction")
router.register("support-requests", SupportRequestViewSet, basename="support-request")
router.register("shariah-audit-plans", ShariahAuditPlanViewSet, basename="shariah-audit-plan")
router.register("shariah-audit-findings", ShariahAuditFindingViewSet, basename="shariah-audit-finding")

urlpatterns = [
    path("shariah-dashboard/", shariah_dashboard, name="shariah-dashboard"),
] + router.urls
