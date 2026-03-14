"""Seed demo data using the MTSamples medical transcription dataset.

Downloads the CC0-licensed MTSamples CSV, curates ~60 documents across 6
specialties, creates a demo tenant + user, and populates Document and
DocumentChunk rows (with tsvector but no embeddings).

Usage:
    uv run python scripts/seed_demo_data.py          # seed fresh data
    uv run python scripts/seed_demo_data.py --clear   # delete existing demo data first
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import logging
import re
import sys
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the backend package is importable when running from repo root
# ---------------------------------------------------------------------------
_backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import httpx
from sqlalchemy import text

from app.core.database import _get_session_factory, init_engine
from app.core.logging import setup_logging
from app.models.base import AppRole, DocumentStatus
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.tenant import Tenant
from app.models.user_profile import UserProfile
from app.services.chunking_service import chunk_document

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MTSAMPLES_CSV_URL = (
    "https://raw.githubusercontent.com/eshza/"
    "medicalTranscriptsKaggle/master/mtsamples.csv"
)

DEMO_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")
DEMO_TENANT_NAME = "Demo Medical Center"
DEMO_TENANT_SLUG = "demo"
DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_USER_NAME = "Demo User"
DEMO_USER_ROLE = AppRole.STAFF

# Specialty quotas — maps the MTSamples "medical_specialty" column value
# (stripped/lower-cased) to the desired document count.
SPECIALTY_QUOTAS: dict[str, int] = {
    "cardiovascular / pulmonary": 12,
    "orthopedic": 10,
    "general medicine": 12,
    "neurology": 8,
    "gastroenterology": 8,
    "radiology": 10,
}

# Friendly labels for logging
SPECIALTY_LABELS: dict[str, str] = {
    "cardiovascular / pulmonary": "Cardiology",
    "orthopedic": "Orthopedic",
    "general medicine": "General Medicine",
    "neurology": "Neurology",
    "gastroenterology": "Gastroenterology",
    "radiology": "Radiology",
}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_filename(title: str, specialty: str) -> str:
    """Turn a sample title into a clean PDF-ish filename.

    Example: "Chest Pain - Loss of Consciousness" with specialty "Cardiology"
    -> "cardiology-chest-pain-loss-of-consciousness.pdf"
    """
    label = SPECIALTY_LABELS.get(specialty, specialty).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    # Truncate overly long slugs
    if len(slug) > 80:
        slug = slug[:80].rsplit("-", 1)[0]
    return f"{label}-{slug}.pdf"


def _download_csv() -> list[dict[str, str]]:
    """Download the MTSamples CSV and return rows as dicts."""
    print(f"Downloading MTSamples CSV from {MTSAMPLES_CSV_URL} ...")
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        resp = client.get(MTSAMPLES_CSV_URL)
        resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    print(f"  Downloaded {len(rows)} rows.")
    return rows


def _curate_samples(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Select documents per specialty quota, preferring longer transcriptions."""
    selected: list[dict[str, str]] = []

    for specialty_key, quota in SPECIALTY_QUOTAS.items():
        # Filter rows matching this specialty (case-insensitive, stripped)
        matching = [
            r for r in rows
            if r.get("medical_specialty", "").strip().lower() == specialty_key
            and r.get("transcription", "").strip()  # skip empty transcriptions
        ]

        # Sort by transcription length descending — prefer richer content
        matching.sort(key=lambda r: len(r.get("transcription", "")), reverse=True)

        picked = matching[:quota]
        label = SPECIALTY_LABELS.get(specialty_key, specialty_key)
        print(f"  {label}: found {len(matching)} candidates, selected {len(picked)}")
        selected.extend(picked)

    return selected


# ---------------------------------------------------------------------------
# Core seeding logic
# ---------------------------------------------------------------------------

