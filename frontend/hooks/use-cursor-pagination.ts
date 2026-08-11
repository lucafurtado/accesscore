"use client";

import { useCallback, useState } from "react";

/**
 * The backend only ever returns a forward `next_cursor` (keyset pagination
 * has no concept of "page N"), so "Previous" is implemented here by keeping
 * a client-side stack of cursors already visited. Each page is still a real
 * request driven by a real backend cursor - this only remembers where
 * you've been, it never fetches more than one page at a time.
 */
export function useCursorPagination() {
  const [cursor, setCursor] = useState<string | null>(null);
  const [history, setHistory] = useState<(string | null)[]>([]);

  const goNext = useCallback(
    (nextCursor: string) => {
      setHistory((prev) => [...prev, cursor]);
      setCursor(nextCursor);
    },
    [cursor],
  );

  const goPrevious = useCallback(() => {
    setHistory((prev) => {
      if (prev.length === 0) return prev;
      setCursor(prev[prev.length - 1]);
      return prev.slice(0, -1);
    });
  }, []);

  const reset = useCallback(() => {
    setCursor(null);
    setHistory([]);
  }, []);

  return { cursor, goNext, goPrevious, reset, canGoPrevious: history.length > 0 };
}
