import { apiClient } from "@/lib/api/client";
import type { PermissionCreate, PermissionResponse } from "@/types/api";

export const permissionsApi = {
  list: () => apiClient.get<PermissionResponse[]>("/permissions"),
  create: (payload: PermissionCreate) => apiClient.post<PermissionResponse>("/permissions", payload),
};
