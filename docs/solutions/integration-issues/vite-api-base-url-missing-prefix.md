---
title: "VITE_API_URL missing /api/v1 prefix causes 404 on demo endpoint"
category: integration-issues
date: 2026-03-14
tags:
  - vite
  - environment-variables
  - axios
  - base-url
  - vercel
  - render
  - cors
  - deployment
severity: medium
component: frontend/src/services/api.ts, frontend/src/pages/Demo.tsx
framework:
  - React
  - Vite
  - Axios
  - FastAPI
symptoms:
  - "Demo page shows 'Unable to Start Demo' with 'Request failed with status code 404'"
  - "POST to /demo/session returns 404"
  - "All other API routes also fail with 404 in production"
---

# VITE_API_URL Missing /api/v1 Prefix Causes 404 on All API Calls

## Problem

After deploying frontend to Vercel and backend to Render, the demo page at `https://medrag-assistant.vercel.app/demo` showed "Unable to Start Demo" with error "Request failed with status code 404".

## Root Cause

The Axios client in `frontend/src/services/api.ts` uses `VITE_API_URL` as its `baseURL`:

```typescript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api/v1",
});
```

The Vercel env var was set to `https://medrag-assistant.onrender.com` (no path prefix). The demo page calls `api.post("/demo/session")`, which resolved to:

```
https://medrag-assistant.onrender.com/demo/session  (404 - no such route)
```

But the FastAPI backend mounts the demo router at `/api/v1`:

```python
app.include_router(demo_router, prefix="/api/v1")
```

So the correct URL is:

```
https://medrag-assistant.onrender.com/api/v1/demo/session
```

## Solution

Update the `VITE_API_URL` environment variable in Vercel to include the `/api/v1` prefix:

```
VITE_API_URL=https://medrag-assistant.onrender.com/api/v1
```

Then redeploy.

## Prevention

When setting API base URLs in environment variables, always include the full path prefix that the backend expects. The local fallback (`"/api/v1"`) already includes the prefix — production env vars should match.
