"use client";

import { useState } from "react";
import { Plus } from "lucide-react";

import { PageHeader } from "@/components/common/page-header";
import { ErrorState } from "@/components/common/state-message";
import { PermissionGate } from "@/components/permission-gate";
import { PermissionFormDialog } from "@/components/permissions/permission-form-dialog";
import { PermissionTable } from "@/components/permissions/permission-table";
import { Button } from "@/components/ui/button";
import { useAsyncData } from "@/hooks/use-async-data";
import { permissionsApi } from "@/lib/api/permissions";

export default function PermissionsPage() {
  const { data: permissions, isLoading, error, reload } = useAsyncData(
    () => permissionsApi.list(),
    [],
  );
  const [formOpen, setFormOpen] = useState(false);

  return (
    <div>
      <PageHeader
        title="Permissions"
        description="The full set of resource:action permissions roles can be granted."
        actions={
          <PermissionGate permission="permissions:manage">
            <Button onClick={() => setFormOpen(true)}>
              <Plus className="mr-1.5 h-4 w-4" />
              Create permission
            </Button>
          </PermissionGate>
        }
      />

      {error ? (
        <ErrorState title="Couldn't load permissions" onRetry={reload} />
      ) : (
        <PermissionTable permissions={permissions ?? []} isLoading={isLoading} />
      )}

      <PermissionFormDialog open={formOpen} onOpenChange={setFormOpen} onSaved={reload} />
    </div>
  );
}
