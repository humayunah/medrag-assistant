---
title: "SQLAlchemy sends enum NAME instead of VALUE to PostgreSQL"
category: database-issues
date: 2026-03-14
tags:
  - sqlalchemy
  - postgresql
  - enum
  - asyncpg
  - values-callable
severity: high
component: backend/app/models/user_profile.py, backend/app/models/document.py, backend/app/models/invitation.py
framework:
  - SQLAlchemy
  - asyncpg
  - PostgreSQL
---

# SQLAlchemy Sends Enum NAME Instead of VALUE to PostgreSQL

## Problem

Seeding demo data failed with `invalid input value for enum app_role: "STAFF"`. The PostgreSQL `app_role` type expects lowercase values (`staff`, `admin`) but SQLAlchemy was sending uppercase member names (`STAFF`, `ADMIN`). This affected all ORM inserts using enum columns — signup and invitations would also have failed.

## Root Cause

SQLAlchemy's `Enum()` column type uses the Python enum member's `.name` attribute by default, not `.value`. Given `AppRole.STAFF = "staff"`, the ORM sends `"STAFF"` (the name) while the DB enum was created with `"staff"` (the value).

## Solution

Added `values_callable` to every `Enum()` column definition to force SQLAlchemy to use `.value`:

```python
# Before — sends "STAFF" (name)
role: Mapped[AppRole] = mapped_column(
    Enum(AppRole, name="app_role", create_type=False),
)

# After — sends "staff" (value)
role: Mapped[AppRole] = mapped_column(
    Enum(
        AppRole,
        name="app_role",
        create_type=False,
        values_callable=lambda e: [x.value for x in e],
    ),
)
```

Applied to all 4 affected columns across 3 model files:
- `user_profile.py` — `role` (AppRole)
- `document.py` — `status` (DocumentStatus)
- `invitation.py` — `role` (AppRole), `status` (InvitationStatus)

## Prevention

When using Python `str` enums with SQLAlchemy and PostgreSQL, always add `values_callable=lambda e: [x.value for x in e]` to the `Enum()` type. Without it, SQLAlchemy defaults to sending `.name` (uppercase) which won't match DB enums created with lowercase values.
