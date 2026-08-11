import { apiClient } from "@/lib/api/client";
import type { PermissionResponse, RoleCreate, RoleResponse, RoleUpdate } from "@/types/api";

export const rolesApi = {
  list: () => apiClient.get<RoleResponse[]>("/roles"),
  get: (id: string) => apiClient.get<RoleResponse>(`/roles/${id}`),
  create: (payload: RoleCreate) => apiClient.post<RoleResponse>("/roles", payload),
  update: (id: string, payload: RoleUpdate) => apiClient.put<RoleResponse>(`/roles/${id}`, payload),
  delete: (id: string) => apiClient.delete<void>(`/roles/${id}`),
  permissions: (roleId: string) =>
    apiClient.get<PermissionResponse[]>(`/roles/${roleId}/permissions`),
  assignPermission: (roleId: string, permissionId: string) =>
    apiClient.post<void>(`/roles/${roleId}/permissions`, { permission_id: permissionId }),
  removePermission: (roleId: string, permissionId: string) =>
    apiClient.delete<void>(`/roles/${roleId}/permissions/${permissionId}`),
};
