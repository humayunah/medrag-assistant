"""Section-aware medical document chunking service.

Parses medical documents by recognized section headers, splits long sections
using recursive character splitting, and produces chunk metadata suitable for
vector and full-text search indexing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Public data structures
# ---------------------------------------------------------------------------


@dataclass
class ChunkResult:
    content: str  # The chunk text with micro-header prepended
    plain_text: str  # Raw text for tsvector generation
    chunk_index: int
    page_number: int | None
    section_title: str | None
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Recognised medical section headers (canonical forms, upper-cased)
# ---------------------------------------------------------------------------

_KNOWN_HEADERS: set[str] = {
    "IMPRESSION",
    "ASSESSMENT",
    "ASSESSMENT AND PLAN",
    "PLAN",
    "HPI",
    "HISTORY OF PRESENT ILLNESS",
    "MEDICATIONS",
    "CURRENT MEDICATIONS",
    "ALLERGIES",
    "PAST MEDICAL HISTORY",
    "PMH",
    "PAST SURGICAL HISTORY",
    "PSH",
    "FAMILY HISTORY",
    "SOCIAL HISTORY",
    "REVIEW OF SYSTEMS",
    "ROS",
    "PHYSICAL EXAMINATION",
    "PHYSICAL EXAM",
    "PE",
    "PROCEDURES",
    "PROCEDURE",
    "DISCHARGE INSTRUCTIONS",
    "DISCHARGE SUMMARY",
    "DISCHARGE DIAGNOSIS",
    "LABS",
    "LABORATORY",
    "LABORATORY DATA",
    "LABORATORY RESULTS",
    "VITALS",
    "VITAL SIGNS",
    "CHIEF COMPLAINT",
    "CC",
    "DIAGNOSIS",
    "DIAGNOSES",
    "OPERATIVE FINDINGS",
    "OPERATIVE NOTE",
    "FINDINGS",
    "IMAGING",
    "RADIOLOGY",
    "RESULTS",
    "RECOMMENDATIONS",
    "FOLLOW UP",
    "FOLLOW-UP",
    "CONSULT",
    "CONSULTATION",
    "SUBJECTIVE",
    "OBJECTIVE",
    "INDICATIONS",
    "TECHNIQUE",
    "COMPLICATIONS",
    "ESTIMATED BLOOD LOSS",
    "SPECIMENS",
    "ANESTHESIA",
    "PREOPERATIVE DIAGNOSIS",
    "POSTOPERATIVE DIAGNOSIS",
    "CLINICAL HISTORY",
    "INTERVAL HISTORY",
    "MENTAL STATUS EXAM",
    "NEUROLOGICAL EXAM",
    "DISPOSITION",
    "CONDITION ON DISCHARGE",
    "INSTRUCTIONS",
    "EMERGENCY DEPARTMENT COURSE",
    "ED COURSE",
    "HOSPITAL COURSE",
    "BRIEF HOSPITAL COURSE",
}

# ---------------------------------------------------------------------------
# Chunking parameters
# ---------------------------------------------------------------------------

_TARGET_CHARS = 2048  # ~512 tokens
_OVERLAP_CHARS = 200  # ~50 tokens

# Preferred split boundaries in descending priority
_SPLIT_SEPARATORS: list[str] = ["\n\n", "\n", ". ", ", ", " "]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_section_header(line: str) -> str | None:
    """Return the canonical section title if *line* looks like a medical header.

    Detection rules:
      1. Line stripped of whitespace and trailing colon/dash matches a known
         header (case-insensitive).
      2. A line that is entirely UPPER-CASE letters/spaces/punctuation **and**
         matches a known header is accepted.
    """
    stripped = line.strip()
    if not stripped:
        return None

    # Remove common trailing punctuation used after headers
    candidate = re.sub(r"[\s:;\-]+$", "", stripped)
    upper = candidate.upper()

    if upper in _KNOWN_HEADERS:
        return upper

    # Accept ALL-CAPS lines that match known headers even with minor
    # punctuation differences (e.g. "HISTORY OF PRESENT ILLNESS:")
    if candidate == candidate.upper() and len(candidate) > 1:
        # Already tried exact match above; try stripping digits/punctuation
        cleaned = re.sub(r"[^A-Z\s]", "", upper).strip()
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        if cleaned in _KNOWN_HEADERS:
            return cleaned

    return None


def _normalize_for_tsvector(text: str) -> str:
    """Strip formatting artifacts and collapse whitespace for full-text search."""
    text = re.sub(r"[^\S\n]+", " ", text)  # collapse horizontal whitespace
    text = re.sub(r"\n{2,}", "\n", text)  # collapse blank lines
    text = re.sub(r"[^\x20-\x7E\n]", "", text)  # strip non-printable
    return text.strip()


def _make_micro_header(section_title: str | None, page_number: int | None) -> str:
    parts: list[str] = []
    if section_title:
        parts.append(f"Section: {section_title}")
    if page_number is not None:
        parts.append(f"Page: {page_number}")
    if parts:
        return f"[{' | '.join(parts)}]"
    return ""


@dataclass
class _Section:
    """Intermediate representation of a detected document section."""

    title: str | None
    text: str
    page_number: int | None  # page where section starts


def _detect_sections(pages: list[dict]) -> list[_Section]:
    """Walk through pages and split the document into sections."""
    sections: list[_Section] = []
    current_title: str | None = None
    current_lines: list[str] = []
    current_page: int | None = None

    for page in pages:
        page_text: str = page.get("text", "")
        page_number: int = page.get("page_number", 1)

        for line in page_text.split("\n"):
            header = _is_section_header(line)
            if header is not None:
                # Flush the accumulated text as a section
                if current_lines:
                    sections.append(
                        _Section(
                            title=current_title,
                            text="\n".join(current_lines),
                            page_number=current_page,
                        )
                    )
                current_title = header
                current_lines = []
                current_page = page_number
            else:
                if current_page is None:
                    current_page = page_number
                current_lines.append(line)

    # Flush remaining text
    if current_lines:
        sections.append(
            _Section(
                title=current_title,
                text="\n".join(current_lines),
                page_number=current_page,
            )
        )

    return sections


def _recursive_split(text: str, max_chars: int, overlap: int) -> list[str]:
    """Recursively split *text* into chunks of at most *max_chars*.

    Tries each separator in priority order.  If no separator is found the text
    is hard-split at *max_chars*.
    """
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        # Try each separator to find a good split point
        split_pos: int | None = None
        for sep in _SPLIT_SEPARATORS:
            # Search backwards from max_chars for the separator
            idx = remaining.rfind(sep, 0, max_chars)
            if idx != -1:
                split_pos = idx + len(sep)
                break

        if split_pos is None or split_pos == 0:
            # Hard split as last resort
            split_pos = max_chars

        chunk = remaining[:split_pos].rstrip()
        chunks.append(chunk)

        # Advance with overlap
        advance = max(split_pos - overlap, 1)
        remaining = remaining[advance:].lstrip("\n")

    return chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk_document(pages: list[dict]) -> list[ChunkResult]:
    """Chunk a document into sections.

    Args:
        pages: List of dicts with keys 'text' (str) and 'page_number' (int).

    Returns:
        List of ChunkResult objects.
    """
    if not pages:
        return []

    # Fast-path: if the entire document is short, return a single chunk
    full_text = "\n".join(p.get("text", "") for p in pages)
    if len(full_text) <= _TARGET_CHARS:
        first_page = pages[0].get("page_number")
        micro = _make_micro_header(None, first_page)
        content = f"{micro}\n{full_text}" if micro else full_text
        return [
            ChunkResult(
                content=content,
                plain_text=_normalize_for_tsvector(full_text),
                chunk_index=0,
                page_number=first_page,
                section_title=None,
                metadata={
                    "page_number": first_page,
                    "section_title": None,
                    "chunk_index": 0,
                    "char_count": len(full_text),
                },
            )
        ]

    # Detect sections then split each one
    sections = _detect_sections(pages)
    results: list[ChunkResult] = []
    chunk_idx = 0

    for section in sections:
        text = section.text.strip()
        if not text:
            continue

        fragments = _recursive_split(text, _TARGET_CHARS, _OVERLAP_CHARS)

        for fragment in fragments:
            micro = _make_micro_header(section.title, section.page_number)
            content = f"{micro}\n{fragment}" if micro else fragment
            plain = _normalize_for_tsvector(fragment)

            results.append(
                ChunkResult(
                    content=content,
                    plain_text=plain,
                    chunk_index=chunk_idx,
                    page_number=section.page_number,
                    section_title=section.title,
                    metadata={
                        "page_number": section.page_number,
                        "section_title": section.title,
                        "chunk_index": chunk_idx,
                        "char_count": len(fragment),
                    },
                )
            )
            chunk_idx += 1

    return results
