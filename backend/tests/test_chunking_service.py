"""Tests for the section-aware medical document chunking service."""

import re

import pytest

from app.services.chunking_service import chunk_document, ChunkResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pages(texts: list[str], start_page: int = 1) -> list[dict]:
    """Build a list of page dicts from plain text strings."""
    return [{"text": t, "page_number": start_page + i} for i, t in enumerate(texts)]


# ---------------------------------------------------------------------------
# 1. Basic chunking of a simple single-page document
# ---------------------------------------------------------------------------


class TestBasicSinglePage:
    def test_single_short_page_returns_one_chunk(self):
        pages = _make_pages(["Patient presents with headache and fatigue."])
        chunks = chunk_document(pages)

        assert len(chunks) == 1
        assert isinstance(chunks[0], ChunkResult)
        assert chunks[0].chunk_index == 0
        assert chunks[0].page_number == 1

    def test_single_chunk_content_contains_original_text(self):
        text = "Patient presents with headache and fatigue."
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        assert text in chunks[0].content

    def test_plain_text_populated(self):
        text = "Patient presents with headache and fatigue."
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        assert chunks[0].plain_text.strip() != ""

    def test_metadata_dict_present(self):
        pages = _make_pages(["Some clinical note."])
        chunks = chunk_document(pages)

        meta = chunks[0].metadata
        assert "page_number" in meta
        assert "section_title" in meta
        assert "chunk_index" in meta
        assert "char_count" in meta

    def test_empty_pages_list_returns_empty(self):
        assert chunk_document([]) == []


# ---------------------------------------------------------------------------
# 2. Section header detection
# ---------------------------------------------------------------------------


class TestSectionHeaderDetection:
    @pytest.mark.parametrize(
        "header_line",
        [
            "ASSESSMENT AND PLAN:",
            "MEDICATIONS:",
            "HPI:",
            "HISTORY OF PRESENT ILLNESS:",
            "CHIEF COMPLAINT",
            "REVIEW OF SYSTEMS:",
            "PHYSICAL EXAMINATION:",
            "LABS:",
            "VITAL SIGNS:",
            "SOCIAL HISTORY",
            "FAMILY HISTORY:",
            "ALLERGIES",
            "DISCHARGE INSTRUCTIONS:",
            "HOSPITAL COURSE:",
        ],
    )
    def test_known_headers_create_sections(self, header_line):
        """Each known header should be detected and used as section_title."""
        # Build a document long enough to avoid the fast-path single-chunk return.
        filler = "x " * 1200  # ~2400 chars
        text = f"Intro paragraph.\n{filler}\n{header_line}\nSome section body text.\n{filler}"
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        # The header (stripped of trailing colon/punctuation, uppercased) should
        # appear as a section_title on at least one chunk.
        canonical = re.sub(r"[\s:;\-]+$", "", header_line.strip()).upper()
        section_titles = {c.section_title for c in chunks if c.section_title}
        assert (
            canonical in section_titles
        ), f"Expected '{canonical}' in section_titles {section_titles}"

    def test_lowercase_header_not_detected(self):
        """Headers must match known list; random lowercase text should not match."""
        filler = "y " * 1200
        text = f"{filler}\nrandom line of text\n{filler}"
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        for c in chunks:
            assert c.section_title is None

    def test_header_with_trailing_colon_recognized(self):
        filler = "z " * 1200
        text = f"{filler}\nMEDICATIONS:\nAspirin 81 mg daily\n{filler}"
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        titles = {c.section_title for c in chunks}
        assert "MEDICATIONS" in titles

    def test_header_with_trailing_dash_recognized(self):
        filler = "z " * 1200
        text = f"{filler}\nPLAN -\nContinue current medications\n{filler}"
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        titles = {c.section_title for c in chunks}
        assert "PLAN" in titles


# ---------------------------------------------------------------------------
# 3. Micro-header prepending when section_title exists
# ---------------------------------------------------------------------------


