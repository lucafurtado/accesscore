"use client";

import { KeyRound, MoreHorizontal, Pencil, Trash2 } from "lucide-react";

import { PermissionGate } from "@/components/permission-gate";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { RoleResponse } from "@/types/api";

interface RoleTableProps {
  roles: RoleResponse[];
  isLoading: boolean;
  onEdit: (role: RoleResponse) => void;
  onManagePermissions: (role: RoleResponse) => void;
  onDelete: (role: RoleResponse) => void;
}

export function RoleTable({ roles, isLoading, onEdit, onManagePermissions, onDelete }: RoleTableProps) {
  return (
    <div className="overflow-x-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead className="hidden sm:table-cell">Description</TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={3}>
                    <Skeleton className="h-8 w-full" />
                  </TableCell>
                </TableRow>
              ))
            : roles.map((role) => (
                <TableRow key={role.id}>
                  <TableCell className="font-medium">{role.name}</TableCell>
                  <TableCell className="text-muted-foreground hidden sm:table-cell">
                    {role.description || "—"}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger
                        render={
                          <Button variant="ghost" size="icon" aria-label={`Actions for ${role.name}`}>
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        }
                      />
                      <DropdownMenuContent align="end">
                        <PermissionGate permission="roles:manage">
                          <DropdownMenuItem onClick={() => onEdit(role)}>
                            <Pencil className="mr-2 h-4 w-4" />
                            Edit
                          </DropdownMenuItem>
                        </PermissionGate>
                        <PermissionGate permission="roles:manage">
                          <DropdownMenuItem onClick={() => onManagePermissions(role)}>
                            <KeyRound className="mr-2 h-4 w-4" />
                            Manage permissions
                          </DropdownMenuItem>
                        </PermissionGate>
                        <PermissionGate permission="roles:manage">
                          <DropdownMenuItem variant="destructive" onClick={() => onDelete(role)}>
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </DropdownMenuItem>
                        </PermissionGate>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
        </TableBody>
      </Table>
    </div>
  );
}
