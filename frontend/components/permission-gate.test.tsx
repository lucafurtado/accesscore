import { beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { clearSession, setSession } from "@/lib/session-store";

import { PermissionGate } from "./permission-gate";

describe("PermissionGate", () => {
  beforeEach(() => clearSession());

  it("renders children when the user has the required permission", () => {
    setSession({ permissions: ["users:read", "roles:read"] });
    render(
      <PermissionGate permission="users:read">
        <button>Create user</button>
      </PermissionGate>,
    );
    expect(screen.getByText("Create user")).toBeInTheDocument();
  });

  it("hides children when the user lacks the required permission - UX only, not a security boundary", () => {
    setSession({ permissions: ["users:read"] });
    render(
      <PermissionGate permission="users:create">
        <button>Create user</button>
      </PermissionGate>,
    );
    expect(screen.queryByText("Create user")).not.toBeInTheDocument();
  });

  it("renders the fallback (defaulting to nothing) when provided", () => {
    setSession({ permissions: [] });
    render(
      <PermissionGate permission="users:create" fallback={<span>No access</span>}>
        <button>Create user</button>
      </PermissionGate>,
    );
    expect(screen.getByText("No access")).toBeInTheDocument();
    expect(screen.queryByText("Create user")).not.toBeInTheDocument();
  });
});
