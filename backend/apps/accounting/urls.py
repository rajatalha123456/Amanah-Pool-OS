from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import JournalBatchViewSet, gl_export

router = DefaultRouter()
router.register("journal-batches", JournalBatchViewSet, basename="journal-batch")

urlpatterns = [
    path("journal-batches/gl-export/", gl_export, name="journal-batch-gl-export"),
] + router.urls