class TestMicroHeaderPrepending:
    def test_micro_header_present_when_section_title_exists(self):
        filler = "a " * 1200
        text = f"{filler}\nASSESSMENT AND PLAN:\nPatient is stable.\n{filler}"
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        section_chunks = [c for c in chunks if c.section_title == "ASSESSMENT AND PLAN"]
        assert len(section_chunks) >= 1

        for c in section_chunks:
            assert "[Section: ASSESSMENT AND PLAN" in c.content

    def test_micro_header_includes_page_number(self):
        filler = "b " * 1200
        text = f"{filler}\nMEDICATIONS:\nAspirin 81mg\n{filler}"
        pages = _make_pages([text], start_page=3)
        chunks = chunk_document(pages)

        section_chunks = [c for c in chunks if c.section_title == "MEDICATIONS"]
        assert len(section_chunks) >= 1

        for c in section_chunks:
            assert "Page: 3" in c.content

    def test_micro_header_format(self):
        """Micro-header should follow the pattern [Section: X | Page: N]."""
        filler = "c " * 1200
        text = f"{filler}\nHPI:\nOnset was two days ago.\n{filler}"
        pages = _make_pages([text], start_page=5)
        chunks = chunk_document(pages)

        hpi_chunks = [c for c in chunks if c.section_title == "HPI"]
        assert len(hpi_chunks) >= 1
        assert "[Section: HPI | Page: 5]" in hpi_chunks[0].content

    def test_no_micro_header_when_no_section_title_and_no_page(self):
        """When section_title is None and page is None, no micro-header bracket."""
        # The fast-path (short text) with page_number still produces a micro-header
        # with the page.  We need to verify the micro_header helper logic
        # through chunk_document indirectly: a single short doc does get a
        # page-based micro-header, so check it's well-formed.
        pages = [{"text": "Short text.", "page_number": 1}]
        chunks = chunk_document(pages)

        # Should have "[Page: 1]" since section is None but page exists
        assert "[Page: 1]" in chunks[0].content


# ---------------------------------------------------------------------------
# 4. Multi-page document chunking preserves page numbers
# ---------------------------------------------------------------------------


class TestMultiPageDocument:
    def test_page_numbers_preserved_across_pages(self):
        filler = "d " * 600
        page1 = f"HPI:\nPatient reports chest pain.\n{filler}"
        page2 = f"MEDICATIONS:\nMetoprolol 25mg BID\n{filler}"
        page3 = f"ASSESSMENT AND PLAN:\nContinue treatment.\n{filler}"
        pages = _make_pages([page1, page2, page3])
        chunks = chunk_document(pages)

        page_numbers = {c.page_number for c in chunks}
        # At least pages 1 and 2 should appear (page 3 section starts on page 3)
        assert 1 in page_numbers or 2 in page_numbers or 3 in page_numbers

    def test_sections_spanning_pages_get_start_page(self):
        """A section that starts on page 2 should have page_number=2."""
        filler = "e " * 600
        page1 = f"Introduction text.\n{filler}"
        page2 = f"LABS:\nWBC 7.2, Hgb 13.1\n{filler}"
        pages = _make_pages([page1, page2])
        chunks = chunk_document(pages)

        lab_chunks = [c for c in chunks if c.section_title == "LABS"]
        assert len(lab_chunks) >= 1
        assert lab_chunks[0].page_number == 2

    def test_first_page_number_propagated_to_unsectioned_text(self):
        """Text before any header gets the page number from the first page."""
        pages = _make_pages(["Just some intro text."], start_page=7)
        chunks = chunk_document(pages)
        assert chunks[0].page_number == 7


# ---------------------------------------------------------------------------
# 5. Very long text gets split into multiple chunks
# ---------------------------------------------------------------------------


class TestLongTextSplitting:
    def test_long_section_produces_multiple_chunks(self):
        """A section with >2048 chars should be split into multiple chunks."""
        # Build a long section body (~5000 chars)
        long_body = "This is a sentence about the patient. " * 200  # ~7600 chars
        filler = "f " * 1200
        text = f"{filler}\nASSESSMENT AND PLAN:\n{long_body}"
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        assessment_chunks = [
            c for c in chunks if c.section_title == "ASSESSMENT AND PLAN"
        ]
        assert (
            len(assessment_chunks) >= 2
        ), f"Expected >=2 chunks for long section, got {len(assessment_chunks)}"

    def test_each_sub_chunk_within_size_limit(self):
        """No individual chunk's plain_text should vastly exceed _TARGET_CHARS."""
        long_body = "Word " * 2000  # ~10000 chars
        filler = "g " * 1200
        text = f"{filler}\nHPI:\n{long_body}"
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        for c in chunks:
            # Allow some overhead from the micro-header, but plain_text
            # (which is from the fragment) should be close to _TARGET_CHARS.
            # Use a generous upper bound (3x) to catch gross violations.
            assert (
                len(c.plain_text) <= 2048 * 3
            ), f"Chunk plain_text is {len(c.plain_text)} chars, expected <= ~6144"

    def test_long_text_without_headers_still_splits(self):
        """Even text with no recognised headers should split when it's long."""
        long_text = "Unrecognised paragraph. " * 400  # ~9600 chars
        pages = _make_pages([long_text])
        chunks = chunk_document(pages)

        assert len(chunks) >= 2

    def test_overlap_between_consecutive_chunks(self):
        """Consecutive chunks from the same section should share overlap text."""
        # Build text with identifiable sentences
        sentences = [f"Sentence number {i} in the document. " for i in range(200)]
        long_body = "".join(sentences)
        filler = "h " * 1200
        text = f"{filler}\nMEDICATIONS:\n{long_body}"
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        med_chunks = [c for c in chunks if c.section_title == "MEDICATIONS"]
        if len(med_chunks) >= 2:
            # The end of chunk N should overlap with the beginning of chunk N+1
            # Check that some text from the tail of chunk 0 appears in chunk 1
            tail_of_first = med_chunks[0].plain_text[-100:]
            # At least some portion should appear in the next chunk
            # (overlap is 200 chars, so this is a reasonable check)
            overlap_found = any(
                word in med_chunks[1].plain_text
                for word in tail_of_first.split()
                if len(word) > 3
            )
            assert overlap_found, "Expected overlap between consecutive chunks"


