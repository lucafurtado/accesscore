import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/token-refresh", () => ({
  refreshAccessToken: vi.fn(),
}));

import { refreshAccessToken } from "@/lib/api/token-refresh";
import { clearSession, getSessionState, setSession } from "@/lib/session-store";

import { apiClient, ApiError } from "./client";

describe("apiClient", () => {
  beforeEach(() => {
    clearSession();
    vi.restoreAllMocks();
    vi.mocked(refreshAccessToken).mockReset();
  });

  it("attaches the in-memory access token as a Bearer header", async () => {
    setSession({ accessToken: "my-token" });
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    await apiClient.get("/users/me");

    const [, options] = fetchSpy.mock.calls[0];
    const headers = options?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer my-token");
  });

  it("retries once after a successful refresh on 401", async () => {
    setSession({ accessToken: "expired" });
    // The real refreshAccessToken() updates the session store as a side
    // effect (see token-refresh.ts); replicate that here since it's mocked.
    vi.mocked(refreshAccessToken).mockImplementation(async () => {
      setSession({ accessToken: "fresh-token" });
      return "fresh-token";
    });

    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    const result = await apiClient.get<{ ok: boolean }>("/users/me");

    expect(result).toEqual({ ok: true });
    expect(fetchSpy).toHaveBeenCalledTimes(2);
    // The retried request must use the freshly refreshed token, not the stale one.
    const [, retryOptions] = fetchSpy.mock.calls[1];
    expect((retryOptions?.headers as Headers).get("Authorization")).toBe("Bearer fresh-token");
  });

  it("does not retry more than once even if the retried request also 401s", async () => {
    setSession({ accessToken: "expired" });
    vi.mocked(refreshAccessToken).mockResolvedValue("fresh-token");
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(new Response(null, { status: 401 }));

    await expect(apiClient.get("/users/me")).rejects.toThrow(ApiError);
    // One initial attempt + exactly one retry, never an infinite loop.
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("clears the session and throws when refresh fails after a 401", async () => {
    setSession({ status: "authenticated", accessToken: "expired" });
    vi.mocked(refreshAccessToken).mockResolvedValue(null);
    vi.spyOn(global, "fetch").mockResolvedValue(new Response(null, { status: 401 }));

    await expect(apiClient.get("/users/me")).rejects.toThrow(ApiError);
    expect(getSessionState().status).toBe("unauthenticated");
    expect(getSessionState().accessToken).toBeNull();
  });

  it("surfaces the backend's detail message for non-401 errors", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Role not found" }), { status: 404 }),
    );

    await expect(apiClient.get("/roles/unknown")).rejects.toMatchObject({
      status: 404,
      message: "Role not found",
    });
  });

  it("joins FastAPI 422 validation error messages", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [{ loc: ["body", "email"], msg: "value is not a valid email address", type: "value_error" }],
        }),
        { status: 422 },
      ),
    );

    await expect(apiClient.post("/users", {})).rejects.toMatchObject({
      status: 422,
      message: "value is not a valid email address",
    });
  });

  it("returns undefined for 204 No Content responses", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
    const result = await apiClient.delete("/users/1/roles/2");
    expect(result).toBeUndefined();
  });
});
