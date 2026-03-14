import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = structlog.get_logger("audit")


async def log_action(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Record an audit event. Never include PHI in details."""
    entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details or {},
    )
    db.add(entry)
    await db.flush()  # Don't commit — let the caller's transaction handle it

    logger.info(
        "audit_logged",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=str(tenant_id),
    )


async def log_from_request(
    db: AsyncSession,
    request,  # FastAPI Request
    user,  # AuthenticatedUser
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Log audit event extracting IP/UA from request and tenant/user from auth."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    await log_action(
        db=db,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
    )
