"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { permissionsApi } from "@/lib/api/permissions";
import { rolesApi } from "@/lib/api/roles";
import type { PermissionResponse, RoleResponse } from "@/types/api";

interface RolePermissionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role: RoleResponse | null;
}

// Remounted (via key) each time the dialog opens for a given role. isLoading
// starts true and is only ever flipped to false inside the async
// .then/.catch - never set synchronously in the effect body.
function RolePermissionsDialogBody({ role }: { role: RoleResponse }) {
  const [allPermissions, setAllPermissions] = useState<PermissionResponse[] | null>(null);
  const [assignedIds, setAssignedIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([permissionsApi.list(), rolesApi.permissions(role.id)])
      .then(([permissions, assigned]) => {
        if (cancelled) return;
        setAllPermissions(permissions);
        setAssignedIds(new Set(assigned.map((p) => p.id)));
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Failed to load permissions.");
        setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [role.id]);

  async function togglePermission(permission: PermissionResponse, assign: boolean) {
    setPendingId(permission.id);
    const key = `${permission.resource}:${permission.action}`;
    try {
      if (assign) {
        await rolesApi.assignPermission(role.id, permission.id);
        setAssignedIds((prev) => new Set(prev).add(permission.id));
        toast.success(`Assigned ${key}`);
      } else {
        await rolesApi.removePermission(role.id, permission.id);
        setAssignedIds((prev) => {
          const next = new Set(prev);
          next.delete(permission.id);
          return next;
        });
        toast.success(`Removed ${key}`);
      }
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to update permission assignment.");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <div className="max-h-80 space-y-1 overflow-y-auto py-2">
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      ) : error ? (
        <p className="text-destructive text-sm">{error}</p>
      ) : allPermissions && allPermissions.length > 0 ? (
        allPermissions.map((permission) => {
          const checked = assignedIds.has(permission.id);
          return (
            <label
              key={permission.id}
              className="hover:bg-muted/50 flex items-center gap-3 rounded-md px-2 py-2 text-sm"
            >
              <Checkbox
                checked={checked}
                disabled={pendingId === permission.id}
                onCheckedChange={(value) => togglePermission(permission, value)}
              />
              <div>
                <p className="font-mono text-xs font-medium">
                  {permission.resource}:{permission.action}
                </p>
                {permission.description ? (
                  <p className="text-muted-foreground text-xs">{permission.description}</p>
                ) : null}
              </div>
            </label>
          );
        })
      ) : (
        <p className="text-muted-foreground text-sm">No permissions exist yet.</p>
      )}
    </div>
  );
}

export function RolePermissionsDialog({ open, onOpenChange, role }: RolePermissionsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Manage permissions</DialogTitle>
          <DialogDescription>
            {role ? `Assign or remove permissions for "${role.name}".` : ""}
          </DialogDescription>
        </DialogHeader>

        {role ? <RolePermissionsDialogBody key={role.id} role={role} /> : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
