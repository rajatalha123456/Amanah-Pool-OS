"""
URL configuration for the amanah_pool_os project.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/products/", include("apps.products.urls")),
    path("api/v1/pools/", include("apps.pools.urls")),
    path("api/v1/participants/", include("apps.participants.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/allocation/", include("apps.allocation.urls")),
    path("api/v1/accounting/", include("apps.accounting.urls")),
    path("api/v1/governance/", include("apps.governance.urls")),
    path("api/v1/ai/", include("apps.ai_agents.urls")),
    path("api/v1/investments/", include("apps.investments.urls")),
    path("api/v1/circles/", include("apps.circles.urls")),
    path("api/v1/", include("apps.tenants.urls")),
]

# The Django admin edits tables directly, bypassing the maker-checker rules of the API. It is a development tool only:
# it is mounted when DEBUG is on, or when ENABLE_DJANGO_ADMIN is set explicitly.
if settings.DEBUG or getattr(settings, "ENABLE_DJANGO_ADMIN", False):
    urlpatterns.insert(0, path("admin/", admin.site.urls))
