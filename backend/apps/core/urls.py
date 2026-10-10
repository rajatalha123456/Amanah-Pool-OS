from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("core/audit-log", views.AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("health/", views.health_check, name="health-check"),
    path("core/audit-log/export/", views.audit_log_export, name="audit-log-export"),
    path("banking/settle/", views.process_banking_settlement, name="banking-settle"),
    path("core/evidence-bundle/compile/", views.compile_evidence_bundle, name="evidence-bundle-compile"),
    path("core/evidence-bundle/download/", views.download_evidence_bundle_zip, name="evidence-bundle-download"),
] + router.urls

