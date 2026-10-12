from rest_framework.routers import DefaultRouter

from .distribution_views import DistributionRunViewSet
from .negligence_views import NegligenceCaseViewSet
from .disclosure_views import PoolDisclosureViewSet
from .views import (
	CapitalAccountViewSet,
	ImpairmentEventViewSet,
	InvestorProfileViewSet,
	NAVSnapshotViewSet,
	RedemptionViewSet,
	SubscriptionViewSet,
)

router = DefaultRouter()
router.register("capital-accounts", CapitalAccountViewSet, basename="capital-account")
router.register("nav-snapshots", NAVSnapshotViewSet, basename="nav-snapshot")
router.register("investor-profiles", InvestorProfileViewSet, basename="investor-profile")
router.register("disclosures", PoolDisclosureViewSet, basename="pool-disclosure")
router.register("impairment-events", ImpairmentEventViewSet, basename="impairment-event")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("redemptions", RedemptionViewSet, basename="redemption")
router.register("distribution-runs", DistributionRunViewSet, basename="distribution-run")
router.register("negligence-cases", NegligenceCaseViewSet, basename="negligence-case")

urlpatterns = router.urls
