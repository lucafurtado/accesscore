import type { UserResponse } from "@/types/api";

// Plain module-level store (React's useSyncExternalStore pattern) rather
// than a state-management library: the state shape here is small and
// doesn't need one. The access token lives ONLY here, in memory - never in
// localStorage/sessionStorage - so it disappears on tab close/reload. The
// refresh token never reaches this module at all; it lives in an httpOnly
// cookie only the Next.js route handlers under app/api/auth/* can read.
export type SessionStatus = "loading" | "authenticated" | "unauthenticated";

export interface SessionState {
  status: SessionStatus;
  accessToken: string | null;
  user: UserResponse | null;
  permissions: string[];
}

let state: SessionState = {
  status: "loading",
  accessToken: null,
  user: null,
  permissions: [],
};

const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

export function getSessionState(): SessionState {
  return state;
}

export function subscribeSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function setSession(partial: Partial<SessionState>): void {
  state = { ...state, ...partial };
  emit();
}

export function clearSession(): void {
  state = { status: "unauthenticated", accessToken: null, user: null, permissions: [] };
  emit();
}
