from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("core/audit-log", views.AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("health/", views.health_check, name="health-check"),
    path("core/audit-log/export/", views.audit_log_export, name="audit-log-export"),
] + router.urls
