from django.db import models

from apps.core.models import TenantScopedModel


class ShariahDecisionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    SUPERSEDED = "superseded", "Superseded"


class ShariahDecisionType(models.TextChoices):
    PRODUCT_APPROVAL = "product_approval", "Product Approval"
    POLICY_RULING = "policy_ruling", "Policy Ruling"
    ANNUAL_REVIEW = "annual_review", "Annual Review"
    PURIFICATION_DIRECTIVE = "purification_directive", "Purification Directive"
    EXEMPTION = "exemption", "Exemption"


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
    decision_type = models.CharField(
        max_length=30,
        choices=ShariahDecisionType.choices,
        default=ShariahDecisionType.PRODUCT_APPROVAL,
    )
    meeting_reference = models.CharField(max_length=100, null=True, blank=True)
    scholars_signatories = models.TextField(null=True, blank=True)
    fiqh_reference = models.TextField(null=True, blank=True)
    description = models.TextField()
    mandatory_caveats = models.TextField(null=True, blank=True)
    fatwa_arabic_text = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=ShariahDecisionStatus.choices, default=ShariahDecisionStatus.DRAFT
    )
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    document_url = models.URLField(max_length=500, null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_shariah_decisions",
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_shariah_decisions",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.decision_code} - {self.title}"



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


class JurisdictionRulePack(TenantScopedModel):
    """
    Screen 42: Administration & Rule Packs - Jurisdictions, roles and effective versions.
    """

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=20, default="2025.01")
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    rules_config = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code", "version"], name="unique_rulepack_version_per_tenant"
            ),
        ]
        ordering = ["-effective_date"]

    def __str__(self):
        return f"{self.name} v{self.version} ({self.code})"


class QuorumVoteDecision(models.TextChoices):
    APPROVE = "approve", "Approve"
    REJECT = "reject", "Reject"
    ABSTAIN = "abstain", "Abstain"


class ShariahQuorumVote(TenantScopedModel):
    """
    Records an individual Shariah scholar's vote and cryptographic sign-off
    toward the collective board quorum required to enact a fatwa or product approval.
    """

    decision = models.ForeignKey(
        ShariahDecision, on_delete=models.CASCADE, related_name="quorum_votes"
    )
    scholar_name = models.CharField(max_length=255)
    scholar_title = models.CharField(max_length=150)
    decision_vote = models.CharField(
        max_length=20, choices=QuorumVoteDecision.choices, default=QuorumVoteDecision.APPROVE
    )
    fiqh_concurrence_notes = models.TextField(blank=True, default="")
    digital_signature_hash = models.CharField(max_length=64)
    voted_at = models.DateTimeField(auto_now_add=True)
    signatory_user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["voted_at"]

    def __str__(self):
        return f"{self.scholar_name} ({self.decision_vote}) - {self.decision.decision_code}"


