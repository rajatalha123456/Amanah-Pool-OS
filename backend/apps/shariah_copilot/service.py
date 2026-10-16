"""
The copilot's public interface for the rest of the platform (views, contract analyzer). Everything here runs in-process and
is scoped to the calling user's tenant.
"""

from datetime import datetime

from django.utils import timezone

from . import agent, ingestion
from .models import ApprovalStatus, CopilotDocument, EvidencePack, ReviewStatus
from .retrieval import candidate_documents

DOCUMENT_TYPES = ("ruling", "fatwa", "standard", "policy", "resolution", "minutes", "circular", "sop", "guideline")


class CopilotRefused(Exception):
    """A request the copilot will not carry out; carries an HTTP status and a plain message."""

    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail
        super().__init__(detail)


def serialise_document(d):
    return {
        "id": str(d.id), "document_name": d.document_name, "document_type": d.document_type, "version": d.version,
        "approval_status": d.approval_status, "status_emoji": d.status_emoji,
        "approval_date": d.approval_date.isoformat() if d.approval_date else None,
        "product_category": d.product_category or None, "jurisdiction": d.jurisdiction or None,
        "is_current_version": 1 if d.is_current_version else 0,
        "uploaded_by": d.uploaded_by_id, "approved_by": d.approved_by_id,
    }


def upload_document(user, uploaded, data):
    """
    Adds a document to the tenant's library as a draft or under review. A source only becomes something the AI may rely
    on when a Shariah Board member who did NOT upload it approves it (approve_document): the people who feed the
    library cannot also declare it authoritative.
    """
    name, doc_type = str(data.get("document_name") or "").strip(), str(data.get("document_type") or "").strip().lower()
    if not name:
        raise CopilotRefused(400, "document_name is required.")
    if doc_type not in DOCUMENT_TYPES:
        raise CopilotRefused(400, f"document_type must be one of: {', '.join(DOCUMENT_TYPES)}.")
    status = str(data.get("approval_status") or ApprovalStatus.DRAFT)
    if status == ApprovalStatus.APPROVED:
        raise CopilotRefused(
            400, "A document is approved by a Shariah Board member other than the uploader: upload it as under_review, then approve it."
        )
    if status not in (ApprovalStatus.DRAFT, ApprovalStatus.UNDER_REVIEW):
        raise CopilotRefused(400, "A new document starts as draft or under_review.")
    supersedes = None
    if data.get("supersedes_document_id"):
        supersedes = CopilotDocument.objects.filter(pk=data["supersedes_document_id"], tenant=user.tenant).first()
        if supersedes is None:
            raise CopilotRefused(400, "The document to supersede was not found in this tenant.")
    metadata = {
        "document_name": name, "document_type": doc_type, "version": str(data.get("version") or "1.0"),
        "approval_status": status, "product_category": str(data.get("product_category") or ""),
        "jurisdiction": str(data.get("jurisdiction") or ""), "confidentiality_level": str(data.get("confidentiality_level") or "internal"),
        "supersedes": supersedes,
    }
    try:
        document = ingestion.ingest(tenant=user.tenant, user=user, uploaded=uploaded, metadata=metadata)
    except ingestion.UnsupportedFile as exc:
        raise CopilotRefused(400, str(exc)) from exc
    return serialise_document(document)


def approve_document(user, document_id, approve=True):
    document = CopilotDocument.objects.filter(pk=document_id, tenant=user.tenant).first()
    if document is None:
        raise CopilotRefused(404, "Document not found.")
    if document.approval_status == ApprovalStatus.APPROVED and approve:
        raise CopilotRefused(400, "This document is already approved.")
    if document.uploaded_by_id == user.id:
        raise CopilotRefused(400, "Four eyes: the Board member who uploaded a document cannot be the one who approves it.")
    document.approval_status = ApprovalStatus.APPROVED if approve else ApprovalStatus.ARCHIVED
    document.approved_by = user if approve else None
    document.approval_date = timezone.now() if approve else None
    document.save(update_fields=["approval_status", "approved_by", "approval_date", "updated_at"])
    return serialise_document(document)


def list_documents(user, params):
    docs = CopilotDocument.objects.filter(tenant=user.tenant)
    for field in ("approval_status", "document_type", "product_category"):
        if params.get(field):
            docs = docs.filter(**{field: params[field]})
    if str(params.get("current_only", "true")).lower() in ("true", "1"):
        docs = docs.filter(is_current_version=True)
    return [serialise_document(d) for d in docs.order_by("-created_at")]


def ask_question(user, question, filters):
    return agent.ask(user.tenant, user, question, _clean_filters(filters))


def _clean_filters(filters):
    """Only the documented filters are honoured; a caller cannot widen the scope to unapproved or other tenants' material."""
    allowed = {"approved_only", "current_version_only", "product_category", "document_type", "date_from", "date_to"}
    clean = {k: v for k, v in (filters or {}).items() if k in allowed and v not in (None, "")}
    for key in ("date_from", "date_to"):
        if key in clean:
            try:
                clean[key] = datetime.fromisoformat(str(clean[key]))
            except ValueError:
                clean.pop(key)
    clean["approved_only"] = True  # the AI relies on approved sources only (BRD 9); this is not a caller's choice
    return clean


def submit_review(user, pack_id, approve):
    pack = EvidencePack.objects.filter(pk=pack_id, tenant=user.tenant).first()
    if pack is None:
        raise CopilotRefused(404, f"Evidence pack not found: {pack_id}")
    pack.review_status = ReviewStatus.APPROVED if approve else ReviewStatus.REJECTED
    pack.reviewer, pack.reviewed_at = user, timezone.now()
    pack.save(update_fields=["review_status", "reviewer", "reviewed_at", "updated_at"])
    return {"id": str(pack.id), "review_status": pack.review_status, "reviewer_id": user.id, "reviewed_at": str(pack.reviewed_at)}


def library_size(user):
    return candidate_documents(user.tenant, {}).count()
