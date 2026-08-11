import { setSession } from "@/lib/session-store";

// Shared by the API client's 401-retry path AND SessionProvider's initial
// bootstrap - anything in the app that might need a fresh access token goes
// through this one function. Refresh tokens are single-use/rotating
// server-side, so two independent callers hitting /api/auth/refresh at the
// same moment would race: whichever request the backend sees second is
// using an already-rotated-away token and fails. Collapsing every caller
// onto one shared in-flight promise avoids that - including React's
// Strict Mode dev-only double-invocation of effects, which would otherwise
// trigger exactly this race on mount.
let inFlight: Promise<string | null> | null = null;

export async function refreshAccessToken(): Promise<string | null> {
  if (!inFlight) {
    inFlight = fetch("/api/auth/refresh", { method: "POST" })
      .then(async (res) => {
        if (!res.ok) return null;
        const data = (await res.json()) as { access_token: string };
        setSession({ accessToken: data.access_token });
        return data.access_token;
      })
      .catch(() => null)
      .finally(() => {
        inFlight = null;
      });
  }
  return inFlight;
}
