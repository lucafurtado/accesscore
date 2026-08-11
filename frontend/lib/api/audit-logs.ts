import { apiClient } from "@/lib/api/client";
import { buildQuery } from "@/lib/api/query";
import type { AuditLogResponse, CursorPage } from "@/types/api";

export interface ListAuditLogsParams {
  cursor?: string | null;
  limit?: number;
  actor_user_id?: string;
  action?: string;
  resource_type?: string;
  resource_id?: string;
  created_after?: string;
  created_before?: string;
  [key: string]: string | number | boolean | undefined | null;
}

export const auditLogsApi = {
  list: (params: ListAuditLogsParams = {}) =>
    apiClient.get<CursorPage<AuditLogResponse>>(`/audit-logs${buildQuery(params)}`),
};
