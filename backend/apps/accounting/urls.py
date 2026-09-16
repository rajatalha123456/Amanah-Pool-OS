from rest_framework.routers import DefaultRouter

from .views import JournalBatchViewSet

router = DefaultRouter()
router.register("journal-batches", JournalBatchViewSet, basename="journal-batch")

urlpatterns = router.urls
