from rest_framework.routers import DefaultRouter

from .views import AssetAssignmentViewSet, AssetViewSet, PoolViewSet

router = DefaultRouter()
router.register("pools", PoolViewSet, basename="pool")
router.register("assets", AssetViewSet, basename="asset")
router.register("asset-assignments", AssetAssignmentViewSet, basename="asset-assignment")

urlpatterns = router.urls
