"""
URL configuration for the amanah_pool_os project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/products/", include("apps.products.urls")),
    path("api/v1/pools/", include("apps.pools.urls")),
    path("api/v1/allocation/", include("apps.allocation.urls")),
    path("api/v1/accounting/", include("apps.accounting.urls")),
]
