from rest_framework.routers import DefaultRouter
from django.urls import path

from . import public_views, views

router = DefaultRouter()
router.register("tenants", views.TenantViewSet, basename="tenant")
router.register("demo-requests", public_views.DemoRequestViewSet, basename="demo-request")
router.register("legal-entities", views.LegalEntityViewSet, basename="legal-entity")

urlpatterns = [
    path("public/demo-requests/", public_views.submit_demo_request, name="public-demo-request"),
] + router.urls
