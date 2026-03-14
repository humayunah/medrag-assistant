---
title: "HuggingFace Inference API returns 410 Gone — URL deprecated"
category: integration-issues
date: 2026-03-14
tags:
  - huggingface
  - embeddings
  - api-deprecation
  - rag-pipeline
  - fallback
severity: high
component: backend/app/services/embedding_service.py, backend/app/services/rag_service.py
framework:
  - FastAPI
  - httpx
---

# HuggingFace Inference API Returns 410 Gone

## Problem

RAG queries failed with `Client error '410 Gone'` when calling the HuggingFace embedding endpoint. The error message stated: `https://api-inference.huggingface.co is no longer supported. Please use https://router.huggingface.co instead.`

The entire query pipeline crashed because the embedding step was a hard dependency — if it failed, no BM25 fallback was attempted.

## Root Cause

Two issues:

1. HuggingFace deprecated `api-inference.huggingface.co` in favor of `router.huggingface.co` (March 2026).
2. The RAG service called `embed_query()` before BM25 search and treated any failure as fatal, with no fallback path.

## Solution

**1. Updated the API URL** in `embedding_service.py`:

```python
# Before
_API_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{_MODEL_ID}"

# After
_API_URL = f"https://router.huggingface.co/pipeline/feature-extraction/{_MODEL_ID}"
```

**2. Added BM25 fallback** in `rag_service.py` so the pipeline degrades gracefully:

```python
# Embed with graceful fallback
query_embedding = None
try:
    query_embedding = await self._embedding_service.embed_query(query_text)
except Exception as exc:
    logger.warning("embedding_failed_fallback_bm25", error=str(exc))

# Vector search only if embedding succeeded
vector_results = []
if query_embedding is not None:
    vector_results = await self._vector_search(db, tenant_id, query_embedding, document_ids)
bm25_results = await self._bm25_search(db, tenant_id, query_text, document_ids)
```

**3. Adjusted quality gate** — RRF scores (~0.016) are much smaller than cosine similarity (0-1), so the 0.65 threshold was skipped for BM25-only results:

```python
if vector_results:
    filtered = [r for r in fused if r["score"] >= _SIMILARITY_THRESHOLD]
else:
    filtered = fused  # BM25 tsquery already filters for relevance
```

## Prevention

External API endpoints deprecate without warning. Always build resilient pipelines with fallback paths so a single provider failure doesn't crash the entire feature. Log the degradation rather than raising.
