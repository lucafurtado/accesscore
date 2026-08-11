import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { proxy } from "./proxy";

describe("proxy (coarse auth gate)", () => {
  it("redirects to /login when visiting /dashboard with no session cookie", () => {
    const req = new NextRequest("http://localhost:3000/dashboard");
    const res = proxy(req);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/login");
  });

  it("redirects nested /dashboard/* routes too", () => {
    const req = new NextRequest("http://localhost:3000/dashboard/users");
    const res = proxy(req);
    expect(res.headers.get("location")).toBe("http://localhost:3000/login");
  });

  it("lets /dashboard through when the refresh-token cookie is present", () => {
    const req = new NextRequest("http://localhost:3000/dashboard", {
      headers: { cookie: "accesscore_refresh_token=abc123" },
    });
    const res = proxy(req);
    expect(res.status).not.toBe(307);
  });

  it("redirects an already-authenticated visit to /login back to /dashboard", () => {
    const req = new NextRequest("http://localhost:3000/login", {
      headers: { cookie: "accesscore_refresh_token=abc123" },
    });
    const res = proxy(req);
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://localhost:3000/dashboard");
  });

  it("lets an unauthenticated visit to /login through", () => {
    const req = new NextRequest("http://localhost:3000/login");
    const res = proxy(req);
    expect(res.status).not.toBe(307);
  });
});
