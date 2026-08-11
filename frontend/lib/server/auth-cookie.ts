import type { cookies as cookiesFn } from "next/headers";

type CookieStore = Awaited<ReturnType<typeof cookiesFn>>;

export const REFRESH_COOKIE_NAME = "accesscore_refresh_token";

// Matches the backend's default REFRESH_TOKEN_EXPIRE_DAYS (7). The cookie's
// lifetime is advisory only - the backend is what actually enforces expiry
// and revocation on every /auth/refresh call.
const REFRESH_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

export function backendApiUrl(): string {
  return process.env.BACKEND_API_URL ?? "http://localhost:8000/api/v1";
}

export function setRefreshCookie(cookies: CookieStore, refreshToken: string): void {
  cookies.set(REFRESH_COOKIE_NAME, refreshToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: REFRESH_TOKEN_MAX_AGE_SECONDS,
  });
}

export function clearRefreshCookie(cookies: CookieStore): void {
  cookies.delete(REFRESH_COOKIE_NAME);
}
