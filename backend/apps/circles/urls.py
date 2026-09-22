from rest_framework.routers import DefaultRouter

from .views import ArrearsRecordViewSet, CircleMemberViewSet, ContributionViewSet, PayoutViewSet

router = DefaultRouter()
router.register("circle-members", CircleMemberViewSet, basename="circle-member")
router.register("contributions", ContributionViewSet, basename="circle-contribution")
router.register("payouts", PayoutViewSet, basename="circle-payout")
router.register("arrears-records", ArrearsRecordViewSet, basename="circle-arrears-record")

urlpatterns = router.urls
