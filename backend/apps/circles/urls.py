from rest_framework.routers import DefaultRouter

from .views import (
    ArrearsRecordViewSet,
    CircleMemberViewSet,
    CircleProposalViewSet,
    ContributionViewSet,
    PayoutViewSet,
)
from .governance_views import CircleClosureViewSet, CircleDrawViewSet, CircleRulesViewSet

router = DefaultRouter()
router.register("circle-members", CircleMemberViewSet, basename="circle-member")
router.register("contributions", ContributionViewSet, basename="circle-contribution")
router.register("payouts", PayoutViewSet, basename="circle-payout")
router.register("arrears-records", ArrearsRecordViewSet, basename="circle-arrears-record")
router.register("circle-proposals", CircleProposalViewSet, basename="circle-proposal")
router.register("rules", CircleRulesViewSet, basename="circle-rules")
router.register("draws", CircleDrawViewSet, basename="circle-draw")
router.register("closures", CircleClosureViewSet, basename="circle-closure")

urlpatterns = router.urls
