from django.contrib import admin

from .models import Pool, PoolVersion


@admin.register(Pool)
class PoolAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "product", "status", "effective_date", "closed_date")
    list_filter = ("status", "tenant")
    search_fields = ("name", "code")


@admin.register(PoolVersion)
class PoolVersionAdmin(admin.ModelAdmin):
    list_display = ("pool", "version_number", "is_current", "created_by", "created_at")
    list_filter = ("is_current", "tenant")
