"use client";

import { MoreHorizontal, ShieldCheck, UserCog, UserMinus, UserCheck } from "lucide-react";

import { PermissionGate } from "@/components/permission-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useSession } from "@/hooks/use-session";
import { formatDateTimeOrNever } from "@/lib/format";
import type { UserResponse } from "@/types/api";

interface UserTableProps {
  users: UserResponse[];
  isLoading: boolean;
  onEdit: (user: UserResponse) => void;
  onManageRoles: (user: UserResponse) => void;
  onToggleActive: (user: UserResponse) => void;
}

export function UserTable({ users, isLoading, onEdit, onManageRoles, onToggleActive }: UserTableProps) {
  const { user: currentUser } = useSession();

  return (
    <div className="overflow-x-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>User</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="hidden md:table-cell">Created</TableHead>
            <TableHead className="hidden md:table-cell">Last login</TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading
            ? Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}>
                    <Skeleton className="h-8 w-full" />
                  </TableCell>
                </TableRow>
              ))
            : users.map((user) => {
                const isSelf = user.id === currentUser?.id;
                return (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="font-medium">{user.full_name || "—"}</div>
                      <div className="text-muted-foreground text-xs">{user.email}</div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={user.is_active ? "default" : "secondary"}>
                        {user.is_active ? "Active" : "Disabled"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground hidden md:table-cell">
                      {formatDateTimeOrNever(user.created_at)}
                    </TableCell>
                    <TableCell className="text-muted-foreground hidden md:table-cell">
                      {formatDateTimeOrNever(user.last_login_at)}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          render={
                            <Button variant="ghost" size="icon" aria-label={`Actions for ${user.email}`}>
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          }
                        />
                        <DropdownMenuContent align="end">
                          <PermissionGate permission="users:update">
                            <DropdownMenuItem onClick={() => onEdit(user)}>
                              <UserCog className="mr-2 h-4 w-4" />
                              Edit
                            </DropdownMenuItem>
                          </PermissionGate>
                          <PermissionGate permission="roles:manage">
                            <DropdownMenuItem onClick={() => onManageRoles(user)}>
                              <ShieldCheck className="mr-2 h-4 w-4" />
                              Manage roles
                            </DropdownMenuItem>
                          </PermissionGate>
                          <PermissionGate permission="users:disable">
                            <DropdownMenuItem
                              disabled={isSelf}
                              onClick={() => onToggleActive(user)}
                              variant={user.is_active ? "destructive" : "default"}
                            >
                              {user.is_active ? (
                                <>
                                  <UserMinus className="mr-2 h-4 w-4" />
                                  Disable
                                </>
                              ) : (
                                <>
                                  <UserCheck className="mr-2 h-4 w-4" />
                                  Reactivate
                                </>
                              )}
                            </DropdownMenuItem>
                          </PermissionGate>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })}
        </TableBody>
      </Table>
    </div>
  );
}
