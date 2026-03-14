import secrets
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client

from app.core.auth import require_permission
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.base import InvitationStatus
from app.models.invitation import Invitation
from app.models.user_profile import UserProfile
from app.schemas.auth import AuthenticatedUser
from app.schemas.invitation import InvitationCreate, InvitationResponse

logger = structlog.get_logger("invitations_api")
router = APIRouter(prefix="/invitations", tags=["Invitations"])

INVITATION_EXPIRY_DAYS = 7


@router.post("", response_model=InvitationResponse, status_code=201)
async def create_invitation(
    body: InvitationCreate,
    user: AuthenticatedUser = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Invite a user to the organization (Admin only)."""
    # Check if user already exists in this org
    existing_profile = await db.execute(
        select(UserProfile)
        .join(UserProfile.tenant)
        .where(UserProfile.tenant_id == user.tenant_id)
    )
    for profile in existing_profile.scalars():
        # We'd need to check email via Supabase Auth, but for now check invitations
        pass

    # Check for existing pending invitation
    existing_invite = await db.execute(
        select(Invitation).where(
            Invitation.tenant_id == user.tenant_id,
            Invitation.email == body.email,
            Invitation.status == InvitationStatus.PENDING,
        )
    )
    if existing_invite.scalar_one_or_none():
        raise ConflictError(detail="A pending invitation already exists for this email")

    invitation = Invitation(
        tenant_id=user.tenant_id,
        invited_by=user.user_id,
        email=body.email,
        role=body.role,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS),
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    logger.info(
        "invitation_created",
        invitation_id=str(invitation.id),
        email=body.email,
        role=body.role.value,
    )

    return InvitationResponse.model_validate(invitation)


@router.get("/{token}")
async def validate_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Validate an invitation link and return its details."""
    result = await db.execute(select(Invitation).where(Invitation.token == token))
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise NotFoundError("Invitation")

    if invitation.status != InvitationStatus.PENDING:
        raise ValidationError(detail=f"Invitation is {invitation.status.value}")

    if invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = InvitationStatus.EXPIRED
        await db.commit()
        raise ValidationError(detail="Invitation has expired")

    return InvitationResponse.model_validate(invitation)


@router.post("/{token}/accept")
async def accept_invitation(
    token: str,
    password: str,
    full_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Accept an invitation and create user account."""
    result = await db.execute(select(Invitation).where(Invitation.token == token))
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise NotFoundError("Invitation")

    if invitation.status != InvitationStatus.PENDING:
        raise ValidationError(detail=f"Invitation is {invitation.status.value}")

    if invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = InvitationStatus.EXPIRED
        await db.commit()
        raise ValidationError(detail="Invitation has expired")

    # Create user in Supabase Auth
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    try:
        auth_response = supabase.auth.admin.create_user(
            {
                "email": invitation.email,
                "password": password,
                "email_confirm": True,
                "app_metadata": {
                    "tenant_id": str(invitation.tenant_id),
                    "role": invitation.role.value,
                },
            }
        )
    except Exception as e:
        error_msg = str(e)
        if "already been registered" in error_msg.lower():
            raise ConflictError(detail="A user with this email already exists")
        logger.error("supabase_auth_error", error=error_msg)
        raise ValidationError(detail="Failed to create user account")

    supabase_user = auth_response.user
    if not supabase_user:
        raise ValidationError(detail="Failed to create user account")

    # Create user profile
    profile = UserProfile(
        id=uuid.UUID(supabase_user.id),
        tenant_id=invitation.tenant_id,
        role=invitation.role,
        full_name=full_name,
    )
    db.add(profile)

    # Mark invitation as accepted
    invitation.status = InvitationStatus.ACCEPTED
    await db.commit()

    logger.info(
        "invitation_accepted",
        invitation_id=str(invitation.id),
        user_id=str(supabase_user.id),
    )

    # Sign in to get tokens
    sign_in = supabase.auth.sign_in_with_password(
        {"email": invitation.email, "password": password}
    )

    return {
        "access_token": sign_in.session.access_token,
        "refresh_token": sign_in.session.refresh_token,
        "token_type": "bearer",
    }


@router.delete("/{invitation_id}", status_code=204)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_permission("users.manage")),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a pending invitation (Admin only)."""
    result = await db.execute(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.tenant_id == user.tenant_id,
        )
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise NotFoundError("Invitation")

    if invitation.status != InvitationStatus.PENDING:
        raise ValidationError(detail="Can only revoke pending invitations")

    invitation.status = InvitationStatus.REVOKED
    await db.commit()

    logger.info("invitation_revoked", invitation_id=str(invitation_id))
