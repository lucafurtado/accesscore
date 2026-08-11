import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { backendApiUrl, setRefreshCookie } from "@/lib/server/auth-cookie";
import type { TokenResponse } from "@/types/api";

// This route is the only place the raw refresh token is ever visible to
// Next.js server code; it is immediately moved into an httpOnly cookie and
// never returned to the client. The browser only ever receives the access
// token, which lives in memory on the client and dies on reload/tab close.
export async function POST(request: Request): Promise<NextResponse> {
  const body = await request.json();

  const backendRes = await fetch(`${backendApiUrl()}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await backendRes.json();

  if (!backendRes.ok) {
    return NextResponse.json(data, { status: backendRes.status });
  }

  const tokens = data as TokenResponse;
  const cookieStore = await cookies();
  setRefreshCookie(cookieStore, tokens.refresh_token);

  return NextResponse.json({
    access_token: tokens.access_token,
    expires_in: tokens.expires_in,
  });
}
