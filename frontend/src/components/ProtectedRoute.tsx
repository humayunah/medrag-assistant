import { Navigate, Outlet } from "react-router-dom";
import { useAuthContext } from "./AuthProvider";

export function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuthContext();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#faf7f2]">
        <div className="animate-pulse text-slate-400 text-sm tracking-wide">
          Loading...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/signin" replace />;
  }

  return <Outlet />;
}
