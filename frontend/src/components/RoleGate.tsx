import type { ReactNode } from "react";
import { useAuthContext } from "./AuthProvider";
import type { AppRole } from "../types";

interface RoleGateProps {
  allowed: AppRole[];
  children: ReactNode;
  fallback?: ReactNode;
}

export function RoleGate({ allowed, children, fallback = null }: RoleGateProps) {
  const { role } = useAuthContext();
  if (!role || !allowed.includes(role)) return <>{fallback}</>;
  return <>{children}</>;
}
