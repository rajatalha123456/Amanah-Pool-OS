from rest_framework.routers import DefaultRouter

from .views import ContractTemplateViewSet, ProductViewSet, ShariahDecisionViewSet

router = DefaultRouter()
router.register("shariah-decisions", ShariahDecisionViewSet, basename="shariah-decision")
router.register("contract-templates", ContractTemplateViewSet, basename="contract-template")
router.register("products", ProductViewSet, basename="product")

urlpatterns = router.urls
