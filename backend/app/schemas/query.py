import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    conversation_id: uuid.UUID | None = None  # None = new conversation
    document_ids: list[uuid.UUID] | None = None  # None = search all org documents


class CitationSource(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    page_number: int | None = None
    section_title: str | None = None
    content_preview: str
    similarity: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationSource]
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    llm_provider: str
    has_insufficient_info: bool = False
    cached: bool = False


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    citations: list | None = None
    llm_provider: str | None = None
    created_at: datetime
