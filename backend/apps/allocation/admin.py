from django.contrib import admin

from .models import ProfitSharingRatio, WeightageBand


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
