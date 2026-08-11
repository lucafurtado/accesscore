// Typed models mirroring backend/app/schemas/*.py exactly. Keep in sync with
// the backend by hand — there is no shared schema generation in this
// project, so any backend schema change must be reflected here too.

export interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface UserCreate {
  email: string;
  password: string;
  full_name?: string | null;
}

export interface UserUpdate {
  full_name?: string | null;
  email?: string | null;
}

export interface UserStats {
  total: number;
  active: number;
}

export interface RoleResponse {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface RoleCreate {
  name: string;
  description?: string | null;
}

export interface RoleUpdate {
  name?: string | null;
  description?: string | null;
}

export interface PermissionResponse {
  id: string;
  resource: string;
  action: string;
  description: string | null;
  created_at: string;
}

export interface PermissionCreate {
  resource: string;
  action: string;
  description?: string | null;
}

export interface AuditLogResponse {
  id: string;
  actor_user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  context: Record<string, unknown> | null;
  created_at: string;
}

export interface CursorPage<T> {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/** FastAPI's default validation error shape (422 responses). */
export interface ValidationErrorDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}
