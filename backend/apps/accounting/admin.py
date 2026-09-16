from django.contrib import admin

from .models import JournalBatch, JournalEntry


class JournalEntryInline(admin.TabularInline):
    model = JournalEntry
    extra = 0
    readonly_fields = ("account_name", "entry_type", "amount")


@admin.register(JournalBatch)
class JournalBatchAdmin(admin.ModelAdmin):
    list_display = (
        "pool",
        "batch_date",
        "total_debit",
        "total_credit",
        "status",
        "posted_by",
        "allocation_run",
    )
    list_filter = ("status", "tenant")
    inlines = [JournalEntryInline]


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("batch", "account_name", "entry_type", "amount")
    list_filter = ("entry_type", "tenant")
