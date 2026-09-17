import json
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_query(
    db: Session,
    tenant_id: str,
    user_id: str,
    question: str,
    retrieved_document_ids: List[str],
    answer_summary: str,
    evidence_pack_id: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        query_text=question,
        retrieved_document_ids=json.dumps(retrieved_document_ids),
        ai_answer_summary=answer_summary,
        evidence_pack_id=evidence_pack_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def log_review_action(db: Session, tenant_id: str, evidence_pack_id: str, reviewer_id: str, action: str) -> None:
    entry = (
        db.query(AuditLog)
        .filter(AuditLog.tenant_id == tenant_id, AuditLog.evidence_pack_id == evidence_pack_id)
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    if entry:
        entry.reviewer_action = action
        db.commit()
