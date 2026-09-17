"""
Thin HTTP client for the Shariah Policy Copilot service (separate FastAPI app).

The Copilot service trusts the Django backend as a single internal caller
(X-Internal-Key) and takes the acting user's identity as headers rather than
re-authenticating them - see its app/utils/security.py.
"""

import requests
from django.conf import settings

ROLE_MAP = {
    "shariah_board": "shariah_reviewer",
    "shariah_secretariat": "shariah_officer",
    "product_manager": "product",
    "risk_compliance": "compliance",
}


class ShariahCopilotUnavailableError(Exception):
    """The Copilot service could not be reached (connection error or timeout)."""


class ShariahCopilotError(Exception):
    """Wraps a 4xx/5xx response from the service with its detail message."""

    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Shariah Copilot returned {status_code}: {detail}")


def _headers(user, tenant_code):
    return {
        "X-Internal-Key": settings.SHARIAH_COPILOT_INTERNAL_KEY,
        "X-User-Id": str(user.id),
        "X-User-Role": ROLE_MAP.get(user.role, "shariah_researcher"),
        "X-Tenant-Id": tenant_code,
    }


def _call(method, path, user, tenant_code, timeout=30, **kwargs):
    try:
        response = requests.request(
            method,
            f"{settings.SHARIAH_COPILOT_BASE_URL}{path}",
            headers=_headers(user, tenant_code),
            timeout=timeout,
            **kwargs,
        )
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        raise ShariahCopilotUnavailableError(str(exc)) from exc

    if not response.ok:
        raise ShariahCopilotError(response.status_code, response.text)

    return response.json() if response.content else None


def upload_document(user, tenant_code, file, metadata: dict) -> dict:
    # Ingestion (chunking + embedding into ChromaDB) is CPU-bound and can take
    # well over 30s, especially on the first call after the Copilot process
    # starts (sentence-transformers loading the embedding model into memory).
    files = {"file": (file.name, file.read(), file.content_type)}
    return _call(
        "POST",
        "/documents/upload",
        user,
        tenant_code,
        timeout=90,
        files=files,
        data=metadata,
    )


def list_documents(user, tenant_code, params: dict) -> list:
    return _call("GET", "/documents", user, tenant_code, params=params)


def ask_question(user, tenant_code, question: str, filters: dict) -> dict:
    # The LLM call behind this endpoint routinely takes 20-30s+, longer than
    # the default timeout used for the other (near-instant) Copilot calls.
    return _call(
        "POST",
        "/query/ask",
        user,
        tenant_code,
        timeout=90,
        json={"user_id": str(user.id), "question": question, "filters": filters},
    )


def submit_review(user, tenant_code, evidence_pack_id: str, approve: bool) -> dict:
    return _call(
        "POST",
        f"/review/{evidence_pack_id}",
        user,
        tenant_code,
        json={"approve": approve},
    )
