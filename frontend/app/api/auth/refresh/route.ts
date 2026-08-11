import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { backendApiUrl, clearRefreshCookie, REFRESH_COOKIE_NAME, setRefreshCookie } from "@/lib/server/auth-cookie";
import type { TokenResponse } from "@/types/api";

// Reads the httpOnly refresh-token cookie server-side (client JS never has
// access to it), exchanges it with FastAPI, and rotates the cookie to the
// new refresh token - the backend's rotation makes the old one single-use,
// so the cookie must always be updated to the latest value or the very next
// refresh attempt would fail.
export async function POST(): Promise<NextResponse> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get(REFRESH_COOKIE_NAME)?.value;

  if (!refreshToken) {
    return NextResponse.json({ detail: "No active session" }, { status: 401 });
  }

  const backendRes = await fetch(`${backendApiUrl()}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  const data = await backendRes.json();

  if (!backendRes.ok) {
    clearRefreshCookie(cookieStore);
    return NextResponse.json(data, { status: backendRes.status });
  }

  const tokens = data as TokenResponse;
  setRefreshCookie(cookieStore, tokens.refresh_token);

  return NextResponse.json({
    access_token: tokens.access_token,
    expires_in: tokens.expires_in,
  });
}
