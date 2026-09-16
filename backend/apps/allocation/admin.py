from django.contrib import admin

from .models import (
    AllocationLine,
    AllocationRun,
    DepositorStatement,
    ProfitSharingRatio,
    WeightageBand,
)


@admin.register(WeightageBand)
class WeightageBandAdmin(admin.ModelAdmin):
    list_display = (
        "pool",
        "participant_class",
        "weightage",
        "effective_from",
        "effective_to",
        "status",
        "tenant",
    )
    list_filter = ("status", "tenant")
    search_fields = ("participant_class",)


@admin.register(ProfitSharingRatio)
class ProfitSharingRatioAdmin(admin.ModelAdmin):
    list_display = (
        "pool",
        "depositor_share",
        "mudarib_share",
        "effective_from",
        "effective_to",
        "status",
        "tenant",
    )
    list_filter = ("status", "tenant")


class AllocationLineInline(admin.TabularInline):
    model = AllocationLine
    extra = 0
    readonly_fields = ("participant_class", "daily_funds", "weightage", "weighted_funds", "allocated_amount")


@admin.register(AllocationRun)
class AllocationRunAdmin(admin.ModelAdmin):
    list_display = (
        "pool",
        "value_date",
        "gross_income",
        "distributable_amount",
        "depositor_pool_share",
        "mudarib_share",
        "status",
        "created_by",
    )
    list_filter = ("status", "tenant")
    inlines = [AllocationLineInline]


@admin.register(AllocationLine)
class AllocationLineAdmin(admin.ModelAdmin):
    list_display = ("allocation_run", "participant_class", "daily_funds", "weightage", "allocated_amount")
    list_filter = ("tenant",)


@admin.register(DepositorStatement)
class DepositorStatementAdmin(admin.ModelAdmin):
    list_display = (
        "allocation_run",
        "participant_class",
        "period_start",
        "period_end",
        "opening_balance",
        "profit_allocated",
        "closing_balance",
        "generated_at",
    )
    list_filter = ("tenant",)
