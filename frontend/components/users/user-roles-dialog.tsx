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
import { rolesApi } from "@/lib/api/roles";
import { usersApi } from "@/lib/api/users";
import type { RoleResponse, UserResponse } from "@/types/api";

interface UserRolesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: UserResponse | null;
}

// Remounted (via key, see below) each time the dialog opens for a given
// user, so it starts a fresh fetch instead of resetting state via an
// effect. isLoading starts true and is only ever flipped to false inside
// the async .then/.catch - never set synchronously in the effect body.
function UserRolesDialogBody({ user }: { user: UserResponse }) {
  const [allRoles, setAllRoles] = useState<RoleResponse[] | null>(null);
  const [assignedIds, setAssignedIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [pendingRoleId, setPendingRoleId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([rolesApi.list(), usersApi.roles(user.id)])
      .then(([roles, userRoles]) => {
        if (cancelled) return;
        setAllRoles(roles);
        setAssignedIds(new Set(userRoles.map((r) => r.id)));
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Failed to load roles.");
        setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user.id]);

  async function toggleRole(role: RoleResponse, assign: boolean) {
    setPendingRoleId(role.id);
    try {
      if (assign) {
        await usersApi.assignRole(user.id, role.id);
        setAssignedIds((prev) => new Set(prev).add(role.id));
        toast.success(`Assigned "${role.name}"`);
      } else {
        await usersApi.removeRole(user.id, role.id);
        setAssignedIds((prev) => {
          const next = new Set(prev);
          next.delete(role.id);
          return next;
        });
        toast.success(`Removed "${role.name}"`);
      }
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to update role assignment.");
    } finally {
      setPendingRoleId(null);
    }
  }

  return (
    <div className="max-h-80 space-y-1 overflow-y-auto py-2">
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      ) : error ? (
        <p className="text-destructive text-sm">{error}</p>
      ) : allRoles && allRoles.length > 0 ? (
        allRoles.map((role) => {
          const checked = assignedIds.has(role.id);
          return (
            <label
              key={role.id}
              className="hover:bg-muted/50 flex items-center gap-3 rounded-md px-2 py-2 text-sm"
            >
              <Checkbox
                checked={checked}
                disabled={pendingRoleId === role.id}
                onCheckedChange={(value) => toggleRole(role, value)}
              />
              <div>
                <p className="font-medium">{role.name}</p>
                {role.description ? (
                  <p className="text-muted-foreground text-xs">{role.description}</p>
                ) : null}
              </div>
            </label>
          );
        })
      ) : (
        <p className="text-muted-foreground text-sm">No roles exist yet.</p>
      )}
    </div>
  );
}

export function UserRolesDialog({ open, onOpenChange, user }: UserRolesDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Manage roles</DialogTitle>
          <DialogDescription>
            {user ? `Assign or remove roles for ${user.email}.` : ""}
          </DialogDescription>
        </DialogHeader>

        {user ? <UserRolesDialogBody key={user.id} user={user} /> : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
