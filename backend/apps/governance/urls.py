from rest_framework.routers import DefaultRouter

from .views import ExceptionCaseViewSet, PurificationEntryViewSet

router = DefaultRouter()
router.register("exceptions", ExceptionCaseViewSet, basename="exception-case")
router.register("purification-entries", PurificationEntryViewSet, basename="purification-entry")

urlpatterns = router.urls
