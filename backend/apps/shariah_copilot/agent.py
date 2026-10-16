"""
The copilot's answer pipeline (BRD 9): retrieve approved evidence, have the model draft a cited summary from it, check the
draft against that evidence, and store the result as an evidence pack that always waits for a Shariah reviewer.
It never answers from general knowledge: no evidence, or a model that cannot ground its answer, ends in the fixed fallback.
"""

import json

from . import llm
from .models import EvidencePack, ReviewStatus
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .retrieval import retrieve

DISCLAIMER_TEXT = (
    "This research output does not constitute a fatwa or final Shariah "
    "determination. Human Shariah review is required."
)

NO_EVIDENCE_FALLBACK = (
    "No approved internal Shariah ruling or standard was found that addresses "
    "this question. This matter should be referred to a designated Shariah "
    "reviewer for a fresh determination. No general or external knowledge has "
    "been used to answer this query."
)


def _citation(retrieved):
    document, chunk = retrieved.document, retrieved.chunk
    return {
        "document_id": str(document.id),
        "document_name": document.document_name,
        "version": document.version,
        "section_label": chunk.section_label or None,
        "page_number": chunk.page_number,
        "approval_date": str(document.approval_date) if document.approval_date else None,
    }


def _draft(question, blocks):
    """
    One model call, retried once when the reply is not valid JSON (Urdu and Arabic use many tokens, so a long reply can be
    cut off mid-object). A second failure is treated as no answer, never as a guess.
    """
    prompt = build_user_prompt(question, blocks)
    parsed = _parse_json(llm.generate(SYSTEM_PROMPT, prompt, max_tokens=4096))
    if parsed.get("research_summary") == "NO_EVIDENCE_FOUND" and len(parsed) == 1:
        retry = prompt + "\n\nYour previous reply was not valid JSON. Reply again with ONE complete, valid JSON object and keep it concise."
        parsed = _parse_json(llm.generate(SYSTEM_PROMPT, retry, max_tokens=4096))
    return parsed


def _parse_json(raw):
    """Models sometimes wrap JSON in prose or code fences; strip defensively. Anything unparseable means no answer."""
    text = (raw or "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {"research_summary": "NO_EVIDENCE_FOUND"}
    try:
        parsed = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return {"research_summary": "NO_EVIDENCE_FOUND"}
    return parsed if isinstance(parsed, dict) else {"research_summary": "NO_EVIDENCE_FOUND"}


def verify_conflict_flag(output, document_ids):
    """BRD 8: a conflict is never silently merged. Backstop for a model that forgets to say so."""
    table = output.get("comparison_table") or []
    table_conflict = any(str(row.get("note", "")).strip().upper() == "CONFLICT" for row in table)
    open_issues = list(output.get("open_issues") or [])
    if len(set(document_ids)) >= 2 and not table:
        open_issues.append(
            "Evidence was drawn from multiple approved documents that were not directly compared by the model - "
            "the reviewer should confirm they agree."
        )
    output["conflict_flagged"] = bool(output.get("conflict_flagged")) or table_conflict
    output["open_issues"] = open_issues
    return output


def _fallback(tenant, user, question, issue, mode):
    pack = EvidencePack.objects.create(
        tenant=tenant, user=user, question=question, research_summary=NO_EVIDENCE_FALLBACK, open_issues=[issue],
        is_fallback=True, retrieval_mode=mode, disclaimer=DISCLAIMER_TEXT,
    )
    return serialise(pack)


def serialise(pack):
    return {
        "id": str(pack.id), "question": pack.question, "research_summary": pack.research_summary,
        "relevant_rulings": pack.relevant_rulings, "relevant_standards": pack.relevant_standards,
        "key_evidence_excerpts": pack.key_evidence_excerpts, "comparison_table": pack.comparison_table,
        "open_issues": pack.open_issues, "citations": pack.citations, "conflict_flagged": pack.conflict_flagged,
        "disclaimer": pack.disclaimer, "review_status": pack.review_status, "is_fallback": pack.is_fallback,
        "retrieval_mode": pack.retrieval_mode,
    }


def ask(tenant, user, question, filters=None):
    filters = filters or {}
    retrieved, mode = retrieve(tenant, question, filters)
    if not retrieved:
        return _fallback(tenant, user, question, "No matching approved evidence was found for this query.", mode)

    blocks = [
        f"[document_id={r.document.id}] {r.document.document_name} (v{r.document.version}, {r.document.approval_status}, "
        f"section={r.chunk.section_label or 'n/a'}, page={r.chunk.page_number or 'n/a'}):\n{r.chunk.text}"
        for r in retrieved
    ]
    output = _draft(question, blocks)
    if output.get("research_summary") == "NO_EVIDENCE_FOUND" or not str(output.get("research_summary") or "").strip():
        return _fallback(tenant, user, question, "Retrieved evidence did not directly address the question.", mode)

    citation_by_doc = {str(r.document.id): _citation(r) for r in retrieved}
    excerpts = []
    for e in output.get("key_evidence_excerpts") or []:
        cite = citation_by_doc.get(str(e.get("document_id")))
        if cite is not None:  # an excerpt that cites a document that was not retrieved is dropped, never trusted
            excerpts.append({"document_id": cite["document_id"], "document_name": e.get("document_name") or cite["document_name"],
                             "excerpt": e.get("excerpt", ""), "citation": cite})
    rows = []
    for row in output.get("comparison_table") or []:
        a, b = citation_by_doc.get(str(row.get("source_a_document_id"))), citation_by_doc.get(str(row.get("source_b_document_id")))
        if a and b:
            rows.append({"topic": row.get("topic", ""), "source_a": row.get("source_a", ""), "source_a_citation": a,
                         "source_b": row.get("source_b", ""), "source_b_citation": b, "note": row.get("note")})
    output["comparison_table"] = rows
    output = verify_conflict_flag(output, [str(r.document.id) for r in retrieved])

    pack = EvidencePack.objects.create(
        tenant=tenant, user=user, question=question, research_summary=output["research_summary"],
        relevant_rulings=list(output.get("relevant_rulings") or []), relevant_standards=list(output.get("relevant_standards") or []),
        key_evidence_excerpts=excerpts, comparison_table=rows, open_issues=output["open_issues"],
        citations=list(citation_by_doc.values()), conflict_flagged=output["conflict_flagged"], retrieval_mode=mode,
        disclaimer=DISCLAIMER_TEXT, review_status=ReviewStatus.HUMAN_REVIEW_REQUIRED,  # always starts here
    )
    return serialise(pack)
