from rest_framework.routers import DefaultRouter

from .views import PSRViewSet, WeightageBandViewSet

router = DefaultRouter()
router.register("weightage-bands", WeightageBandViewSet, basename="weightage-band")
router.register("psr-schedules", PSRViewSet, basename="psr-schedule")

urlpatterns = router.urls
