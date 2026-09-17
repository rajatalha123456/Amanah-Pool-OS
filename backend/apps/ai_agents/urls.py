from django.urls import path

from .views import ask, list_documents, review, upload_document

urlpatterns = [
    path("shariah-copilot/documents/upload/", upload_document, name="shariah-copilot-document-upload"),
    path("shariah-copilot/documents/", list_documents, name="shariah-copilot-document-list"),
    path("shariah-copilot/ask/", ask, name="shariah-copilot-ask"),
    path("shariah-copilot/review/<str:evidence_pack_id>/", review, name="shariah-copilot-review"),
]
