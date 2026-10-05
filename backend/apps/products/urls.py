from rest_framework.routers import DefaultRouter

from .views import (
    ContractTemplateViewSet,
    JurisdictionRulePackViewSet,
    ProductViewSet,
    ShariahDecisionViewSet,
)

router = DefaultRouter()
router.register("shariah-decisions", ShariahDecisionViewSet, basename="shariah-decision")
router.register("contract-templates", ContractTemplateViewSet, basename="contract-template")
router.register("products", ProductViewSet, basename="product")
router.register("jurisdiction-rule-packs", JurisdictionRulePackViewSet, basename="jurisdiction-rule-pack")

urlpatterns = router.urls
