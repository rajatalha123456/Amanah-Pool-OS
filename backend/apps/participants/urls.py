from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ConsentViewSet, my_tax_support, ParticipantAccountViewSet, ParticipantViewSet

router = DefaultRouter()
router.register("participants", ParticipantViewSet, basename="participant")
router.register("consents", ConsentViewSet, basename="consent")
router.register("accounts", ParticipantAccountViewSet, basename="participant-account")

urlpatterns = [path("my-tax-support/", my_tax_support, name="my-tax-support")] + router.urls