async def _clear_demo_data() -> None:
    """Delete demo data using individual queries to avoid subquery issues."""
    factory = _get_session_factory()
    async with factory() as session:
        async with session.begin():
            # First find the demo tenant id
            result = await session.execute(
                text("SELECT id FROM tenants WHERE slug = :slug"),
                {"slug": DEMO_TENANT_SLUG},
            )
            row = result.fetchone()
            if row is None:
                print("No existing demo data found.")
                return

            tenant_id = row[0]

            # Delete in dependency order
            await session.execute(
                text("DELETE FROM document_chunks WHERE tenant_id = :tid"),
                {"tid": str(tenant_id)},
            )
            await session.execute(
                text("DELETE FROM documents WHERE tenant_id = :tid"),
                {"tid": str(tenant_id)},
            )
            await session.execute(
                text("DELETE FROM user_profiles WHERE id = :uid"),
                {"uid": str(DEMO_USER_ID)},
            )
            await session.execute(
                text("DELETE FROM tenants WHERE slug = :slug"),
                {"slug": DEMO_TENANT_SLUG},
            )

    print("Cleared existing demo data.")


async def _seed() -> None:
    """Main seeding coroutine."""
    # 1. Download and curate
    rows = _download_csv()
    samples = _curate_samples(rows)
    total = len(samples)
    specialty_count = len(SPECIALTY_QUOTAS)

    print(f"\nSeeding {total} documents across {specialty_count} specialties...\n")

    factory = _get_session_factory()

    # 2. Create tenant + user
    async with factory() as session:
        async with session.begin():
            tenant = Tenant(
                id=DEMO_TENANT_ID,
                name=DEMO_TENANT_NAME,
                slug=DEMO_TENANT_SLUG,
                settings={},
            )
            session.add(tenant)
            await session.flush()

            tenant_id = tenant.id

            user = UserProfile(
                id=DEMO_USER_ID,
                tenant_id=tenant_id,
                role=DEMO_USER_ROLE,
                full_name=DEMO_USER_NAME,
            )
            session.add(user)

    print(f"Created tenant '{DEMO_TENANT_NAME}' (id={tenant_id})")
    print(f"Created user  '{DEMO_USER_NAME}'  (id={DEMO_USER_ID})")
    print()

    # 3. Create documents and chunks
    doc_count = 0
    chunk_count = 0

    for sample in samples:
        specialty_key = sample.get("medical_specialty", "").strip().lower()
        title = sample.get("sample_name", sample.get("description", "Untitled")).strip()
        transcription = sample.get("transcription", "").strip()

        if not transcription:
            continue

        filename = _sanitize_filename(title, specialty_key)
        storage_path = f"demo/{tenant_id}/{filename}"

        async with factory() as session:
            async with session.begin():
                doc = Document(
                    tenant_id=tenant_id,
                    uploaded_by=DEMO_USER_ID,
                    filename=filename,
                    storage_path=storage_path,
                    mime_type="application/pdf",
                    file_size_bytes=len(transcription.encode("utf-8")),
                    status=DocumentStatus.READY,
                    page_count=1,
                    metadata_={"source": "mtsamples", "specialty": specialty_key},
                )
                session.add(doc)
                await session.flush()

                doc_id = doc.id

                # Chunk the transcription
                pages = [{"text": transcription, "page_number": 1}]
                chunk_results = chunk_document(pages)

                for cr in chunk_results:
                    chunk = DocumentChunk(
                        document_id=doc_id,
                        tenant_id=tenant_id,
                        content=cr.content,
                        chunk_index=cr.chunk_index,
                        page_number=cr.page_number,
                        section_title=cr.section_title,
                        metadata_=cr.metadata,
                    )
                    session.add(chunk)

                chunk_count += len(chunk_results)

            # Generate tsvector for full-text search (outside the ORM)
            async with session.begin():
                await session.execute(
                    text(
                        "UPDATE document_chunks "
                        "SET search_vector = to_tsvector('english', content) "
                        "WHERE document_id = :doc_id"
                    ),
                    {"doc_id": str(doc_id)},
                )

        doc_count += 1
        label = SPECIALTY_LABELS.get(specialty_key, specialty_key)
        if doc_count % 10 == 0 or doc_count == total:
            print(f"  [{doc_count}/{total}] Last: {label} — {filename}")

    print()
    print(f"Done! Seeded {doc_count} documents with {chunk_count} chunks total.")
    print(f"Embeddings are NULL — run the embedding backfill job to populate them.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed demo data using the MTSamples dataset.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete existing demo tenant data before seeding.",
    )
    args = parser.parse_args()

    setup_logging()
    init_engine()

    if args.clear:
        await _clear_demo_data()

    await _seed()


if __name__ == "__main__":
    asyncio.run(main())
