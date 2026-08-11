"use client";

import type { ReactNode } from "react";

import { useHasPermission } from "@/hooks/use-permissions";

interface PermissionGateProps {
  permission: string;
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Hides `children` when the current user lacks `permission`. This is UX
 * only - it makes the UI match what the user can actually do, nothing more.
 * The backend re-checks every permission on every request regardless of
 * what this component renders; removing or bypassing this component cannot
 * grant access to anything the API wouldn't already allow.
 */
export function PermissionGate({ permission, children, fallback = null }: PermissionGateProps) {
  const hasPermission = useHasPermission(permission);
  return hasPermission ? <>{children}</> : <>{fallback}</>;
}
