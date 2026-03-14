---
title: "Python 'from module import variable' creates stale binding for deferred-init state"
category: runtime-errors
date: 2026-03-14
tags:
  - python-import-semantics
  - name-binding
  - fastapi
  - sqlalchemy-async
  - health-check
  - deferred-initialization
severity: high
component: backend/app/api/v1/health.py, backend/app/core/database.py
framework:
  - FastAPI
  - SQLAlchemy
symptoms:
  - "/health/ready always returns {\"database\": \"not_initialized\"} despite successful engine creation"
  - "Startup logs confirm db_engine_initialized but health check does not reflect it"
  - "/health/live returns 200 OK normally"
  - "No database connection errors in logs"
---

# Python Import Binding Bug: Stale Reference to Deferred-Init Module State

## Problem

After deploying the FastAPI backend to Render, `/health/ready` always returned:

```json
{"status": "degraded", "version": "0.1.0", "checks": {"database": "not_initialized"}}
```

Debug logging confirmed `init_engine()` ran successfully at startup. The database was connected. Yet the health check never saw it.

## Root Cause

In `health.py`:

```python
from app.core.database import async_session_factory
```

This creates a **local name binding** to the value of `async_session_factory` at import time -- which is `None`, because the database hasn't been initialized yet.

In `database.py`, the variable starts as:

```python
async_session_factory: async_sessionmaker[AsyncSession] | None = None
```

When `init_engine()` runs during FastAPI's lifespan startup and reassigns this module-level variable, it rebinds the name **in the `database` module's namespace**. But the name `async_session_factory` in `health.py` still points to the original `None`.

**Python's `from X import Y` creates a snapshot binding, not a live reference.**

## Investigation Steps

1. **Checked environment variables** -- Confirmed `DATABASE_URL` and `DATABASE_POOL_URL` were set in Render. Ruled out missing config.
2. **Added debug logging to lifespan** -- Confirmed `init_engine()` executed and logged `db_engine_initialized`. Ruled out startup failure.
3. **Added `statement_cache_size=0`** for pgbouncer compatibility -- Fixed a separate issue but not this one.
4. **Traced the import chain** -- Found that `from app.core.database import async_session_factory` captured `None` at import time.

## Solution

**Before (broken):**

```python
# health.py
from app.core.database import async_session_factory

async def readiness():
    if async_session_factory:          # always None -- stale binding
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
```

**After (fixed):**

```python
# health.py
from app.core import database          # import the MODULE, not the variable

async def readiness():
    if database.async_session_factory:  # attribute lookup at call time -- always current
        async with database.async_session_factory() as session:
            await session.execute(text("SELECT 1"))
```

## Why It Works

- `from module import name` -- binds to the **object** at import time. Reassignment in the source module doesn't propagate.
- `import module; module.name` -- performs an **attribute lookup** on the module object at access time, always reflecting the current value.

## The Rule

> Never use `from module import variable` for any variable that is `None` at import time and assigned later. Use `import module` with attribute access, or use a getter function.

## When `from X import Y` IS Safe

- `Y` is a **function or class** (rarely reassigned)
- `Y` is a **true constant** (never reassigned after module load)
- `Y` is an **object created at import time** (e.g., `settings = Settings()`)

## Prevention

### Code Review Checklist

- [ ] No `from module import variable` where `variable` is mutable module-level state
- [ ] All deferred-init variables accessed via getter function or module attribute
- [ ] Module-level variables initialized to `None` that are later reassigned are NOT imported by name

### Recommended Patterns

| Situation | Pattern |
|-----------|---------|
| Simple access | `import module; module.var` |
| Multiple consumers | Getter function (`get_engine()`) |
| FastAPI routes | `Depends()` + getter |
| Lifecycle management | FastAPI lifespan + `app.state` |

### Regression Test

```python
from fastapi.testclient import TestClient

def test_health_ready_shows_database_ok(app_with_lifespan):
    """Regression: health check must reflect initialized database."""
    client = TestClient(app_with_lifespan)
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["checks"]["database"] == "ok"
```

## Related Files

| File | Pattern | Safe? |
|------|---------|-------|
| `app/api/v1/health.py` | `from app.core import database` + `database.async_session_factory` | Yes |
| `app/api/v1/auth.py` | `from app.core.database import get_db` | Yes (function import) |
| `app/services/document_processor.py` | `from app.core.database import _get_session_factory` | Yes (function import) |
| `app/api/v1/queries.py` | Lazy singleton via `_get_rag_service()` getter | Yes |
| `app/core/config.py` | `settings = Settings()` created at import time | Yes (not deferred) |
