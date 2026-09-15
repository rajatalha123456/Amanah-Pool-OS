from django.contrib import admin

from .models import LegalEntity, Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "domain", "data_residency", "is_suspended", "is_active")
    search_fields = ("name", "code", "domain")


@admin.register(LegalEntity)
class LegalEntityAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "jurisdiction", "base_currency", "timezone", "is_active")
    search_fields = ("name", "registration_number")
    list_filter = ("tenant", "jurisdiction")
