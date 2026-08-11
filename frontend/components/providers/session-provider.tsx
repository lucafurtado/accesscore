"use client";

import { useEffect } from "react";

import { refreshAccessToken } from "@/lib/api/token-refresh";
import { usersApi } from "@/lib/api/users";
import { setSession } from "@/lib/session-store";

/**
 * Runs once at app load. The in-memory access token is gone on every full
 * page load/reload by design (it's never persisted), so this silently
 * exchanges the httpOnly refresh cookie for a fresh access token and
 * bootstraps the current user + effective permissions before anything
 * protected renders. If there's no valid session, status becomes
 * "unauthenticated" and the proxy/page-level checks redirect to /login.
 */
export function SessionProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const token = await refreshAccessToken();
      if (cancelled) return;

      if (!token) {
        setSession({ status: "unauthenticated", accessToken: null, user: null, permissions: [] });
        return;
      }

      try {
        const [user, permissions] = await Promise.all([usersApi.me(), usersApi.myPermissions()]);
        if (cancelled) return;
        setSession({ status: "authenticated", user, permissions });
      } catch {
        if (!cancelled) {
          setSession({ status: "unauthenticated", accessToken: null, user: null, permissions: [] });
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  return <>{children}</>;
}
