import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { clearSession, setSession } from "@/lib/session-store";
import type { UserResponse } from "@/types/api";

import { UserTable } from "./user-table";

const USERS: UserResponse[] = [
  {
    id: "u1",
    email: "carlos@accesscore.dev",
    full_name: "Carlos Silva",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    last_login_at: null,
  },
];

// Base UI's menu popup mounts asynchronously (portal + positioning), so
// every test below opens it and waits for role="menu" before asserting on
// its contents - querying immediately after the click is a common source of
// flakiness with floating-ui-based menus.
async function openRowActions() {
  await userEvent.click(screen.getByRole("button", { name: /actions for carlos/i }));
  return screen.findByRole("menu");
}

describe("UserTable", () => {
  beforeEach(() => clearSession());

  it("renders user rows with their status", () => {
    setSession({ permissions: [] });
    render(
      <UserTable users={USERS} isLoading={false} onEdit={vi.fn()} onManageRoles={vi.fn()} onToggleActive={vi.fn()} />,
    );
    expect(screen.getByText("Carlos Silva")).toBeInTheDocument();
    expect(screen.getByText("carlos@accesscore.dev")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("hides all row actions for a user with no relevant permissions", async () => {
    setSession({ permissions: [] });
    render(
      <UserTable users={USERS} isLoading={false} onEdit={vi.fn()} onManageRoles={vi.fn()} onToggleActive={vi.fn()} />,
    );

    const menu = await openRowActions();

    expect(within(menu).queryByText("Edit")).not.toBeInTheDocument();
    expect(within(menu).queryByText("Manage roles")).not.toBeInTheDocument();
    expect(within(menu).queryByText("Disable")).not.toBeInTheDocument();
  });

  it("shows only the actions matching the user's effective permissions", async () => {
    setSession({ permissions: ["users:update"] });
    render(
      <UserTable users={USERS} isLoading={false} onEdit={vi.fn()} onManageRoles={vi.fn()} onToggleActive={vi.fn()} />,
    );

    const menu = await openRowActions();

    expect(within(menu).getByText("Edit")).toBeInTheDocument();
    expect(within(menu).queryByText("Manage roles")).not.toBeInTheDocument();
    expect(within(menu).queryByText("Disable")).not.toBeInTheDocument();
  });

  it("invokes onEdit when the Edit action is clicked", async () => {
    setSession({ permissions: ["users:update"] });
    const onEdit = vi.fn();
    render(
      <UserTable users={USERS} isLoading={false} onEdit={onEdit} onManageRoles={vi.fn()} onToggleActive={vi.fn()} />,
    );

    const menu = await openRowActions();
    await userEvent.click(within(menu).getByText("Edit"));

    expect(onEdit).toHaveBeenCalledWith(USERS[0]);
  });
});
