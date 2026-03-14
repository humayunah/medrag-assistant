---
title: "Demo returns empty results due to tenant ID mismatch between seed and endpoint"
category: logic-errors
date: 2026-03-14
tags:
  - demo-mode
  - multi-tenant
  - data-seeding
  - uuid
severity: high
component: scripts/seed_demo_data.py, backend/app/api/v1/demo.py
framework:
  - FastAPI
  - SQLAlchemy
---

# Demo Returns Empty Results — Tenant ID Mismatch

## Problem

After seeding 60 demo documents, the demo page showed "No documents yet" and all API responses returned empty arrays. The seed script ran successfully but no data appeared in the demo session.

## Root Cause

The demo endpoint (`demo.py`) hardcodes `DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000000"` and issues JWTs scoped to that tenant. The seed script (`seed_demo_data.py`) created a `Tenant` without specifying an `id`, so SQLAlchemy auto-generated a random UUID (e.g., `51bd609e-...`). All 60 documents were seeded under the random tenant, but demo queries were scoped to the all-zeros tenant — which had zero documents.

## Solution

Added a fixed `DEMO_TENANT_ID` to the seed script matching the demo endpoint:

```python
# seed_demo_data.py
DEMO_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")

# Pass it explicitly when creating the tenant
tenant = Tenant(
    id=DEMO_TENANT_ID,
    name=DEMO_TENANT_NAME,
    slug=DEMO_TENANT_SLUG,
    settings={},
)
```

Re-ran with `--clear` to replace the old data under the correct tenant.

## Prevention

When multiple components reference the same entity by ID (demo endpoint, seed script, tests), define the ID as a shared constant or import it from a single source of truth. Comments like "must match seed_demo_data.py" are insufficient — they go stale silently.
