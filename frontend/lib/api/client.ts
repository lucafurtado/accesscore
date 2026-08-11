import { refreshAccessToken } from "@/lib/api/token-refresh";
import { clearSession, getSessionState } from "@/lib/session-store";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown) {
    super(ApiError.messageFor(detail));
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  private static messageFor(detail: unknown): string {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0 && typeof detail[0]?.msg === "string") {
      // FastAPI 422 validation error shape: [{ loc, msg, type }, ...]
      return detail.map((d: { msg: string }) => d.msg).join("; ");
    }
    return "Request failed";
  }
}

function redirectToLogin(): void {
  // This module is called from plain fetch wrappers, not React components or
  // event handlers, so neither redirect() (render-phase only) nor
  // useRouter() (hook, needs component context) are usable here. A hard
  // navigation is also fine on session expiry: it clears all in-memory
  // state (the access token, session store) in one step.
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/login";
  }
}

async function parseErrorBody(res: Response): Promise<unknown> {
  try {
    const data = await res.json();
    return data?.detail ?? data;
  } catch {
    return null;
  }
}

async function request<T>(path: string, options: RequestInit = {}, allowRetry = true): Promise<T> {
  const { accessToken } = getSessionState();
  const headers = new Headers(options.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && allowRetry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return request<T>(path, options, false);
    }
    clearSession();
    redirectToLogin();
    throw new ApiError(401, "Session expired");
  }

  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorBody(res));
  }

  if (res.status === 204) return undefined as T;

  return (await res.json()) as T;
}

export const apiClient = {
  get: <T,>(path: string, options?: RequestInit) => request<T>(path, { ...options, method: "GET" }),
  post: <T,>(path: string, body?: unknown, options?: RequestInit) =>
    request<T>(path, {
      ...options,
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  put: <T,>(path: string, body?: unknown, options?: RequestInit) =>
    request<T>(path, {
      ...options,
      method: "PUT",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  delete: <T,>(path: string, options?: RequestInit) =>
    request<T>(path, { ...options, method: "DELETE" }),
};