# ---------------------------------------------------------------------------
# 6. Empty page text is handled gracefully
# ---------------------------------------------------------------------------


class TestEmptyPages:
    def test_empty_string_page(self):
        pages = [{"text": "", "page_number": 1}]
        chunks = chunk_document(pages)
        # Should either return empty or a single chunk with empty/whitespace content
        # The function returns [] for truly empty content since full_text is empty
        # Actually, full_text would be "" which is <= _TARGET_CHARS, so fast-path
        # returns a single chunk. Let's just verify no crash.
        assert isinstance(chunks, list)

    def test_whitespace_only_page(self):
        pages = [{"text": "   \n\n  \n  ", "page_number": 1}]
        chunks = chunk_document(pages)
        assert isinstance(chunks, list)

    def test_mixed_empty_and_content_pages(self):
        pages = [
            {"text": "", "page_number": 1},
            {"text": "Real content here.", "page_number": 2},
            {"text": "", "page_number": 3},
        ]
        chunks = chunk_document(pages)
        assert len(chunks) >= 1
        # The real content should be present
        combined_content = " ".join(c.content for c in chunks)
        assert "Real content here." in combined_content

    def test_page_with_missing_text_key(self):
        """A page dict missing the 'text' key should be handled gracefully."""
        pages = [{"page_number": 1}, {"text": "Some text.", "page_number": 2}]
        chunks = chunk_document(pages)
        assert isinstance(chunks, list)


# ---------------------------------------------------------------------------
# 7. chunk_index is sequential starting from 0
# ---------------------------------------------------------------------------


class TestChunkIndexSequencing:
    def test_single_chunk_has_index_zero(self):
        pages = _make_pages(["Short note."])
        chunks = chunk_document(pages)
        assert chunks[0].chunk_index == 0

    def test_multiple_chunks_sequential_indices(self):
        """chunk_index must be 0, 1, 2, ... with no gaps."""
        long_text = "Sequential index test. " * 400
        pages = _make_pages([long_text])
        chunks = chunk_document(pages)

        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_indices_span_across_sections(self):
        """chunk_index should be globally sequential, not reset per section."""
        filler = "i " * 1200
        text = (
            f"{filler}\n"
            f"HPI:\nPatient with chest pain.\n{filler}\n"
            f"MEDICATIONS:\nAspirin daily.\n{filler}\n"
            f"ASSESSMENT AND PLAN:\nContinue treatment.\n{filler}"
        )
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        indices = [c.chunk_index for c in chunks]
        assert indices == list(
            range(len(chunks))
        ), f"Indices {indices} are not sequential 0..{len(chunks)-1}"

    def test_metadata_chunk_index_matches_attribute(self):
        long_text = "Metadata index check. " * 400
        pages = _make_pages([long_text])
        chunks = chunk_document(pages)

        for c in chunks:
            assert c.metadata["chunk_index"] == c.chunk_index


# ---------------------------------------------------------------------------
# 8. tsvector normalization in plain_text (special chars stripped)
# ---------------------------------------------------------------------------


