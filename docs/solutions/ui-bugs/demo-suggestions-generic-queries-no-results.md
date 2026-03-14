---
title: "Demo suggestion queries too generic — RAG returns no relevant documents"
category: ui-bugs
date: 2026-03-15
tags:
  - demo
  - rag
  - bm25
  - query-quality
  - mtsamples
severity: medium
component: frontend/src/pages/Demo.tsx
framework:
  - React
---

# Demo Suggestion Queries Too Generic — No Relevant Results

## Problem

All 5 demo suggestion cards returned "I couldn't find any relevant document excerpts" despite 60 documents (295 chunks) being seeded, including 12 cardiology documents. Every suggested question produced the same unhelpful response.

## Root Cause

The demo queries used generic phrasing like "What are the common findings in cardiology reports?" The OR-based BM25 search matched words like "common", "findings", "reports" across all specialties equally, so cardiology-specific documents were outranked by neurology and general medicine docs that happened to use those generic words more frequently. The actual cardiology documents contained specific terminology (atrial fibrillation, cardioversion, catheterization) that the demo queries never referenced.

## Solution

Updated all 5 demo suggestion queries in `frontend/src/pages/Demo.tsx` to use specific medical terminology from the seeded MTSamples documents:

```typescript
const SUGGESTIONS = [
  // Before: "What are the common findings in cardiology reports?"
  { query: "What treatments are used for atrial fibrillation and cardioversion?" },
  // Before: "Summarize the orthopedic procedures documented"
  { query: "What are the post-operative findings in knee arthroplasty?" },
  // Before: "What medications are frequently mentioned in neurology cases?"
  { query: "What neuropsychological symptoms are evaluated in neurology consultations?" },
  // Before: "Describe the typical radiology report findings"
  { query: "What did the MRI brain scan reveal?" },
  // Before: "What are the discharge instructions for gastroenterology patients?"
  { query: "What are the indications for laparoscopic cholecystectomy?" },
];
```

Verified via SQL that the new queries rank the correct specialty documents in the top BM25 results, and via the live API that the LLM returns specific, cited answers.

## Prevention

When writing demo/example queries for a RAG system, always test them against the actual seeded data. Generic natural language questions often match broad terms across all documents rather than targeting the intended specialty. Use terminology that appears in the actual document content, not just the filenames or category labels.
