from rest_framework.routers import DefaultRouter

from .views import (
    AssetAssignmentViewSet,
    AssetViewSet,
    BalanceImportViewSet,
    DailyBalanceViewSet,
    PoolViewSet,
)

router = DefaultRouter()
router.register("pools", PoolViewSet, basename="pool")
router.register("assets", AssetViewSet, basename="asset")
router.register("asset-assignments", AssetAssignmentViewSet, basename="asset-assignment")
router.register("daily-balances", DailyBalanceViewSet, basename="daily-balance")
router.register("balance-imports", BalanceImportViewSet, basename="balance-import")

urlpatterns = router.urls
