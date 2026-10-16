"""
Hybrid retrieval (BRD 9): the candidate set is fixed first by tenant, approval status and version (so only approved,
current, own-tenant documents can ever be read), then ranked by BM25 and by embedding similarity and merged with reciprocal
rank fusion. A semantic hit must clear a minimum similarity, so an unrelated question finds nothing and takes the fixed
"no approved evidence" fallback.
"""

from dataclasses import dataclass

import numpy as np
from django.conf import settings

from . import embeddings
from .models import ApprovalStatus, CopilotChunk, CopilotDocument
from .search import bm25_rank

RRF_K = 60


@dataclass
class Retrieved:
    chunk: CopilotChunk
    document: CopilotDocument
    source: str  # semantic | keyword | both


def candidate_documents(tenant, filters):
    if tenant is None:
        raise ValueError("A tenant is required for retrieval.")
    docs = CopilotDocument.objects.filter(tenant=tenant)
    if filters.get("approved_only", True):
        docs = docs.filter(approval_status=ApprovalStatus.APPROVED)
    if filters.get("current_version_only", True):
        docs = docs.filter(is_current_version=True)
    for field in ("product_category", "document_type"):
        if filters.get(field):
            docs = docs.filter(**{field: filters[field]})
    if filters.get("date_from"):
        docs = docs.filter(approval_date__gte=filters["date_from"])
    if filters.get("date_to"):
        docs = docs.filter(approval_date__lte=filters["date_to"])
    return docs


def retrieve(tenant, question, filters):
    """Returns (list[Retrieved], mode) where mode is 'hybrid' or 'keyword_only'."""
    documents = {d.id: d for d in candidate_documents(tenant, filters)}
    if not documents:
        return [], "hybrid"
    chunks = list(CopilotChunk.objects.filter(tenant=tenant, document_id__in=list(documents)).order_by("document_id", "chunk_index"))
    if not chunks:
        return [], "hybrid"

    keyword = [i for i, _ in bm25_rank(question, [c.text for c in chunks])[: settings.COPILOT_TOP_K_KEYWORD]]

    semantic, mode = [], "hybrid"
    try:
        wanted = embeddings.model_name()
        usable = [i for i, c in enumerate(chunks) if c.embedding and c.embedding_model == wanted]
        if not usable:
            raise embeddings.EmbeddingsUnavailable("No chunk has an embedding from the current model.")
        query_vector = embeddings.embed([question])[0]
        matrix = np.vstack([embeddings.from_bytes(chunks[i].embedding) for i in usable])
        scores = matrix @ query_vector
        order = np.argsort(-scores)[: settings.COPILOT_TOP_K_SEMANTIC]
        semantic = [usable[j] for j in order if scores[j] >= settings.COPILOT_MIN_SEMANTIC_SCORE]
    except embeddings.EmbeddingsUnavailable:
        mode = "keyword_only"

    fused = {}
    for ranking in (semantic, keyword):
        for rank, index in enumerate(ranking):
            fused[index] = fused.get(index, 0.0) + 1.0 / (RRF_K + rank + 1)
    ordered = sorted(fused, key=lambda i: fused[i], reverse=True)[: settings.COPILOT_TOP_K_FINAL]

    results = []
    for index in ordered:
        in_semantic, in_keyword = index in semantic, index in keyword
        source = "both" if in_semantic and in_keyword else "semantic" if in_semantic else "keyword"
        results.append(Retrieved(chunk=chunks[index], document=documents[chunks[index].document_id], source=source))
    return results, mode
