import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_permission
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.schemas.auth import AuthenticatedUser

logger = structlog.get_logger("audit_api")
router = APIRouter(prefix="/audit-logs", tags=["Audit"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    details: dict | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: str | None = Query(None, description="Filter by action type"),
    user_id: uuid.UUID | None = Query(None, description="Filter by user"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    from_date: datetime | None = Query(None, description="Start of date range"),
    to_date: datetime | None = Query(None, description="End of date range"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user: AuthenticatedUser = Depends(require_permission("audit.view")),
    db: AsyncSession = Depends(get_db),
):
    """List audit logs for the current tenant with optional filters."""
    base = select(AuditLog).where(AuditLog.tenant_id == user.tenant_id)

    if action:
        base = base.where(AuditLog.action == action)
    if user_id:
        base = base.where(AuditLog.user_id == user_id)
    if resource_type:
        base = base.where(AuditLog.resource_type == resource_type)
    if from_date:
        base = base.where(AuditLog.created_at >= from_date)
    if to_date:
        base = base.where(AuditLog.created_at <= to_date)

    # Total count
    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar() or 0

    # Paginated results
    offset = (page - 1) * page_size
    rows_result = await db.execute(
        base.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    )
    items = rows_result.scalars().all()

    logger.info(
        "audit_logs_listed",
        tenant_id=str(user.tenant_id),
        total=total,
        page=page,
    )

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
