import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { backendApiUrl, clearRefreshCookie, REFRESH_COOKIE_NAME } from "@/lib/server/auth-cookie";

export async function POST(): Promise<NextResponse> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get(REFRESH_COOKIE_NAME)?.value;

  if (refreshToken) {
    // Best-effort: revoke server-side, but clear the cookie regardless so
    // the browser is logged out even if the backend call fails.
    await fetch(`${backendApiUrl()}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => undefined);
  }

  clearRefreshCookie(cookieStore);
  return new NextResponse(null, { status: 204 });
}
