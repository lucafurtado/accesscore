import { ApiError } from "@/lib/api/client";

export interface LoginResult {
  access_token: string;
  expires_in: number;
}

/** Calls the Next.js BFF route, never FastAPI directly - see app/api/auth/login/route.ts. */
export async function loginRequest(email: string, password: string): Promise<LoginResult> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(res.status, data.detail ?? "Login failed");
  }

  return res.json() as Promise<LoginResult>;
}

export async function logoutRequest(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
}
