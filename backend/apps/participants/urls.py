from rest_framework.routers import DefaultRouter

from .views import ParticipantAccountViewSet, ParticipantViewSet

router = DefaultRouter()
router.register("participants", ParticipantViewSet, basename="participant")
router.register("accounts", ParticipantAccountViewSet, basename="participant-account")

urlpatterns = router.urls
