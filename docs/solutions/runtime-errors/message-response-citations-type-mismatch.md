---
title: "MessageResponse citations field rejects list — Pydantic expects dict"
category: runtime-errors
date: 2026-03-14
tags:
  - pydantic
  - schema
  - serialization
  - conversations
severity: high
component: backend/app/schemas/query.py
framework:
  - FastAPI
  - Pydantic
---

# MessageResponse Citations Type Mismatch

## Problem

Fetching conversation messages returned 500 with `ValidationError: citations — Input should be a valid dictionary`. The `/conversations/{id}/messages` endpoint crashed when serializing stored messages.

## Root Cause

`MessageResponse.citations` was typed as `dict | None` but the database column stores a JSON array (`[]` for user messages, `[{chunk_id, ...}]` for assistant messages). Pydantic rejected `[]` because it expected a dict.

## Solution

Changed the type from `dict` to `list` in `backend/app/schemas/query.py`:

```python
# Before
citations: dict | None = None

# After
citations: list | None = None
```

## Prevention

When defining Pydantic response schemas for JSONB columns, verify the actual stored shape (array vs object) by checking the ORM model's write path. A quick `SELECT citations FROM query_messages LIMIT 1` would have caught this immediately.
