import { apiClient } from "@/lib/api/client";
import { buildQuery } from "@/lib/api/query";
import type { CursorPage, RoleResponse, UserCreate, UserResponse, UserStats, UserUpdate } from "@/types/api";

export interface ListUsersParams {
  cursor?: string | null;
  limit?: number;
  is_active?: boolean;
  q?: string;
  [key: string]: string | number | boolean | undefined | null;
}

export const usersApi = {
  list: (params: ListUsersParams = {}) =>
    apiClient.get<CursorPage<UserResponse>>(`/users${buildQuery(params)}`),
  stats: () => apiClient.get<UserStats>("/users/stats"),
  me: () => apiClient.get<UserResponse>("/users/me"),
  myPermissions: () => apiClient.get<string[]>("/users/me/permissions"),
  get: (id: string) => apiClient.get<UserResponse>(`/users/${id}`),
  permissions: (id: string) => apiClient.get<string[]>(`/users/${id}/permissions`),
  create: (payload: UserCreate) => apiClient.post<UserResponse>("/users", payload),
  update: (id: string, payload: UserUpdate) => apiClient.put<UserResponse>(`/users/${id}`, payload),
  disable: (id: string) => apiClient.post<void>(`/users/${id}/disable`),
  reactivate: (id: string) => apiClient.post<void>(`/users/${id}/reactivate`),
  roles: (id: string) => apiClient.get<RoleResponse[]>(`/users/${id}/roles`),
  assignRole: (id: string, roleId: string) =>
    apiClient.post<void>(`/users/${id}/roles`, { role_id: roleId }),
  removeRole: (id: string, roleId: string) =>
    apiClient.delete<void>(`/users/${id}/roles/${roleId}`),
};
