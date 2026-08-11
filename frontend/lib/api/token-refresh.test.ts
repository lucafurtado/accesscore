import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearSession, getSessionState } from "@/lib/session-store";

import { refreshAccessToken } from "./token-refresh";

describe("refreshAccessToken", () => {
  beforeEach(() => {
    clearSession();
    vi.restoreAllMocks();
  });

  it("collapses concurrent calls into a single fetch (refresh tokens are single-use)", async () => {
    let resolveFetch!: (value: Response) => void;
    const pending = new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
    const fetchSpy = vi.spyOn(global, "fetch").mockReturnValue(pending);

    const p1 = refreshAccessToken();
    const p2 = refreshAccessToken();

    expect(fetchSpy).toHaveBeenCalledTimes(1);

    resolveFetch(new Response(JSON.stringify({ access_token: "new-token" }), { status: 200 }));

    const [r1, r2] = await Promise.all([p1, p2]);
    expect(r1).toBe("new-token");
    expect(r2).toBe("new-token");
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("returns null (not a throw) when the backend rejects the refresh", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(new Response(null, { status: 401 }));
    const result = await refreshAccessToken();
    expect(result).toBeNull();
  });

  it("allows a fresh fetch once the previous call has resolved", async () => {
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "t1" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: "t2" }), { status: 200 }));

    const t1 = await refreshAccessToken();
    const t2 = await refreshAccessToken();

    expect(t1).toBe("t1");
    expect(t2).toBe("t2");
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("updates the session store with the new access token on success", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ access_token: "abc" }), { status: 200 }),
    );
    await refreshAccessToken();
    expect(getSessionState().accessToken).toBe("abc");
  });
});
