from rest_framework.routers import DefaultRouter

from .views import AllocationRunViewSet, PSRViewSet, WeightageBandViewSet

router = DefaultRouter()
router.register("weightage-bands", WeightageBandViewSet, basename="weightage-band")
router.register("psr-schedules", PSRViewSet, basename="psr-schedule")
router.register("allocation-runs", AllocationRunViewSet, basename="allocation-run")

urlpatterns = router.urls
