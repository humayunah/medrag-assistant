"""RAG query pipeline.

Implements hybrid retrieval (pgvector cosine similarity + tsvector BM25),
Reciprocal Rank Fusion (RRF) for result merging, conversation context,
prompt construction with citation instructions, and response caching.
"""

from __future__ import annotations

import hashlib
import uuid

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.query_cache import QueryCache
from app.models.query_message import QueryMessage
from app.providers.router import ProviderRouter
from app.schemas.query import CitationSource, QueryResponse
from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger("rag_service")

# Retrieval parameters
_VECTOR_TOP_K = 20
_BM25_TOP_K = 20
_FINAL_TOP_K = 8
_SIMILARITY_THRESHOLD = 0.65
_RRF_K = 60  # RRF constant
_CONTEXT_MESSAGES = 3  # Number of previous exchanges to include


class RAGService:
    """Orchestrates the full RAG query pipeline."""

    def __init__(self) -> None:
        self._embedding_service = EmbeddingService()
        self._provider_router = ProviderRouter()

    async def close(self) -> None:
        await self._embedding_service.close()

    async def query(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        query_text: str,
        conversation_id: uuid.UUID | None = None,
        document_ids: list[uuid.UUID] | None = None,
    ) -> QueryResponse:
        """Execute a RAG query and return a citation-backed answer."""
        import time

        start = time.monotonic()

        # Check cache first
        cache_hit = await self._check_cache(db, tenant_id, query_text)
        if cache_hit:
            # Still create conversation/message for history
            conv_id, msg_id = await self._persist_exchange(
                db,
                tenant_id,
                user_id,
                conversation_id,
                query_text,
                cache_hit["content"],
                cache_hit["citations"],
                "cache",
                0,
                0,
                0.0,
            )
            return QueryResponse(
                answer=cache_hit["content"],
                citations=cache_hit["citations"],
                conversation_id=conv_id,
                message_id=msg_id,
                llm_provider="cache",
                cached=True,
            )

        # Step 1: Embed the query (graceful fallback to BM25-only)
        query_embedding = None
        try:
            query_embedding = await self._embedding_service.embed_query(query_text)
        except Exception as exc:
            logger.warning("embedding_failed_fallback_bm25", error=str(exc))

        # Step 2: Hybrid retrieval (or BM25-only if embedding failed)
        vector_results = []
        if query_embedding is not None:
            vector_results = await self._vector_search(
                db, tenant_id, query_embedding, document_ids
            )
        bm25_results = await self._bm25_search(db, tenant_id, query_text, document_ids)

        # Step 3: RRF fusion
        fused = self._rrf_fusion(vector_results, bm25_results)

        # Step 4: Quality gate (skip threshold for BM25-only since RRF scores
        # are much smaller than cosine similarity scores)
        if vector_results:
            filtered = [r for r in fused if r["score"] >= _SIMILARITY_THRESHOLD]
        else:
            filtered = fused  # BM25 tsquery already filters for relevance
        top_chunks = filtered[:_FINAL_TOP_K]

        # Step 5: Build conversation context
        history = await self._get_conversation_history(db, conversation_id)

        # Step 6: Construct prompt
        has_context = len(top_chunks) > 0
        messages = self._build_prompt(query_text, top_chunks, history, has_context)

        # Step 7: Generate answer via LLM
        llm_response = await self._provider_router.complete(messages)

        # Step 8: Build citations
        citations = self._build_citations(top_chunks)

        # Step 9: Detect insufficient info
        has_insufficient_info = not has_context or _is_insufficient_response(
            llm_response.content
        )

        latency_ms = (time.monotonic() - start) * 1000

        # Step 10: Persist exchange
        conv_id, msg_id = await self._persist_exchange(
            db,
            tenant_id,
            user_id,
            conversation_id,
            query_text,
            llm_response.content,
            citations,
            llm_response.provider,
            llm_response.prompt_tokens,
            llm_response.completion_tokens,
            latency_ms,
        )

        # Step 11: Cache response
        await self._cache_response(
            db, tenant_id, query_text, llm_response.content, citations
        )

        logger.info(
            "rag_query_completed",
            tenant_id=str(tenant_id),
            provider=llm_response.provider,
            chunks_retrieved=len(top_chunks),
            latency_ms=round(latency_ms),
        )

        return QueryResponse(
            answer=llm_response.content,
            citations=citations,
            conversation_id=conv_id,
            message_id=msg_id,
            llm_provider=llm_response.provider,
            has_insufficient_info=has_insufficient_info,
            cached=False,
        )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    async def _vector_search(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        query_embedding: list[float],
        document_ids: list[uuid.UUID] | None,
    ) -> list[dict]:
        """Cosine similarity search via pgvector."""
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        doc_filter = ""
        params: dict = {
            "tenant_id": tenant_id,
            "embedding": embedding_str,
            "limit": _VECTOR_TOP_K,
        }

        if document_ids:
            doc_filter = "AND dc.document_id = ANY(:doc_ids)"
            params["doc_ids"] = document_ids

        query = text(f"""
            SELECT dc.id, dc.document_id, dc.content, dc.page_number,
                   dc.section_title, dc.chunk_index,
                   d.filename,
                   1 - (dc.embedding <=> :embedding::vector) AS similarity
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.tenant_id = :tenant_id
              AND dc.embedding IS NOT NULL
              {doc_filter}
            ORDER BY dc.embedding <=> :embedding::vector
            LIMIT :limit
        """)

        result = await db.execute(query, params)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    async def _bm25_search(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        query_text: str,
        document_ids: list[uuid.UUID] | None,
    ) -> list[dict]:
        """Full-text search via PostgreSQL tsvector/tsquery."""
        doc_filter = ""
        params: dict = {
            "tenant_id": tenant_id,
            "query": query_text,
            "limit": _BM25_TOP_K,
        }

        if document_ids:
            doc_filter = "AND dc.document_id = ANY(:doc_ids)"
            params["doc_ids"] = document_ids

        query = text(f"""
            SELECT dc.id, dc.document_id, dc.content, dc.page_number,
                   dc.section_title, dc.chunk_index,
                   d.filename,
                   ts_rank_cd(dc.search_vector, plainto_tsquery('english', :query)) AS bm25_score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.tenant_id = :tenant_id
              AND dc.search_vector @@ plainto_tsquery('english', :query)
              {doc_filter}
            ORDER BY bm25_score DESC
            LIMIT :limit
        """)

        result = await db.execute(query, params)
        rows = result.mappings().all()
        return [dict(r) for r in rows]

    @staticmethod
    def _rrf_fusion(
        vector_results: list[dict],
        bm25_results: list[dict],
    ) -> list[dict]:
        """Reciprocal Rank Fusion to merge vector and BM25 results."""
        scores: dict[uuid.UUID, float] = {}
        chunk_map: dict[uuid.UUID, dict] = {}

        for rank, row in enumerate(vector_results):
            chunk_id = row["id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (_RRF_K + rank + 1)
            chunk_map[chunk_id] = row

        for rank, row in enumerate(bm25_results):
            chunk_id = row["id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (_RRF_K + rank + 1)
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = row

        # Sort by fused score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [
            {**chunk_map[cid], "score": score}
            for cid, score in ranked
            if cid in chunk_map
        ]

    # ------------------------------------------------------------------
    # Conversation context
    # ------------------------------------------------------------------

    async def _get_conversation_history(
        self, db: AsyncSession, conversation_id: uuid.UUID | None
    ) -> list[dict]:
        """Get the last N message pairs from a conversation."""
        if not conversation_id:
            return []

        result = await db.execute(
            select(QueryMessage)
            .where(QueryMessage.conversation_id == conversation_id)
            .order_by(QueryMessage.created_at.desc())
            .limit(_CONTEXT_MESSAGES * 2)
        )
        messages = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in messages]

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(
        query: str,
        chunks: list[dict],
        history: list[dict],
        has_context: bool,
    ) -> list[dict]:
        """Construct the LLM prompt with system instructions, context, and query."""
        if has_context:
            context_text = "\n\n".join(
                f"[Source {i + 1}] (Document: {c['filename']}, "
                f"Page: {c.get('page_number', 'N/A')}, "
                f"Section: {c.get('section_title', 'N/A')})\n{c['content']}"
                for i, c in enumerate(chunks)
            )

            system = (
                "You are a medical document assistant. Answer questions based ONLY on "
                "the provided document excerpts. Follow these rules strictly:\n\n"
                "1. Base your answer ONLY on the provided sources. Do not use external knowledge.\n"
                "2. Cite sources using [Source N] notation after each claim.\n"
                "3. If the sources do not contain sufficient information to answer, "
                "say 'Based on the available documents, I cannot find sufficient information "
                "to answer this question.' and suggest what additional documents might help.\n"
                "4. Be precise and clinical in your language.\n"
                "5. If multiple sources support a claim, cite all of them.\n"
                "6. Never fabricate or hallucinate information not present in the sources.\n\n"
                f"DOCUMENT EXCERPTS:\n{context_text}"
            )
        else:
            system = (
                "You are a medical document assistant. The user asked a question but "
                "no relevant document excerpts were found in the organization's uploaded "
                "documents. Politely inform them that you could not find relevant information "
                "and suggest they upload relevant documents or rephrase their query."
            )

        messages: list[dict] = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": query})
        return messages

    # ------------------------------------------------------------------
    # Citations
    # ------------------------------------------------------------------

    @staticmethod
    def _build_citations(chunks: list[dict]) -> list[CitationSource]:
        return [
            CitationSource(
                chunk_id=c["id"],
                document_id=c["document_id"],
                document_name=c["filename"],
                page_number=c.get("page_number"),
                section_title=c.get("section_title"),
                content_preview=c["content"][:300],
                similarity=round(float(c.get("similarity", c.get("score", 0))), 4),
            )
            for c in chunks
        ]

    # ------------------------------------------------------------------
    # Caching
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_key(tenant_id: uuid.UUID, query_text: str) -> str:
        normalized = query_text.strip().lower()
        return hashlib.sha256(f"{tenant_id}:{normalized}".encode()).hexdigest()

    async def _check_cache(
        self, db: AsyncSession, tenant_id: uuid.UUID, query_text: str
    ) -> dict | None:
        cache_hash = self._cache_key(tenant_id, query_text)
        result = await db.execute(
            select(QueryCache).where(
                QueryCache.tenant_id == tenant_id,
                QueryCache.query_hash == cache_hash,
                QueryCache.invalidated_at.is_(None),
            )
        )
        cached = result.scalar_one_or_none()
        if not cached:
            return None

        citations = [CitationSource(**c) for c in (cached.citations or [])]
        return {"content": cached.response_content, "citations": citations}

    async def _cache_response(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        query_text: str,
        content: str,
        citations: list[CitationSource],
    ) -> None:
        cache_hash = self._cache_key(tenant_id, query_text)
        cache_entry = QueryCache(
            tenant_id=tenant_id,
            query_hash=cache_hash,
            response_content=content,
            citations=[c.model_dump(mode="json") for c in citations],
        )
        db.add(cache_entry)
        try:
            await db.commit()
        except Exception:
            await db.rollback()  # Duplicate key on race condition — acceptable

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _persist_exchange(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
        query_text: str,
        answer: str,
        citations: list[CitationSource],
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
    ) -> tuple[uuid.UUID, uuid.UUID]:
        """Save user message + assistant response. Create conversation if needed."""
        if conversation_id:
            conv = await db.get(Conversation, conversation_id)
        else:
            conv = None

        if not conv:
            conv = Conversation(
                tenant_id=tenant_id,
                user_id=user_id,
                title=query_text[:100],
            )
            db.add(conv)
            await db.flush()

        # User message
        user_msg = QueryMessage(
            conversation_id=conv.id,
            tenant_id=tenant_id,
            role="user",
            content=query_text,
        )
        db.add(user_msg)

        # Assistant message
        assistant_msg = QueryMessage(
            conversation_id=conv.id,
            tenant_id=tenant_id,
            role="assistant",
            content=answer,
            citations=[c.model_dump(mode="json") for c in citations],
            llm_provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )
        db.add(assistant_msg)
        await db.commit()

        return conv.id, assistant_msg.id


def _is_insufficient_response(content: str) -> bool:
    """Detect if the LLM indicated it couldn't find enough information."""
    markers = [
        "cannot find sufficient information",
        "no relevant information",
        "not enough information",
        "insufficient information",
        "could not find",
        "no documents were found",
    ]
    lower = content.lower()
    return any(m in lower for m in markers)
