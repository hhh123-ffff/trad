"use client";

import { useCallback, useEffect, useState } from "react";

/** Async query state used by polling data hook. */
export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refresh: () => Promise<void>;
}

/** Optional configuration for polling query hook. */
interface PollingOptions {
  intervalMs?: number;
  immediate?: boolean;
}

/**
 * Run an async request function and optionally poll it.
 * The hook centralizes loading/error handling for dashboard pages.
 */
export function usePollingQuery<T>(
  request: () => Promise<T>,
  deps: unknown[] = [],
  options: PollingOptions = {},
): AsyncState<T> {
  const { intervalMs = 0, immediate = true } = options;
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(immediate);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await request();
      setData(response);
      setLastUpdated(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unexpected request error.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    if (!immediate) {
      return;
    }
    void refresh();
  }, [refresh, immediate, ...deps]);

  useEffect(() => {
    if (!intervalMs || intervalMs <= 0) {
      return;
    }
    const timer = window.setInterval(() => {
      void refresh();
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [refresh, intervalMs]);

  return {
    data,
    loading,
    error,
    lastUpdated,
    refresh,
  };
}
