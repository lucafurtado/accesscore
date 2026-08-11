import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { PermissionResponse } from "@/types/api";

interface PermissionTableProps {
  permissions: PermissionResponse[];
  isLoading: boolean;
}

export function PermissionTable({ permissions, isLoading }: PermissionTableProps) {
  return (
    <div className="overflow-x-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Permission</TableHead>
            <TableHead className="hidden sm:table-cell">Description</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading
            ? Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={2}>
                    <Skeleton className="h-8 w-full" />
                  </TableCell>
                </TableRow>
              ))
            : permissions.map((permission) => (
                <TableRow key={permission.id}>
                  <TableCell className="font-mono text-sm font-medium">
                    {permission.resource}:{permission.action}
                  </TableCell>
                  <TableCell className="text-muted-foreground hidden sm:table-cell">
                    {permission.description || "—"}
                  </TableCell>
                </TableRow>
              ))}
        </TableBody>
      </Table>
    </div>
  );
}
