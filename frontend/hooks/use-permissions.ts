"use client";

import { useSession } from "@/hooks/use-session";

export function usePermissions(): string[] {
  return useSession().permissions;
}

export function useHasPermission(permission: string): boolean {
  return usePermissions().includes(permission);
}
