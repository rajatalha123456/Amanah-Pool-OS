from rest_framework.routers import DefaultRouter

from .views import AllocationRunViewSet, PSRViewSet, ReservePolicyViewSet, WeightageBandViewSet

router = DefaultRouter()
router.register("weightage-bands", WeightageBandViewSet, basename="weightage-band")
router.register("psr-schedules", PSRViewSet, basename="psr-schedule")
router.register("allocation-runs", AllocationRunViewSet, basename="allocation-run")
router.register("reserve-policies", ReservePolicyViewSet, basename="reserve-policy")

urlpatterns = router.urls

