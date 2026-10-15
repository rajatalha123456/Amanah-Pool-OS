from rest_framework.routers import DefaultRouter
from django.urls import path

from . import public_views, views

router = DefaultRouter()
# Registered before "tenants" so that "tenants/<pk>/" does not swallow these paths.
router.register("tenants/feature-flags", views.FeatureFlagViewSet, basename="feature-flag")
router.register("tenants/encryption-keys", views.EncryptionKeyRecordViewSet, basename="encryption-key")
router.register("tenants", views.TenantViewSet, basename="tenant")
router.register("demo-requests", public_views.DemoRequestViewSet, basename="demo-request")
router.register("legal-entities", views.LegalEntityViewSet, basename="legal-entity")

urlpatterns = [
    path("public/demo-requests/", public_views.submit_demo_request, name="public-demo-request"),
] + router.urls
