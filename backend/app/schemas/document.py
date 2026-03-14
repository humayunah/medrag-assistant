import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.base import DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    uploaded_by: uuid.UUID | None = None
    filename: str
    mime_type: str
    file_size_bytes: int
    status: DocumentStatus
    ocr_confidence: float | None = None
    page_count: int | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int
