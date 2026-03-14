import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.base import AppRole


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    org_name: str = Field(min_length=1, max_length=255)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    role: AppRole
    full_name: str
    avatar_url: str | None = None
    email: str | None = None  # Populated from Supabase Auth, not the profile table


class AuthenticatedUser(BaseModel):
    """Internal model representing the current authenticated user."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: AppRole
    email: str
