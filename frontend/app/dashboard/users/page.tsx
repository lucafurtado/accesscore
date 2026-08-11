"use client";

import { useState } from "react";
import { Plus, Search } from "lucide-react";
import { toast } from "sonner";

import { PageHeader } from "@/components/common/page-header";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { CursorPagination } from "@/components/common/cursor-pagination";
import { ErrorState } from "@/components/common/state-message";
import { PermissionGate } from "@/components/permission-gate";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { UserFormDialog } from "@/components/users/user-form-dialog";
import { UserRolesDialog } from "@/components/users/user-roles-dialog";
import { UserTable } from "@/components/users/user-table";
import { useAsyncData } from "@/hooks/use-async-data";
import { useCursorPagination } from "@/hooks/use-cursor-pagination";
import { ApiError } from "@/lib/api/client";
import { usersApi } from "@/lib/api/users";
import type { UserResponse } from "@/types/api";

type ActiveFilter = "all" | "active" | "inactive";

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<ActiveFilter>("all");
  const pagination = useCursorPagination();

  const [formOpen, setFormOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserResponse | null>(null);
  const [rolesUser, setRolesUser] = useState<UserResponse | null>(null);
  const [toggleTarget, setToggleTarget] = useState<UserResponse | null>(null);
  const [isToggling, setIsToggling] = useState(false);

  const { data, isLoading, error, reload } = useAsyncData(
    () =>
      usersApi.list({
        cursor: pagination.cursor,
        limit: 20,
        q: search || undefined,
        is_active: activeFilter === "all" ? undefined : activeFilter === "active",
      }),
    [pagination.cursor, search, activeFilter],
  );

  function handleSearchChange(value: string) {
    setSearch(value);
    pagination.reset();
  }

  function handleFilterChange(value: ActiveFilter) {
    setActiveFilter(value);
    pagination.reset();
  }

  function openCreate() {
    setEditingUser(null);
    setFormOpen(true);
  }

  function openEdit(user: UserResponse) {
    setEditingUser(user);
    setFormOpen(true);
  }

  async function confirmToggleActive() {
    if (!toggleTarget) return;
    setIsToggling(true);
    try {
      if (toggleTarget.is_active) {
        await usersApi.disable(toggleTarget.id);
        toast.success(`Disabled ${toggleTarget.email}`);
      } else {
        await usersApi.reactivate(toggleTarget.id);
        toast.success(`Reactivated ${toggleTarget.email}`);
      }
      setToggleTarget(null);
      reload();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Action failed.");
    } finally {
      setIsToggling(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Users"
        description="Manage user accounts, roles, and access."
        actions={
          <PermissionGate permission="users:create">
            <Button onClick={openCreate}>
              <Plus className="mr-1.5 h-4 w-4" />
              Create user
            </Button>
          </PermissionGate>
        }
      />

      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative max-w-xs flex-1">
          <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 h-4 w-4 -translate-y-1/2" />
          <Input
            placeholder="Search by email…"
            className="pl-8"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
          />
        </div>
        <Select value={activeFilter} onValueChange={(v) => handleFilterChange(v as ActiveFilter)}>
          <SelectTrigger className="w-[160px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="active">Active only</SelectItem>
            <SelectItem value="inactive">Disabled only</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {error ? (
        <ErrorState title="Couldn't load users" onRetry={reload} />
      ) : (
        <>
          <UserTable
            users={data?.items ?? []}
            isLoading={isLoading}
            onEdit={openEdit}
            onManageRoles={setRolesUser}
            onToggleActive={setToggleTarget}
          />
          <CursorPagination
            onPrevious={pagination.goPrevious}
            onNext={() => data?.next_cursor && pagination.goNext(data.next_cursor)}
            canGoPrevious={pagination.canGoPrevious}
            canGoNext={!!data?.has_more}
          />
        </>
      )}

      <UserFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        user={editingUser}
        onSaved={reload}
      />
      <UserRolesDialog open={!!rolesUser} onOpenChange={() => setRolesUser(null)} user={rolesUser} />
      <ConfirmDialog
        open={!!toggleTarget}
        onOpenChange={(open) => !open && setToggleTarget(null)}
        title={toggleTarget?.is_active ? "Disable this user?" : "Reactivate this user?"}
        description={
          toggleTarget?.is_active
            ? `${toggleTarget?.email} will lose access immediately and all of their active sessions will be revoked.`
            : `${toggleTarget?.email} will regain access to the platform.`
        }
        confirmLabel={toggleTarget?.is_active ? "Disable" : "Reactivate"}
        destructive={toggleTarget?.is_active}
        isLoading={isToggling}
        onConfirm={confirmToggleActive}
      />
    </div>
  );
}
