---
title: "Demo users redirected to login when navigating to protected routes"
category: logic-errors
date: 2026-03-14
tags:
  - demo-mode
  - authentication
  - protected-routes
  - react-router
  - supabase-auth
severity: medium
component: frontend/src/hooks/useAuth.ts, frontend/src/pages/Demo.tsx, frontend/src/components/ProtectedRoute.tsx
framework:
  - React
  - Supabase
---

# Demo Users Redirected to Login on Protected Routes

## Problem

After clicking a suggestion on the demo page, users were redirected to `/signin` instead of navigating to `/query`. The demo session token was acquired successfully, but navigation to any protected route failed.

## Root Cause

`ProtectedRoute` checks `isAuthenticated`, which is `!!state.session` — a Supabase session. Demo mode sets a custom JWT on the axios interceptor but never creates a Supabase session. Since `state.session` is always `null` for demo users, `isAuthenticated` is `false`, and `ProtectedRoute` redirects to `/signin`.

## Solution

Added an `isDemo` flag to auth state and an `enterDemoMode()` function:

```typescript
// useAuth.ts
const enterDemoMode = useCallback(() => {
  setState((s) => ({ ...s, isDemo: true, loading: false }));
}, []);

return {
  ...state,
  isAuthenticated: !!state.session || state.isDemo,  // demo users pass the gate
  enterDemoMode,
};
```

Called `enterDemoMode()` in `Demo.tsx` after acquiring the demo token:

```typescript
const { enterDemoMode } = useAuthContext();
// after api.post("/demo/session") succeeds:
enterDemoMode();
```

Also added `isDemo: false` to all `setState` calls (including `signOut`) to satisfy TypeScript's `AuthState` interface.

## Prevention

When adding alternative auth flows (demo, API keys, SSO), ensure the auth guard checks all valid authentication methods, not just one provider's session state.
