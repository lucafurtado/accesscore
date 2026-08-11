"use client";

import { useState } from "react";
import { ShieldAlert } from "lucide-react";

import { AuditLogDetailDialog } from "@/components/audit-logs/audit-log-detail-dialog";
import {
  AuditLogFilters,
  type AuditLogFilterValues,
} from "@/components/audit-logs/audit-log-filters";
import { AuditLogTable } from "@/components/audit-logs/audit-log-table";
import { CursorPagination } from "@/components/common/cursor-pagination";
import { PageHeader } from "@/components/common/page-header";
import { ErrorState, EmptyState } from "@/components/common/state-message";
import { useAsyncData } from "@/hooks/use-async-data";
import { useCursorPagination } from "@/hooks/use-cursor-pagination";
import { useHasPermission } from "@/hooks/use-permissions";
import { auditLogsApi } from "@/lib/api/audit-logs";
import type { AuditLogResponse } from "@/types/api";

const EMPTY_FILTERS: AuditLogFilterValues = { action: "", resourceType: "", actorUserId: "" };

export default function AuditLogsPage() {
  // Only users with audit_logs:read should ever see audit data - this is a
  // direct-navigation guard (the sidebar already hides the link), the
  // backend enforces this independently regardless of what renders here.
  const canRead = useHasPermission("audit_logs:read");

  const [filters, setFilters] = useState<AuditLogFilterValues>(EMPTY_FILTERS);
  const [detailEntry, setDetailEntry] = useState<AuditLogResponse | null>(null);
  const pagination = useCursorPagination();

  const { data, isLoading, error, reload } = useAsyncData(
    () =>
      canRead
        ? auditLogsApi.list({
            cursor: pagination.cursor,
            limit: 20,
            action: filters.action || undefined,
            resource_type: filters.resourceType || undefined,
            actor_user_id: filters.actorUserId || undefined,
          })
        : Promise.resolve({ items: [], next_cursor: null, has_more: false }),
    [canRead, pagination.cursor, filters.action, filters.resourceType, filters.actorUserId],
  );

  function handleFiltersChange(next: AuditLogFilterValues) {
    setFilters(next);
    pagination.reset();
  }

  if (!canRead) {
    return (
      <div>
        <PageHeader title="Audit Logs" />
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed py-16 text-center">
          <ShieldAlert className="text-muted-foreground mb-2 h-8 w-8" />
          <p className="text-sm font-medium">You don&apos;t have access to audit logs</p>
          <p className="text-muted-foreground max-w-sm text-sm">
            This page requires the <code className="font-mono">audit_logs:read</code> permission.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Audit Logs" description="A record of every security-sensitive action." />
      <AuditLogFilters values={filters} onChange={handleFiltersChange} />

      {error ? (
        <ErrorState title="Couldn't load audit logs" onRetry={reload} />
      ) : !isLoading && data?.items.length === 0 ? (
        <EmptyState title="No audit events found" description="Try adjusting or clearing your filters." />
      ) : (
        <>
          <AuditLogTable
            entries={data?.items ?? []}
            isLoading={isLoading}
            onViewDetails={setDetailEntry}
          />
          <CursorPagination
            onPrevious={pagination.goPrevious}
            onNext={() => data?.next_cursor && pagination.goNext(data.next_cursor)}
            canGoPrevious={pagination.canGoPrevious}
            canGoNext={!!data?.has_more}
          />
        </>
      )}

      <AuditLogDetailDialog entry={detailEntry} onOpenChange={() => setDetailEntry(null)} />
    </div>
  );
}
