"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState } from "@/components/common/state-message";
import { PermissionGate } from "@/components/permission-gate";
import { RoleFormDialog } from "@/components/roles/role-form-dialog";
import { RolePermissionsDialog } from "@/components/roles/role-permissions-dialog";
import { RoleTable } from "@/components/roles/role-table";
import { Button } from "@/components/ui/button";
import { useAsyncData } from "@/hooks/use-async-data";
import { ApiError } from "@/lib/api/client";
import { rolesApi } from "@/lib/api/roles";
import type { RoleResponse } from "@/types/api";

export default function RolesPage() {
  const { data: roles, isLoading, error, reload } = useAsyncData(() => rolesApi.list(), []);

  const [formOpen, setFormOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<RoleResponse | null>(null);
  const [permissionsRole, setPermissionsRole] = useState<RoleResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<RoleResponse | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  function openCreate() {
    setEditingRole(null);
    setFormOpen(true);
  }

  function openEdit(role: RoleResponse) {
    setEditingRole(role);
    setFormOpen(true);
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await rolesApi.delete(deleteTarget.id);
      toast.success(`Deleted "${deleteTarget.name}"`);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to delete role.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Roles"
        description="Group permissions into roles and assign them to users."
        actions={
          <PermissionGate permission="roles:manage">
            <Button onClick={openCreate}>
              <Plus className="mr-1.5 h-4 w-4" />
              Create role
            </Button>
          </PermissionGate>
        }
      />

      {error ? (
        <ErrorState title="Couldn't load roles" onRetry={reload} />
      ) : (
        <RoleTable
          roles={roles ?? []}
          isLoading={isLoading}
          onEdit={openEdit}
          onManagePermissions={setPermissionsRole}
          onDelete={setDeleteTarget}
        />
      )}

      <RoleFormDialog open={formOpen} onOpenChange={setFormOpen} role={editingRole} onSaved={reload} />
      <RolePermissionsDialog
        open={!!permissionsRole}
        onOpenChange={() => setPermissionsRole(null)}
        role={permissionsRole}
      />
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete this role?"
        description={`"${deleteTarget?.name}" will be removed from every user it's currently assigned to. This cannot be undone.`}
        confirmLabel="Delete"
        destructive
        isLoading={isDeleting}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
