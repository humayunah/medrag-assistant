"""Document management endpoints."""

from __future__ import annotations

import asyncio
import uuid

import structlog
from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_permission
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.models.base import DocumentStatus
from app.models.document import Document
from app.schemas.auth import AuthenticatedUser
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.services.document_processor import process_document

logger = structlog.get_logger("documents_api")
router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
}


@router.post("/upload", response_model=DocumentResponse, status_code=202)
async def upload_document(
    file: UploadFile,
    user: AuthenticatedUser = Depends(require_permission("documents.upload")),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document for processing.

    Validates the file, stores metadata, and spawns a background processing task.
    Returns 202 Accepted immediately.
    """
    # Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            detail=f"Unsupported file type: {file.content_type}. "
            f"Allowed: {', '.join(ALLOWED_MIME_TYPES)}"
        )

    # Read and validate file size
    file_bytes = await file.read()
    if len(file_bytes) > settings.max_file_size_bytes:
        raise ValidationError(
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
        )

    if len(file_bytes) == 0:
        raise ValidationError(detail="Empty file")

    # Create document record
    doc = Document(
        tenant_id=user.tenant_id,
        uploaded_by=user.user_id,
        filename=file.filename or "unnamed",
        storage_path=f"documents/{user.tenant_id}/{uuid.uuid4()}/{file.filename}",
        mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(file_bytes),
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info(
        "document_uploaded",
        document_id=str(doc.id),
        filename=doc.filename,
        size_bytes=doc.file_size_bytes,
    )

    # Spawn background processing
    asyncio.create_task(process_document(doc.id, file_bytes))

    return DocumentResponse.model_validate(doc)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    status: DocumentStatus | None = None,
    user: AuthenticatedUser = Depends(require_permission("documents.view")),
    db: AsyncSession = Depends(get_db),
):
    """List documents in the organization with optional filtering."""
    base_query = select(Document).where(Document.tenant_id == user.tenant_id)

    if search:
        base_query = base_query.where(Document.filename.ilike(f"%{search}%"))
    if status:
        base_query = base_query.where(Document.status == status)

    # Count
    count_q = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    docs_q = (
        base_query.order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(docs_q)
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_permission("documents.view")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single document's details."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document")
    return DocumentResponse.model_validate(doc)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    user: AuthenticatedUser = Depends(require_permission("documents.delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its chunks.

    Admins can delete any document. Doctors/Nurses can delete their own.
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("Document")

    # Non-admin users can only delete their own documents
    if user.role.value not in ("admin",) and doc.uploaded_by != user.user_id:
        raise ForbiddenError(detail="You can only delete documents you uploaded")

    await db.delete(doc)
    await db.commit()

    logger.info(
        "document_deleted",
        document_id=str(document_id),
        deleted_by=str(user.user_id),
    )
