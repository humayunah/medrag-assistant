---
title: "Demo page returns 429 due to overly restrictive rate limit default"
category: runtime-errors
date: 2026-03-14
tags:
  - rate-limiting
  - demo-mode
  - deployment
  - in-memory-state
severity: low
component: backend/app/core/config.py
framework:
  - FastAPI
  - SlowAPI
---

# Demo Rate Limit Too Restrictive (429 on Demo Page)

## Problem

After deploying to Render, clicking "Try a suggestion" on the demo page returned **"Request failed with status code 429"**. The demo became unusable after just a few requests.

## Root Cause

`RATE_LIMIT_DEMO` defaulted to `5` per hour per IP — far too low for realistic usage or testing. Additionally, the rate limiter uses in-memory storage (`SlowAPI` default), which resets on every Render deploy, making the limit unpredictable during active development.

## Solution

Increased the default from 5 to 30 requests per hour in `backend/app/core/config.py`:

```python
RATE_LIMIT_DEMO: int = 30  # per hour per IP
```

The value is also overridable via the `RATE_LIMIT_DEMO` environment variable on Render without redeploying code.

## Prevention

When setting rate limit defaults, consider realistic usage patterns — especially for demo/trial flows where users explore multiple features in a single session. In-memory rate limiters reset on deploy; use Redis-backed storage for production consistency.
