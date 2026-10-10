from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AIModelRegistryViewSet,
    analyze_contract,
    ask,
    list_documents,
    predict_circle_hardship,
    detect_collusion_network,
    review,
    run_audit_sampling,
    upload_document,
)

router = DefaultRouter()
router.register("models", AIModelRegistryViewSet, basename="ai-model")

urlpatterns = [
    path("shariah-copilot/documents/upload/", upload_document, name="shariah-copilot-document-upload"),
    path("shariah-copilot/documents/", list_documents, name="shariah-copilot-document-list"),
    path("shariah-copilot/ask/", ask, name="shariah-copilot-ask"),
    path("shariah-copilot/review/<str:evidence_pack_id>/", review, name="shariah-copilot-review"),
    path("contract-analyzer/analyze/", analyze_contract, name="contract-analyzer-analyze"),
    path("audit-sampling/analyze/", run_audit_sampling, name="ai-audit-sampling-analyze"),
    path("circles/<uuid:pool_id>/predict-hardship/", predict_circle_hardship, name="ai-circle-predict-hardship"),
    path("fraud-collusion/detect/", detect_collusion_network, name="ai-fraud-collusion-detect"),
]

urlpatterns += router.urls
