"""
The Shariah Policy Copilot's library and its research output (BRD 9: approved knowledge base only, paragraph-level
citations, no cross-tenant retrieval). Everything is tenant-scoped through TenantScopedModel, so a query can only ever see
its own tenant's documents.
"""

from django.db import models

from apps.core.models import TenantScopedModel


class ApprovalStatus(models.TextChoices):
    APPROVED = "approved", "Approved"
    UNDER_REVIEW = "under_review", "Under review"
    DRAFT = "draft", "Draft"
    ARCHIVED = "archived", "Archived"


STATUS_EMOJI = {"approved": "🟢", "under_review": "🟡", "draft": "🔴", "archived": "⚫"}


class CopilotDocument(TenantScopedModel):
    """A source Shariah document: ruling, fatwa, standard, policy, circular, SOP ..."""

    document_name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=50)  # ruling|fatwa|standard|policy|resolution|minutes|circular|sop|guideline
    version = models.CharField(max_length=30, default="1.0")
    approval_status = models.CharField(max_length=15, choices=ApprovalStatus.choices, default=ApprovalStatus.DRAFT)
    approval_date = models.DateTimeField(null=True, blank=True)
    effective_date = models.DateTimeField(null=True, blank=True)
    expiry_review_date = models.DateTimeField(null=True, blank=True)
    product_category = models.CharField(max_length=100, blank=True, default="")
    jurisdiction = models.CharField(max_length=100, blank=True, default="")
    # Who uploaded it and who approved it: never the same person (four eyes on what the AI may rely on).
    uploaded_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    approved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    confidentiality_level = models.CharField(max_length=20, default="internal")
    source_file_path = models.CharField(max_length=500, blank=True, default="")
    content_hash = models.CharField(max_length=64, blank=True, default="")
    is_current_version = models.BooleanField(default=True)
    supersedes = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="superseded_by")

    class Meta:
        ordering = ["-created_at"]

    @property
    def status_emoji(self):
        return STATUS_EMOJI.get(self.approval_status, "")

    def __str__(self):
        return f"{self.document_name} v{self.version}"


class CopilotChunk(TenantScopedModel):
    """A clause/section-level piece of a document; carries what a citation needs."""

    document = models.ForeignKey(CopilotDocument, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.IntegerField()
    section_label = models.CharField(max_length=80, blank=True, default="")
    page_number = models.IntegerField(null=True, blank=True)
    text = models.TextField()
    # L2-normalised float32 vector (see embeddings.py) and the model that produced it; empty when semantic search is off.
    embedding = models.BinaryField(null=True, blank=True)
    embedding_model = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        ordering = ["document_id", "chunk_index"]
        indexes = [models.Index(fields=["document", "chunk_index"])]


class ReviewStatus(models.TextChoices):
    HUMAN_REVIEW_REQUIRED = "human_review_required", "Human review required"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class EvidencePack(TenantScopedModel):
    """One research answer. It always starts as 'human review required' (BRD 1: AI never issues a ruling)."""

    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="+")
    question = models.TextField()
    research_summary = models.TextField()
    relevant_rulings = models.JSONField(default=list)
    relevant_standards = models.JSONField(default=list)
    key_evidence_excerpts = models.JSONField(default=list)
    comparison_table = models.JSONField(default=list)
    open_issues = models.JSONField(default=list)
    citations = models.JSONField(default=list)
    conflict_flagged = models.BooleanField(default=False)
    is_fallback = models.BooleanField(default=False)
    retrieval_mode = models.CharField(max_length=20, default="hybrid")  # hybrid | keyword_only
    disclaimer = models.TextField()
    review_status = models.CharField(max_length=25, choices=ReviewStatus.choices, default=ReviewStatus.HUMAN_REVIEW_REQUIRED)
    reviewer = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
