from django.contrib import admin

from .models import Asset, AssetAssignment, BalanceImportBatch, DailyBalance, Pool, PoolVersion


@admin.register(Pool)
class PoolAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "product", "status", "effective_date", "closed_date")
    list_filter = ("status", "tenant")
    search_fields = ("name", "code")


@admin.register(PoolVersion)
class PoolVersionAdmin(admin.ModelAdmin):
    list_display = ("pool", "version_number", "is_current", "created_by", "created_at")
    list_filter = ("is_current", "tenant")


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("reference_code", "asset_type", "face_value", "status", "tenant")
    list_filter = ("asset_type", "status", "tenant")
    search_fields = ("reference_code", "description")


@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = ("asset", "pool", "assigned_date", "unassigned_date", "assigned_by", "tenant")
    list_filter = ("tenant",)


@admin.register(DailyBalance)
class DailyBalanceAdmin(admin.ModelAdmin):
    list_display = ("pool", "participant_class", "value_date", "balance_amount", "source", "status", "tenant")
    list_filter = ("status", "source", "tenant")


@admin.register(BalanceImportBatch)
class BalanceImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "pool",
        "value_date",
        "total_records",
        "matched_records",
        "exception_count",
        "control_total_expected",
        "control_total_actual",
        "status",
        "imported_by",
    )
    list_filter = ("status", "tenant")
