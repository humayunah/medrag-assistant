import uuid

import structlog
from fastapi import Depends, Header
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.models.base import AppRole
from app.schemas.auth import AuthenticatedUser

logger = structlog.get_logger("auth")

# Permission map: role -> set of permissions
ROLE_PERMISSIONS: dict[AppRole, set[str]] = {
    AppRole.ADMIN: {
        "documents.upload",
        "documents.delete",
        "documents.view",
        "queries.execute",
        "audit.view",
        "users.manage",
        "org.settings",
        "llm.configure",
    },
    AppRole.DOCTOR: {
        "documents.upload",
        "documents.delete",
        "documents.view",
        "queries.execute",
    },
    AppRole.NURSE: {
        "documents.upload",
        "documents.delete",
        "documents.view",
        "queries.execute",
    },
    AppRole.STAFF: {
        "documents.view",
        "queries.execute",
    },
}


def has_permission(role: AppRole, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
) -> AuthenticatedUser:
    """Extract and verify the current user from the JWT token.

    The JWT is issued by Supabase Auth and contains custom claims
    for tenant_id and user_role set during signup/role assignment.
    """
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError(detail="Invalid authorization header format")

    token = authorization.removeprefix("Bearer ")

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as e:
        logger.warning("jwt_decode_failed", error=str(e))
        raise UnauthorizedError(detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError(detail="Token missing subject claim")

    # Custom claims added via Supabase Auth hooks or custom JWT
    app_metadata = payload.get("app_metadata", {})
    tenant_id = app_metadata.get("tenant_id")
    role_str = app_metadata.get("role", "staff")

    if not tenant_id:
        raise UnauthorizedError(detail="Token missing tenant context")

    try:
        role = AppRole(role_str)
    except ValueError:
        role = AppRole.STAFF

    return AuthenticatedUser(
        user_id=uuid.UUID(user_id),
        tenant_id=uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
        role=role,
        email=payload.get("email", ""),
    )


def require_permission(permission: str):
    """Dependency factory that enforces a specific permission."""

    async def checker(
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not has_permission(user.role, permission):
            raise ForbiddenError(
                detail=f"Permission '{permission}' required. Your role: {user.role.value}"
            )
        return user

    return checker
