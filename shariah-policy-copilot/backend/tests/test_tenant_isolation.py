import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mktemp(suffix='.db')}")
os.environ.setdefault("VECTOR_STORE_DIR", tempfile.mkdtemp())

from app.database import SessionLocal, init_db  # noqa: E402
from app.models.document import ApprovalStatus, Document  # noqa: E402
from app.retrieval.hybrid_retriever import _candidate_documents  # noqa: E402
from app.schemas.query import QueryFilters  # noqa: E402


def test_candidate_documents_are_scoped_to_tenant():
    init_db()
    db = SessionLocal()
    try:
        db.add_all([
            Document(
                tenant_id="tenant-a",
                document_name="A",
                document_type="policy",
                approval_status=ApprovalStatus.APPROVED,
            ),
            Document(
                tenant_id="tenant-b",
                document_name="B",
                document_type="policy",
                approval_status=ApprovalStatus.APPROVED,
            ),
        ])
        db.commit()

        results = _candidate_documents(db, "tenant-a", QueryFilters())

        assert [document.document_name for document in results] == ["A"]
    finally:
        db.close()