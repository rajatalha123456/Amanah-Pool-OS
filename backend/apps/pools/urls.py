from rest_framework.routers import DefaultRouter

from .views import PoolViewSet

router = DefaultRouter()
router.register("pools", PoolViewSet, basename="pool")

urlpatterns = router.urls
