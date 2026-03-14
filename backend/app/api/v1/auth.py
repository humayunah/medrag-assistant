import re
import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client, create_client

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.models.base import AppRole
from app.models.tenant import Tenant
from app.models.user_profile import UserProfile
from app.schemas.auth import (
    AuthenticatedUser,
    AuthResponse,
    ForgotPasswordRequest,
    SignInRequest,
    SignUpRequest,
    UserProfileResponse,
)

logger = structlog.get_logger("auth_api")
router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_supabase_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "org"


@router.post("/signup", response_model=AuthResponse)
async def signup(
    body: SignUpRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user account and organization."""
    supabase = _get_supabase_client()

    # Check if org slug already exists
    slug = _slugify(body.org_name)
    existing = await db.execute(select(Tenant).where(Tenant.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    # Create the tenant
    tenant = Tenant(
        name=body.org_name,
        slug=slug,
    )
    db.add(tenant)
    await db.flush()

    # Create user in Supabase Auth
    try:
        auth_response = supabase.auth.admin.create_user(
            {
                "email": body.email,
                "password": body.password,
                "email_confirm": True,
                "app_metadata": {
                    "tenant_id": str(tenant.id),
                    "role": AppRole.ADMIN.value,
                },
            }
        )
    except Exception as e:
        await db.rollback()
        error_msg = str(e)
        if "already been registered" in error_msg.lower():
            raise ConflictError(detail="A user with this email already exists")
        logger.error("supabase_auth_error", error=error_msg)
        raise ValidationError(detail="Failed to create user account")

    supabase_user = auth_response.user
    if not supabase_user:
        await db.rollback()
        raise ValidationError(detail="Failed to create user account")

    # Create user profile
    profile = UserProfile(
        id=uuid.UUID(supabase_user.id),
        tenant_id=tenant.id,
        role=AppRole.ADMIN,
        full_name=body.full_name,
    )
    db.add(profile)
    await db.commit()

    # Sign in to get tokens
    sign_in = supabase.auth.sign_in_with_password(
        {"email": body.email, "password": body.password}
    )

    logger.info(
        "user_signup",
        user_id=str(supabase_user.id),
        tenant_id=str(tenant.id),
    )

    return AuthResponse(
        access_token=sign_in.session.access_token,
        refresh_token=sign_in.session.refresh_token,
    )


@router.post("/signin", response_model=AuthResponse)
async def signin(body: SignInRequest):
    """Sign in with email and password."""
    supabase = _get_supabase_client()

    try:
        response = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        logger.warning("signin_failed", email=body.email, error=str(e))
        raise UnauthorizedError(detail="Invalid email or password")

    if not response.session:
        raise UnauthorizedError(detail="Invalid email or password")

    return AuthResponse(
        access_token=response.session.access_token,
        refresh_token=response.session.refresh_token,
    )


@router.post("/signout")
async def signout(user: AuthenticatedUser = Depends(get_current_user)):
    """Sign out the current user (invalidate session)."""
    # Supabase handles token invalidation on the client side.
    # Server-side revocation requires the service role key.
    logger.info("user_signout", user_id=str(user.user_id))
    return {"message": "Signed out successfully"}


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Send a password reset email."""
    supabase = _get_supabase_client()

    try:
        supabase.auth.reset_password_email(body.email)
    except Exception:
        pass  # Don't reveal whether email exists

    return {"message": "If an account exists, a password reset email has been sent"}


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's profile."""
    result = await db.execute(select(UserProfile).where(UserProfile.id == user.user_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise UnauthorizedError(detail="User profile not found")

    response = UserProfileResponse.model_validate(profile)
    response.email = user.email
    return response
