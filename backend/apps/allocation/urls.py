from rest_framework.routers import DefaultRouter

from .views import (
    AllocationRunViewSet,
    PayoutClearingViewSet,
    PSRViewSet,
    ReservePolicyViewSet,
    WeightageBandViewSet,
)

router = DefaultRouter()
router.register("weightage-bands", WeightageBandViewSet, basename="weightage-band")
router.register("psr-schedules", PSRViewSet, basename="psr-schedule")
router.register("allocation-runs", AllocationRunViewSet, basename="allocation-run")
router.register("reserve-policies", ReservePolicyViewSet, basename="reserve-policy")
router.register("payout-clearing", PayoutClearingViewSet, basename="payout-clearing")

urlpatterns = router.urls

