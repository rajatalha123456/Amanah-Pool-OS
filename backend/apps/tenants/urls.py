from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("tenants", views.TenantViewSet, basename="tenant")
router.register("legal-entities", views.LegalEntityViewSet, basename="legal-entity")

urlpatterns = router.urls
