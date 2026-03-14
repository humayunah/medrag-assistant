import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_permission
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.tenant import Tenant
from app.schemas.auth import AuthenticatedUser
from app.schemas.tenant import TenantResponse, TenantUpdate

logger = structlog.get_logger("tenants_api")
router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's organization."""
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Organization")
    return TenantResponse.model_validate(tenant)


@router.patch("/me", response_model=TenantResponse)
async def update_my_tenant(
    body: TenantUpdate,
    user: AuthenticatedUser = Depends(require_permission("org.settings")),
    db: AsyncSession = Depends(get_db),
):
    """Update organization settings (Admin only)."""
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Organization")

    if body.name is not None:
        tenant.name = body.name
    if body.settings is not None:
        tenant.settings = body.settings

    await db.commit()
    await db.refresh(tenant)

    logger.info("tenant_updated", tenant_id=str(tenant.id))
    return TenantResponse.model_validate(tenant)
