from django.contrib import admin

from .models import ContractTemplate, Product, ShariahDecision


@admin.register(ShariahDecision)
class ShariahDecisionAdmin(admin.ModelAdmin):
    list_display = (
        "decision_code",
        "decision_type",
        "title",
        "tenant",
        "status",
        "effective_date",
        "created_by",
        "approved_by",
        "approved_at",
    )
    list_filter = ("status", "decision_type", "tenant")
    search_fields = ("decision_code", "title", "meeting_reference")


@admin.register(ContractTemplate)
class ContractTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "contract_type", "tenant", "status", "shariah_decision")
    list_filter = ("status", "contract_type", "tenant")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "operating_model", "status", "contract_template")
    list_filter = ("status", "operating_model", "tenant")
    search_fields = ("name", "code")
