from rest_framework.routers import DefaultRouter

from .views import ExceptionCaseViewSet

router = DefaultRouter()
router.register("exceptions", ExceptionCaseViewSet, basename="exception-case")

urlpatterns = router.urls
