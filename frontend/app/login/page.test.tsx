import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const pushMock = vi.fn();
const refreshMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, refresh: refreshMock }),
}));

vi.mock("@/lib/api/auth", () => ({
  loginRequest: vi.fn(),
}));
vi.mock("@/lib/api/users", () => ({
  usersApi: { me: vi.fn(), myPermissions: vi.fn() },
}));

import { ApiError } from "@/lib/api/client";
import { loginRequest } from "@/lib/api/auth";
import { usersApi } from "@/lib/api/users";
import { clearSession, getSessionState } from "@/lib/session-store";

import LoginPage from "./page";

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearSession();
  });

  it("logs in, bootstraps the session, and redirects to /dashboard", async () => {
    vi.mocked(loginRequest).mockResolvedValue({ access_token: "tok", expires_in: 900 });
    vi.mocked(usersApi.me).mockResolvedValue({
      id: "1",
      email: "admin@accesscore.dev",
      full_name: "Admin",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      last_login_at: null,
    });
    vi.mocked(usersApi.myPermissions).mockResolvedValue(["users:read"]);

    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText(/email/i), "admin@accesscore.dev");
    await userEvent.type(screen.getByLabelText(/password/i), "correct-password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/dashboard"));
    expect(getSessionState().status).toBe("authenticated");
    expect(getSessionState().permissions).toEqual(["users:read"]);
  });

  it("shows the backend's error message on invalid credentials and does not navigate", async () => {
    vi.mocked(loginRequest).mockRejectedValue(new ApiError(401, "Invalid credentials"));

    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText(/email/i), "admin@accesscore.dev");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials");
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("disables the submit button while the request is in flight", async () => {
    let resolveLogin!: (value: { access_token: string; expires_in: number }) => void;
    vi.mocked(loginRequest).mockReturnValue(
      new Promise((resolve) => {
        resolveLogin = resolve;
      }),
    );

    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText(/email/i), "admin@accesscore.dev");
    await userEvent.type(screen.getByLabelText(/password/i), "correct-password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByRole("button", { name: /signing in/i })).toBeDisabled();

    resolveLogin({ access_token: "tok", expires_in: 900 });
    vi.mocked(usersApi.me).mockResolvedValue({
      id: "1",
      email: "admin@accesscore.dev",
      full_name: null,
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      last_login_at: null,
    });
    vi.mocked(usersApi.myPermissions).mockResolvedValue([]);
    await waitFor(() => expect(pushMock).toHaveBeenCalled());
  });
});
