from django.db import models

from apps.core.models import TenantScopedModel


class ShariahDecisionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    # BRD 6.1: the Shariah authority approves, rejects or returns the review pack.
    RETURNED = "returned", "Returned to the Secretariat"
    REJECTED = "rejected", "Rejected"
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
    # What the ruling covers (products, contract types, pools) and the earlier ruling it replaces.
    scope = models.TextField(blank=True, default="")
    supersedes = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="superseded_by"
    )
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
    # Each return to the Secretariat opens a new review round; only the votes of the current round count.
    review_round = models.PositiveIntegerField(default=1)
    return_note = models.TextField(blank=True, default="")

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
    # Asset types (pools.AssetType values) a pool of this product may hold. Empty = no restriction.
    eligible_asset_types = models.JSONField(default=list, blank=True)
    # Investment-pool exit terms: minimum notice before the dealing date, and the share of pool value that may
    # be redeemed in any 30-day window (100 = no gate).
    redemption_notice_days = models.PositiveIntegerField(default=0)
    redemption_gate_pct = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    # Participation terms. Empty / zero means "no limit".
    minimum_subscription = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    subscription_cap = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)  # per account, in total
    minimum_tenure_days = models.PositiveIntegerField(default=0)  # no redemption before first subscription + N days
    required_kyc_tier = models.CharField(max_length=10, default="basic")  # basic < standard < enhanced
    max_participants = models.PositiveIntegerField(null=True, blank=True)  # accounts / members per pool

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        RulePackRevision.record(self)

    def __str__(self):
        return f"{self.name} v{self.version} ({self.code})"


class RulePackRevision(TenantScopedModel):
    """
    One immutable row for every distinct content a rule pack has had (BRD 11: a signed run references immutable
    rule-pack versions). A run seals the hash of the pack it used; this history lets anyone read what that content was.
    """

    pack = models.ForeignKey(JurisdictionRulePack, on_delete=models.PROTECT, related_name="revisions")
    revision = models.PositiveIntegerField()
    content_hash = models.CharField(max_length=64)
    content = models.JSONField()

    class Meta:
        ordering = ["-revision"]
        constraints = [models.UniqueConstraint(fields=["pack", "revision"], name="unique_rulepack_revision")]

    @staticmethod
    def content_of(pack):
        effective = pack.effective_date
        return {
            "version": pack.version,
            "effective_date": effective.isoformat() if hasattr(effective, "isoformat") else str(effective),
            "is_active": bool(pack.is_active),
            "is_default": bool(pack.is_default),
            "rules_config": pack.rules_config or {},
        }

    @staticmethod
    def hash_of(content):
        import hashlib
        import json

        return hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    @classmethod
    def record(cls, pack):
        content = cls.content_of(pack)
        digest = cls.hash_of(content)
        last = cls._base_manager.filter(pack=pack).order_by("-revision").first()
        if last is not None and last.content_hash == digest:
            return last
        return cls._base_manager.create(
            tenant_id=pack.tenant_id, pack=pack, revision=(last.revision + 1) if last else 1,
            content_hash=digest, content=content,
        )

    def save(self, *args, **kwargs):
        if not self._state.adding:
            from django.core.exceptions import ValidationError

            raise ValidationError("A rule pack revision is a historical record and cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError

        raise ValidationError("A rule pack revision is a historical record and cannot be deleted.")


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
    review_round = models.PositiveIntegerField(default=1)
    digital_signature_hash = models.CharField(max_length=64)
    voted_at = models.DateTimeField(auto_now_add=True)
    signatory_user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["voted_at"]

    def __str__(self):
        return f"{self.scholar_name} ({self.decision_vote}) - {self.decision.decision_code}"


