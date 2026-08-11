"use client";

import { useEffect, useState, type DependencyList } from "react";

interface AsyncState<T> {
  data: T | null;
  error: unknown;
  isLoading: boolean;
}

interface Result<T> {
  key: string | null;
  data: T | null;
  error: unknown;
}

export function useAsyncData<T>(
  fetcher: () => Promise<T>,
  deps: DependencyList,
): AsyncState<T> & { reload: () => void } {
  const [reloadKey, setReloadKey] = useState(0);
  // Identifies "what we're currently asking for". Comparing this against the
  // key of the last resolved result (computed at render time, not via an
  // extra setState call at the top of the effect) is what derives isLoading,
  // so the effect only ever calls setState from inside the async callback -
  // never synchronously in the effect body itself.
  const requestKey = JSON.stringify([...deps, reloadKey]);

  const [result, setResult] = useState<Result<T>>({ key: null, data: null, error: null });

  useEffect(() => {
    let cancelled = false;

    fetcher()
      .then((data) => {
        if (!cancelled) setResult({ key: requestKey, data, error: null });
      })
      .catch((error: unknown) => {
        if (!cancelled) setResult({ key: requestKey, data: null, error });
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestKey]);

  const isLoading = result.key !== requestKey;

  return {
    data: result.data,
    error: isLoading ? null : result.error,
    isLoading,
    reload: () => setReloadKey((k) => k + 1),
  };
}
