import { NextRequest, NextResponse } from "next/server";

import { REFRESH_COOKIE_NAME } from "@/lib/server/auth-cookie";

// Coarse gate only: checks whether a refresh-token cookie is present, not
// whether it's still valid. It cannot drive the actual client-side token
// refresh (no access to in-page fetch calls after hydration), so real
// session validation happens in SessionProvider on the client - this just
// avoids flashing protected content before that runs, and blocks direct
// navigation to /dashboard with no session at all.
export function proxy(request: NextRequest): NextResponse {
  const hasSession = request.cookies.has(REFRESH_COOKIE_NAME);
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/dashboard") && !hasSession) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (pathname === "/login" && hasSession) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login"],
};
