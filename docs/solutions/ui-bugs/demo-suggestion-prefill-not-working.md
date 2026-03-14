---
title: "Demo suggestion click does not prefill query input on /query page"
category: ui-bugs
date: 2026-03-14
tags:
  - react-router
  - navigation-state
  - demo-mode
  - useLocation
severity: low
component: frontend/src/pages/QueryChat.tsx, frontend/src/pages/Demo.tsx
framework:
  - React
  - React Router
---

# Demo Suggestion Click Does Not Prefill Query Input

## Problem

Clicking a suggestion card on the demo page navigated to `/query` but the input field remained empty. The user had to manually type or paste the question.

## Root Cause

`Demo.tsx` passed the suggestion via React Router navigation state (`navigate("/query", { state: { prefill: query } })`), but `QueryChat.tsx` never read `location.state.prefill`. The input was initialized as `useState("")` with no effect to pick up the prefill value.

## Solution

Added `useLocation` and a `useEffect` in `QueryChat.tsx` to read and apply the prefill:

```typescript
import { useLocation } from "react-router-dom";

// Inside the component:
const location = useLocation();

const prefillHandled = useRef(false);
useEffect(() => {
  const prefill = (location.state as { prefill?: string } | null)?.prefill;
  if (prefill && !prefillHandled.current) {
    prefillHandled.current = true;
    setInputValue(prefill);
    window.history.replaceState({}, "");
  }
}, [location.state]);
```

The `prefillHandled` ref prevents double-execution in React StrictMode, and `replaceState` clears the state so a page refresh doesn't re-trigger.

## Prevention

When passing data between pages via React Router state, always verify both the sender and receiver are connected. Search for `location.state` usage when adding `navigate(..., { state })` calls.
