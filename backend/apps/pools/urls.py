from rest_framework.routers import DefaultRouter

from .views import (
    DailyCloseViewSet,
    AssetAssignmentViewSet,
    AssetTransferViewSet,
    AssetProvisionEntryViewSet,
    AssetViewSet,
    BalanceImportViewSet,
    DailyBalanceViewSet,
    PeriodCloseChecklistViewSet,
    PoolViewSet,
)

router = DefaultRouter()
router.register("pools", PoolViewSet, basename="pool")
router.register("assets", AssetViewSet, basename="asset")
router.register("asset-provisions", AssetProvisionEntryViewSet, basename="asset-provision")
router.register("asset-assignments", AssetAssignmentViewSet, basename="asset-assignment")
router.register("asset-transfers", AssetTransferViewSet, basename="asset-transfer")
router.register("daily-balances", DailyBalanceViewSet, basename="daily-balance")
router.register("balance-imports", BalanceImportViewSet, basename="balance-import")
router.register("daily-closes", DailyCloseViewSet, basename="daily-close")
router.register("period-closes", PeriodCloseChecklistViewSet, basename="period-closes")

urlpatterns = router.urls
