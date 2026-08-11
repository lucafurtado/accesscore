"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime } from "@/lib/format";
import type { AuditLogResponse } from "@/types/api";

interface AuditLogTableProps {
  entries: AuditLogResponse[];
  isLoading: boolean;
  onViewDetails: (entry: AuditLogResponse) => void;
}

export function AuditLogTable({ entries, isLoading, onViewDetails }: AuditLogTableProps) {
  return (
    <div className="overflow-x-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Timestamp</TableHead>
            <TableHead>Action</TableHead>
            <TableHead className="hidden md:table-cell">Resource</TableHead>
            <TableHead className="hidden lg:table-cell">Actor</TableHead>
            <TableHead className="hidden lg:table-cell">IP address</TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading
            ? Array.from({ length: 8 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={6}>
                    <Skeleton className="h-8 w-full" />
                  </TableCell>
                </TableRow>
              ))
            : entries.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="text-muted-foreground text-xs whitespace-nowrap">
                    {formatDateTime(entry.created_at)}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="font-mono text-xs">
                      {entry.action}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground hidden md:table-cell">
                    {entry.resource_type ? (
                      <span className="font-mono text-xs">
                        {entry.resource_type}
                        {entry.resource_id ? `:${entry.resource_id.slice(0, 8)}…` : ""}
                      </span>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground hidden font-mono text-xs lg:table-cell">
                    {entry.actor_user_id ? `${entry.actor_user_id.slice(0, 8)}…` : "System"}
                  </TableCell>
                  <TableCell className="text-muted-foreground hidden lg:table-cell">
                    {entry.ip_address ?? "—"}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" onClick={() => onViewDetails(entry)}>
                      Details
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
        </TableBody>
      </Table>
    </div>
  );
}
