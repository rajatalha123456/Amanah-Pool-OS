"""Authentication and tenant context for calls from the trusted Django backend."""
from dataclasses import dataclass
from enum import Enum

from fastapi import Header, HTTPException

from app.config import settings


class Role(str, Enum):
    SHARIAH_OFFICER = "shariah_officer"
    SHARIAH_RESEARCHER = "shariah_researcher"
    SHARIAH_REVIEWER = "shariah_reviewer"  # only role allowed to approve/reject (FR-18)
    PRODUCT = "product"
    COMPLIANCE = "compliance"
    AUDITOR = "auditor"


@dataclass
class CurrentUser:
    user_id: str
    role: Role
    tenant_id: str


def get_current_user(
    x_internal_key: str | None = Header(None, alias="X-Internal-Key"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_role: str | None = Header(None, alias="X-User-Role"),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-Id"),
) -> CurrentUser:
    if not settings.internal_service_key or x_internal_key != settings.internal_service_key:
        raise HTTPException(status_code=401, detail="Invalid internal service key")
    if not x_user_id or not x_user_role or not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-User-Id, X-User-Role, and X-Tenant-Id are required")

    try:
        role = Role(x_user_role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown role: {x_user_role}")
    return CurrentUser(user_id=x_user_id, role=role, tenant_id=x_tenant_id)

def require_reviewer(user: CurrentUser) -> None:
    if user.role != Role.SHARIAH_REVIEWER:
        raise HTTPException(status_code=403, detail="Only a Shariah reviewer can approve/reject evidence packs.")
