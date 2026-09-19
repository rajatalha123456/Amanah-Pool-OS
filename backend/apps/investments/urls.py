from rest_framework.routers import DefaultRouter

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
router.register("impairment-events", ImpairmentEventViewSet, basename="impairment-event")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("redemptions", RedemptionViewSet, basename="redemption")

urlpatterns = router.urls
