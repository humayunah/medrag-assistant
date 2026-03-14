"""RAG query and conversation endpoints."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_permission
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.conversation import Conversation
from app.models.query_message import QueryMessage
from app.schemas.auth import AuthenticatedUser
from app.schemas.query import (
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
    QueryRequest,
    QueryResponse,
)
from app.services.rag_service import RAGService

logger = structlog.get_logger("queries_api")
router = APIRouter(tags=["Queries"])

# Module-level singleton — created once, reused across requests
_rag_service: RAGService | None = None


def _get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


@router.post("/queries", response_model=QueryResponse)
async def execute_query(
    body: QueryRequest,
    user: AuthenticatedUser = Depends(require_permission("queries.execute")),
    db: AsyncSession = Depends(get_db),
):
    """Execute a RAG query against the organization's documents."""
    rag = _get_rag_service()
    response = await rag.query(
        db=db,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        query_text=body.query,
        conversation_id=body.conversation_id,
        document_ids=body.document_ids,
    )
    return response


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's conversations."""
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.tenant_id == user.tenant_id,
            Conversation.user_id == user.user_id,
        )
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()

    return ConversationListResponse(
        conversations=[ConversationResponse.model_validate(c) for c in conversations],
        total=len(conversations),
    )


@router.get(
    "/conversations/{conversation_id}/messages", response_model=list[MessageResponse]
)
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a conversation."""
    # Verify conversation belongs to user
    conv = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user.tenant_id,
            Conversation.user_id == user.user_id,
        )
    )
    if not conv.scalar_one_or_none():
        raise NotFoundError("Conversation")

    result = await db.execute(
        select(QueryMessage)
        .where(QueryMessage.conversation_id == conversation_id)
        .order_by(QueryMessage.created_at)
    )
    messages = result.scalars().all()
    return [MessageResponse.model_validate(m) for m in messages]


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == user.tenant_id,
            Conversation.user_id == user.user_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise NotFoundError("Conversation")

    await db.delete(conv)
    await db.commit()

    logger.info("conversation_deleted", conversation_id=str(conversation_id))
