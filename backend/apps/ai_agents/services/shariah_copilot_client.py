"""
Adapter between the AI views and the Shariah Policy Copilot, which now runs inside this service (apps.shariah_copilot).

It keeps the old function names and error types so the views and tests are unchanged, but nothing here is a network call
any more: no second service, no shared key, and the same tenant scoping and audit log as the rest of the platform.
"""

from apps.shariah_copilot import service
from apps.shariah_copilot.llm import LLMError, LLMUnavailable

ROLE_MAP = {
    "shariah_board": "shariah_reviewer",
    "shariah_secretariat": "shariah_officer",
    "product_manager": "product",
    "risk_compliance": "compliance",
}


class ShariahCopilotUnavailableError(Exception):
    """The language model behind the copilot is not configured or cannot be reached."""


class ShariahCopilotError(Exception):
    """A refused or failed request, with an HTTP-style status and a plain message."""

    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Shariah Copilot returned {status_code}: {detail}")


def _run(call, *args):
    try:
        return call(*args)
    except service.CopilotRefused as exc:
        raise ShariahCopilotError(exc.status_code, exc.detail) from exc
    except LLMUnavailable as exc:
        raise ShariahCopilotUnavailableError(str(exc)) from exc
    except LLMError as exc:
        raise ShariahCopilotError(502, f"Failed to generate an answer: {exc.detail}") from exc


def upload_document(user, tenant_code, file, metadata: dict) -> dict:
    return _run(service.upload_document, user, file, metadata)


def approve_document(user, tenant_code, document_id: str, approve: bool = True) -> dict:
    return _run(service.approve_document, user, document_id, approve)


def list_documents(user, tenant_code, params: dict) -> list:
    return _run(service.list_documents, user, params)


def ask_question(user, tenant_code, question: str, filters: dict) -> dict:
    return _run(service.ask_question, user, question, filters)


def submit_review(user, tenant_code, evidence_pack_id: str, approve: bool) -> dict:
    return _run(service.submit_review, user, evidence_pack_id, approve)
