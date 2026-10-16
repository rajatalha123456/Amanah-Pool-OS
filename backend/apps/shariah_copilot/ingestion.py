"""Reading a source file, cutting it into clause-level chunks and storing them with their embeddings (BRD 9)."""

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db import transaction

from . import embeddings
from .models import CopilotChunk, CopilotDocument

logger = logging.getLogger("apps")

CLAUSE_PATTERN = re.compile(r"^\s*((?:Section|Clause|Article)?\s*\d+(?:\.\d+)*[\.\)]?\s+.{0,80})", re.MULTILINE)
FALLBACK_CHUNK_CHARS = 1200
FALLBACK_OVERLAP_CHARS = 150
SUPPORTED = (".pdf", ".docx", ".txt", ".md")


@dataclass
class RawChunk:
    text: str
    section_label: str
    page_number: int


class UnsupportedFile(ValueError):
    pass


def load_pages(path):
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        pages = []
        for number, page in enumerate(PdfReader(str(path)).pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append((number, text))
        return pages
    if suffix == ".docx":
        import docx

        text = "\n".join(p.text for p in docx.Document(str(path)).paragraphs if p.text.strip())
        return [(1, text)]
    if suffix in (".txt", ".md"):
        return [(1, Path(path).read_text(encoding="utf-8", errors="ignore"))]
    raise UnsupportedFile(f"Unsupported file type '{suffix}'. Use PDF, DOCX, TXT or MD.")


def _split_by_clause(text):
    matches = list(CLAUSE_PATTERN.finditer(text))
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.start():end].strip()
        if block:
            out.append((m.group(1).strip()[:60], block))
    return out


def _split_fixed(text):
    text, chunks, start = text.strip(), [], 0
    while start < len(text):
        end = min(start + FALLBACK_CHUNK_CHARS, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = end - FALLBACK_OVERLAP_CHARS
    return [c for c in chunks if c]


def chunk_pages(pages):
    chunks = []
    for page_number, text in pages:
        by_clause = _split_by_clause(text)
        if by_clause:
            chunks += [RawChunk(t.strip(), label, page_number) for label, t in by_clause if t.strip()]
        else:
            chunks += [RawChunk(t, "", page_number) for t in _split_fixed(text)]
    return chunks


def store_source_file(tenant, uploaded):
    suffix = Path(uploaded.name).suffix.lower()
    if suffix not in SUPPORTED:
        raise UnsupportedFile(f"Unsupported file type '{suffix}'. Use PDF, DOCX, TXT or MD.")
    data = uploaded.read()
    digest = hashlib.sha256(data).hexdigest()
    folder = Path(settings.COPILOT_RAW_DOCS_DIR) / str(tenant.code)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{digest[:16]}_{Path(uploaded.name).name}"
    path.write_bytes(data)
    return path, digest


@transaction.atomic
def ingest(*, tenant, user, uploaded, metadata):
    path, digest = store_source_file(tenant, uploaded)
    raw = chunk_pages(load_pages(path))
    if not raw:
        raise UnsupportedFile("No readable text was found in the file (a scanned image needs OCR first).")

    document = CopilotDocument.objects.create(
        tenant=tenant, uploaded_by=user, source_file_path=str(path), content_hash=digest, **metadata
    )
    prior = metadata.get("supersedes")
    if prior is not None:
        CopilotDocument.objects.filter(pk=prior.pk).update(is_current_version=False)

    vectors = None
    try:
        vectors = embeddings.embed([c.text for c in raw])
    except embeddings.EmbeddingsUnavailable as exc:
        logger.warning("Document %s stored without embeddings: %s", document.id, exc)
    name = embeddings.model_name() if vectors is not None else ""
    CopilotChunk.objects.bulk_create([
        CopilotChunk(
            tenant=tenant, document=document, chunk_index=i, section_label=c.section_label, page_number=c.page_number,
            text=c.text, embedding=embeddings.to_bytes(vectors[i]) if vectors is not None else None, embedding_model=name,
        )
        for i, c in enumerate(raw)
    ])
    return document
