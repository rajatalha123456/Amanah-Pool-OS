from django.db import models

from apps.core.models import TenantScopedModel


class ShariahDecisionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    SUPERSEDED = "superseded", "Superseded"


class ContractType(models.TextChoices):
    MUDARABAH_UNRESTRICTED = "mudarabah_unrestricted", "Mudarabah (Unrestricted)"
    MUDARABAH_RESTRICTED = "mudarabah_restricted", "Mudarabah (Restricted)"
    MUSHARAKAH = "musharakah", "Musharakah"
    WAKALAH = "wakalah", "Wakalah"
    QARD = "qard", "Qard"


class ContractTemplateStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    RETIRED = "retired", "Retired"


class OperatingModel(models.TextChoices):
    BANK_POOL = "bank_pool", "Bank Pool"
    INVESTMENT_POOL = "investment_pool", "Investment Pool"
    COMMUNITY_CIRCLE = "community_circle", "Community Circle"


class ProductStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SHARIAH_REVIEW = "shariah_review", "Shariah Review"
    APPROVED = "approved", "Approved"
    ACTIVE = "active", "Active"
    RETIRED = "retired", "Retired"


class ShariahDecision(TenantScopedModel):
    decision_code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=20, choices=ShariahDecisionStatus.choices, default=ShariahDecisionStatus.DRAFT
    )
    effective_date = models.DateField()
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_shariah_decisions",
    )

    def __str__(self):
        return self.decision_code


class ContractTemplate(TenantScopedModel):
    name = models.CharField(max_length=255)
    contract_type = models.CharField(max_length=30, choices=ContractType.choices)
    version = models.CharField(max_length=20)
    clauses = models.JSONField()
    shariah_decision = models.ForeignKey(
        ShariahDecision,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contract_templates",
    )
    status = models.CharField(
        max_length=20, choices=ContractTemplateStatus.choices, default=ContractTemplateStatus.DRAFT
    )

    def __str__(self):
        return f"{self.name} v{self.version}"


class Product(TenantScopedModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    operating_model = models.CharField(max_length=30, choices=OperatingModel.choices)
    contract_template = models.ForeignKey(
        ContractTemplate, on_delete=models.PROTECT, related_name="products"
    )
    status = models.CharField(max_length=20, choices=ProductStatus.choices, default=ProductStatus.DRAFT)
    base_currency = models.CharField(max_length=10, default="PKR")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="unique_product_code_per_tenant"),
        ]

    def __str__(self):
        return self.name
