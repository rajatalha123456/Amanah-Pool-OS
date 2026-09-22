from rest_framework.routers import DefaultRouter

from .views import CircleMemberViewSet, ContributionViewSet, PayoutViewSet

router = DefaultRouter()
router.register("circle-members", CircleMemberViewSet, basename="circle-member")
router.register("contributions", ContributionViewSet, basename="circle-contribution")
router.register("payouts", PayoutViewSet, basename="circle-payout")

urlpatterns = router.urls