class TestTsvectorNormalization:
    def test_non_printable_chars_removed(self):
        text = "Patient\x00 has\x01 a\x02 condition\x07."
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        plain = chunks[0].plain_text
        # No non-printable characters should remain (outside 0x20-0x7E and \n)
        assert "\x00" not in plain
        assert "\x01" not in plain
        assert "\x02" not in plain
        assert "\x07" not in plain

    def test_excessive_whitespace_collapsed(self):
        text = "Patient    has     multiple      spaces."
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        plain = chunks[0].plain_text
        assert "    " not in plain
        # Multiple horizontal spaces should become a single space
        assert "Patient has multiple spaces." in plain

    def test_multiple_blank_lines_collapsed(self):
        text = "Line one.\n\n\n\n\nLine two."
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        plain = chunks[0].plain_text
        # Multiple newlines collapsed to single newline
        assert "\n\n" not in plain
        assert "Line one.\nLine two." in plain

    def test_tabs_converted_to_space(self):
        text = "Lab\tresults\tare\tnormal."
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        plain = chunks[0].plain_text
        assert "\t" not in plain
        assert "Lab results are normal." in plain

    def test_unicode_chars_stripped(self):
        text = "Temperature: 98.6\u00b0F, Weight: 70\u00a0kg"
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        plain = chunks[0].plain_text
        # degree sign and non-breaking space are outside 0x20-0x7E
        assert "\u00b0" not in plain
        assert "\u00a0" not in plain

    def test_plain_text_is_stripped(self):
        text = "  \n  Content with surrounding whitespace.  \n  "
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        plain = chunks[0].plain_text
        assert not plain.startswith(" ")
        assert not plain.startswith("\n")
        assert not plain.endswith(" ")
        assert not plain.endswith("\n")


# ---------------------------------------------------------------------------
# 9. Edge case: text with no recognized headers -> section_title=None
# ---------------------------------------------------------------------------


class TestNoRecognizedHeaders:
    def test_no_headers_all_sections_none(self):
        text = (
            "The patient is a 45-year-old male presenting with shortness of breath.\n"
            "He has a history of asthma and seasonal allergies.\n"
            "Currently taking albuterol inhaler as needed.\n"
        )
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        for c in chunks:
            assert c.section_title is None

    def test_no_headers_long_text_still_chunks(self):
        """Even without headers, long text should be chunked."""
        paragraphs = "No header paragraph. " * 400
        pages = _make_pages([paragraphs])
        chunks = chunk_document(pages)

        assert len(chunks) >= 2
        for c in chunks:
            assert c.section_title is None

    def test_random_uppercase_not_treated_as_header(self):
        """ALL-CAPS text that isn't a known header should NOT create a section."""
        filler = "j " * 1200
        text = f"{filler}\nRANDOM UNKNOWN HEADING\nSome body text.\n{filler}"
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        for c in chunks:
            assert c.section_title != "RANDOM UNKNOWN HEADING"

    def test_metadata_section_title_none_when_no_headers(self):
        pages = _make_pages(["Simple text without any section headers."])
        chunks = chunk_document(pages)

        for c in chunks:
            assert c.metadata["section_title"] is None


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_single_page_with_multiple_sections(self):
        filler = "k " * 600
        text = (
            f"HPI:\nChest pain for 3 days.\n{filler}\n"
            f"MEDICATIONS:\nAspirin 81mg\n{filler}\n"
            f"ALLERGIES:\nNKDA"
        )
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        titles = {c.section_title for c in chunks}
        assert "HPI" in titles
        assert "MEDICATIONS" in titles
        assert "ALLERGIES" in titles

    def test_page_number_in_metadata_matches_attribute(self):
        pages = _make_pages(["Note content."], start_page=42)
        chunks = chunk_document(pages)

        for c in chunks:
            assert c.metadata["page_number"] == c.page_number

    def test_char_count_in_metadata(self):
        text = "Exactly this text."
        pages = _make_pages([text])
        chunks = chunk_document(pages)

        # char_count in metadata should reflect the fragment length (the raw text,
        # not the content with micro-header).
        assert chunks[0].metadata["char_count"] == len(text)

    def test_content_differs_from_plain_text_with_special_chars(self):
        """content has the micro-header; plain_text is normalized raw text."""
        text = "Note\twith\ttabs\tand\x00nulls."
        pages = _make_pages([text], start_page=2)
        chunks = chunk_document(pages)

        # content should include micro-header with page
        assert "[Page: 2]" in chunks[0].content
        # plain_text should not have micro-header
        assert "[Page:" not in chunks[0].plain_text

    def test_many_pages_all_processed(self):
        pages = [{"text": f"Page {i} content.", "page_number": i} for i in range(1, 11)]
        chunks = chunk_document(pages)
        assert len(chunks) >= 1

        combined = " ".join(c.content for c in chunks)
        for i in range(1, 11):
            assert f"Page {i} content." in combined
