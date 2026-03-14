import { Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { ColdStartGuard } from "./components/ColdStartGuard";
import { ProtectedRoute } from "./components/ProtectedRoute";

// Public pages
import Landing from "./pages/Landing";
import Demo from "./pages/Demo";
import SignIn from "./pages/auth/SignIn";
import SignUp from "./pages/auth/SignUp";
import ForgotPassword from "./pages/auth/ForgotPassword";
import ResetPassword from "./pages/auth/ResetPassword";
import AcceptInvitation from "./pages/auth/AcceptInvitation";

// Protected pages
import Dashboard from "./pages/Dashboard";
import QueryChat from "./pages/QueryChat";

// Admin pages
import Users from "./pages/admin/Users";
import AuditLog from "./pages/admin/AuditLog";
import Settings from "./pages/admin/Settings";

export default function App() {
  return (
    <ColdStartGuard>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/signin" element={<SignIn />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/accept-invitation" element={<AcceptInvitation />} />
        <Route path="/demo" element={<Demo />} />

        {/* Protected routes with app layout */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/query" element={<QueryChat />} />
            <Route path="/query/:conversationId" element={<QueryChat />} />
            <Route path="/admin/users" element={<Users />} />
            <Route path="/admin/audit" element={<AuditLog />} />
            <Route path="/admin/settings" element={<Settings />} />
          </Route>
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ColdStartGuard>
  );
}
