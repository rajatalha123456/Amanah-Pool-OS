from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AIModelRegistryViewSet, ask, list_documents, review, upload_document

router = DefaultRouter()
router.register("models", AIModelRegistryViewSet, basename="ai-model")

urlpatterns = [
    path("shariah-copilot/documents/upload/", upload_document, name="shariah-copilot-document-upload"),
    path("shariah-copilot/documents/", list_documents, name="shariah-copilot-document-list"),
    path("shariah-copilot/ask/", ask, name="shariah-copilot-ask"),
    path("shariah-copilot/review/<str:evidence_pack_id>/", review, name="shariah-copilot-review"),
]

urlpatterns += router.urls
