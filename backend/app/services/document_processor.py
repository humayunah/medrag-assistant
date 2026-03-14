"""Document processing pipeline.

Extracts text from PDFs (with OCR fallback for scanned pages), chunks the
document using section-aware splitting, generates embeddings, and persists
chunks to the database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import fitz  # PyMuPDF
import structlog
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import _get_session_factory
from app.models.base import DocumentStatus
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.query_cache import QueryCache
from app.services.chunking_service import ChunkResult, chunk_document
from app.services.embedding_service import EmbeddingService
from app.services.websocket_manager import ws_manager

logger = structlog.get_logger("document_processor")

# Minimum chars per page before OCR fallback triggers
_OCR_CHAR_THRESHOLD = 50


async def process_document(document_id: uuid.UUID, file_bytes: bytes) -> None:
    """Full document processing pipeline.

    1. Extract text from PDF (with OCR fallback for scanned pages)
    2. Chunk text into section-aware segments
    3. Generate embeddings via HuggingFace API
    4. Persist chunks + embeddings to database
    5. Update document status
    6. Broadcast progress via WebSocket
    """
    factory = _get_session_factory()

    async with factory() as db:
        doc = await db.get(Document, document_id)
        if not doc:
            logger.error("document_not_found", document_id=str(document_id))
            return

        tenant_id = doc.tenant_id

        try:
            # -- Status: processing --
            doc.status = DocumentStatus.PROCESSING
            await db.commit()
            await _send_update(
                tenant_id, document_id, "processing", 0.0, "Starting text extraction"
            )

            # Step 1: Extract text from PDF
            pages, ocr_confidence = _extract_text(file_bytes)
            page_count = len(pages)

            doc.page_count = page_count
            doc.ocr_confidence = ocr_confidence
            await db.commit()
            await _send_update(
                tenant_id,
                document_id,
                "processing",
                0.2,
                f"Extracted {page_count} pages",
            )

            # Step 2: Chunk document
            chunks = chunk_document(pages)
            if not chunks:
                doc.status = DocumentStatus.FAILED
                doc.metadata_ = {"error": "No text content extracted"}
                await db.commit()
                await _send_update(
                    tenant_id, document_id, "failed", 1.0, "No text content found"
                )
                return

            await _send_update(
                tenant_id,
                document_id,
                "processing",
                0.4,
                f"Created {len(chunks)} chunks",
            )

            # Step 3: Generate embeddings
            embedding_service = EmbeddingService()
            try:
                texts_to_embed = [c.content for c in chunks]
                embeddings = await embedding_service.embed_texts(texts_to_embed)
            finally:
                await embedding_service.close()

            await _send_update(
                tenant_id, document_id, "processing", 0.7, "Embeddings generated"
            )

            # Step 4: Persist chunks
            await _store_chunks(db, document_id, tenant_id, chunks, embeddings)
            await _send_update(
                tenant_id, document_id, "processing", 0.9, "Chunks stored"
            )

            # Step 5: Mark ready
            doc.status = DocumentStatus.READY
            await db.commit()

            # Step 6: Invalidate query cache for this tenant
            await _invalidate_tenant_cache(db, tenant_id)

            await _send_update(
                tenant_id, document_id, "ready", 1.0, "Processing complete"
            )
            logger.info(
                "document_processed",
                document_id=str(document_id),
                pages=page_count,
                chunks=len(chunks),
                ocr_confidence=ocr_confidence,
            )

        except Exception as e:
            logger.error(
                "document_processing_failed",
                document_id=str(document_id),
                error=str(e),
            )
            doc.status = DocumentStatus.FAILED
            doc.metadata_ = {"error": str(e)[:500]}
            await db.commit()
            await _send_update(
                tenant_id,
                document_id,
                "failed",
                1.0,
                f"Processing failed: {str(e)[:200]}",
            )


def _extract_text(file_bytes: bytes) -> tuple[list[dict], float | None]:
    """Extract text from a PDF, with OCR fallback for scanned pages.

    Returns:
        (pages, avg_ocr_confidence) where pages is a list of
        {"text": str, "page_number": int} dicts.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[dict] = []
    ocr_confidences: list[float] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text").strip()

        if len(page_text) < _OCR_CHAR_THRESHOLD:
            # OCR fallback for scanned/image-heavy pages
            ocr_result = _ocr_page(page)
            page_text = ocr_result["text"]
            if ocr_result["confidence"] is not None:
                ocr_confidences.append(ocr_result["confidence"])

        if page_text:
            pages.append({"text": page_text, "page_number": page_num + 1})

    doc.close()

    avg_confidence = (
        sum(ocr_confidences) / len(ocr_confidences) if ocr_confidences else None
    )
    return pages, avg_confidence


def _ocr_page(page: fitz.Page) -> dict:
    """Run Tesseract OCR on a PDF page rendered as an image.

    Returns dict with 'text' and 'confidence' keys.
    """
    try:
        import pytesseract
        from PIL import Image
        import io

        # Render page at 300 DPI for good OCR quality
        pix = page.get_pixmap(dpi=300)
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes))

        # Convert to grayscale for better OCR
        image = image.convert("L")

        # Get OCR data with confidence scores
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        # Extract text and compute average confidence
        words = []
        confidences = []
        for i, conf in enumerate(ocr_data["conf"]):
            if int(conf) > 0:
                words.append(ocr_data["text"][i])
                confidences.append(int(conf))

        text = " ".join(w for w in words if w.strip())
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return {"text": text, "confidence": avg_conf / 100.0}

    except Exception as e:
        logger.warning("ocr_fallback_failed", error=str(e))
        return {"text": "", "confidence": None}


async def _store_chunks(
    db: AsyncSession,
    document_id: uuid.UUID,
    tenant_id: uuid.UUID,
    chunks: list[ChunkResult],
    embeddings: list[list[float]],
) -> None:
    """Persist document chunks with embeddings and tsvector to the database."""
    for chunk, embedding in zip(chunks, embeddings):
        db_chunk = DocumentChunk(
            document_id=document_id,
            tenant_id=tenant_id,
            content=chunk.content,
            embedding=embedding,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            metadata_=chunk.metadata,
        )
        db.add(db_chunk)

    await db.flush()

    # Generate tsvector for all chunks in this document using PostgreSQL's to_tsvector
    await db.execute(
        text("""
            UPDATE document_chunks
            SET search_vector = to_tsvector('english', content)
            WHERE document_id = :doc_id
            AND search_vector IS NULL
        """),
        {"doc_id": document_id},
    )
    await db.commit()


async def _invalidate_tenant_cache(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Invalidate all query cache entries for a tenant when documents change."""
    await db.execute(
        update(QueryCache)
        .where(
            QueryCache.tenant_id == tenant_id,
            QueryCache.invalidated_at.is_(None),
        )
        .values(invalidated_at=datetime.now(timezone.utc))
    )
    await db.commit()


async def _send_update(
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
    status: str,
    progress: float,
    message: str,
) -> None:
    """Send a WebSocket processing update, swallowing errors."""
    try:
        await ws_manager.send_processing_update(
            tenant_id=tenant_id,
            document_id=document_id,
            status=status,
            progress=progress,
            message=message,
        )
    except Exception:
        pass  # WebSocket delivery is best-effort
