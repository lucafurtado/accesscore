import { describe, expect, it } from "vitest";

import { clearSession, getSessionState, setSession, subscribeSession } from "./session-store";
import type { UserResponse } from "@/types/api";

const FAKE_USER: UserResponse = {
  id: "1",
  email: "a@b.com",
  full_name: null,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  last_login_at: null,
};

describe("session-store", () => {
  it("merges partial updates into the existing state", () => {
    setSession({ status: "authenticated", accessToken: "t" });
    expect(getSessionState().status).toBe("authenticated");
    expect(getSessionState().accessToken).toBe("t");
  });

  it("clearSession resets to unauthenticated with no token, user, or permissions", () => {
    setSession({ status: "authenticated", accessToken: "t", user: FAKE_USER, permissions: ["a"] });
    clearSession();
    const state = getSessionState();
    expect(state).toEqual({
      status: "unauthenticated",
      accessToken: null,
      user: null,
      permissions: [],
    });
  });

  it("notifies subscribers on every change and stops after unsubscribing", () => {
    let calls = 0;
    const unsubscribe = subscribeSession(() => {
      calls++;
    });

    setSession({ status: "loading" });
    expect(calls).toBe(1);

    unsubscribe();
    setSession({ status: "authenticated" });
    expect(calls).toBe(1);
  });
});
