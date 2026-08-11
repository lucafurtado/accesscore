"use client";

import { useSyncExternalStore } from "react";

import { getSessionState, type SessionState, subscribeSession } from "@/lib/session-store";

export function useSession(): SessionState {
  return useSyncExternalStore(subscribeSession, getSessionState, getSessionState);
}
