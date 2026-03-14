---
title: "BM25 search returns 0 matches — plainto_tsquery AND logic too restrictive"
category: logic-errors
date: 2026-03-15
tags:
  - postgresql
  - full-text-search
  - tsquery
  - rag-pipeline
  - bm25
severity: high
component: backend/app/services/rag_service.py
framework:
  - FastAPI
  - SQLAlchemy
  - PostgreSQL
---

# BM25 plainto_tsquery AND Logic Returns Zero Matches

## Problem

RAG queries consistently returned "I couldn't find any relevant document excerpts" despite 295 chunks being seeded with populated `search_vector` columns. Every suggested question on the demo page produced the same "no relevant documents" response.

## Root Cause

The `_bm25_search` method used `plainto_tsquery('english', :query)` which applies AND logic — all stemmed words must appear in a single chunk. For a natural language question like "What are the common findings in cardiology reports?", PostgreSQL generates:

```
'common' & 'find' & 'cardiolog' & 'report'
```

No single chunk contained ALL four stemmed terms, so the query returned 0 rows. Since the embedding service was also failing (HuggingFace API deprecation), the pipeline fell back to BM25-only mode, meaning zero retrieval results across the board.

## Diagnosis

Verified with direct SQL queries against Supabase:

```sql
-- AND logic (plainto_tsquery): 0 matches
SELECT count(*) FROM document_chunks
WHERE search_vector @@ plainto_tsquery('english',
  'What are the common findings in cardiology reports?');

-- OR logic (to_tsquery with |): 110 matches
SELECT count(*) FROM document_chunks
WHERE search_vector @@ to_tsquery('english',
  'common | findings | cardiology | reports');

-- Individual terms work fine
SELECT count(*) FROM document_chunks
WHERE search_vector @@ to_tsquery('english', 'cardiology');
-- Returns: 10
```

## Solution

Added `_build_or_tsquery` helper that extracts words (3+ chars) from the query and joins them with `|` (OR) operators. Replaced `plainto_tsquery` with `to_tsquery` using this OR-based input:

```python
@staticmethod
def _build_or_tsquery(query_text: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", query_text)
    words = [w for w in words if len(w) > 2]
    if not words:
        return query_text.strip() or "empty"
    return " | ".join(words)
```

SQL changed from:
```sql
-- Before (AND — too restrictive)
AND dc.search_vector @@ plainto_tsquery('english', :query)

-- After (OR — retrieves chunks matching any term)
AND dc.search_vector @@ to_tsquery('english', :tsquery)
```

PostgreSQL's English dictionary still stems the words and removes stop words. `ts_rank_cd` ensures chunks matching more terms rank higher.

## Prevention

- For RAG BM25 search, OR-based matching is almost always correct — you want to retrieve documents matching *any* query term, then let ranking/RRF sort by relevance.
- `plainto_tsquery` is designed for exact-phrase-style matching, not for natural language questions. Use `to_tsquery` with `|` for broad recall.
- Always test full-text search with actual user queries during development, not just single keywords.
