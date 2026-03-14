import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.base import AppRole, InvitationStatus


class InvitationCreate(BaseModel):
    email: EmailStr
    role: AppRole


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: AppRole
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime
