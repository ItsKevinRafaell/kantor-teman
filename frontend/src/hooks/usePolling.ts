import { useEffect, useRef, useCallback } from "react";

interface UsePollingOptions {
  interval: number;
  enabled?: boolean;
}

/**
 * Generic polling hook for refreshing data at regular intervals
 * Replaces setInterval manual polling in components
 */
export function usePolling(
  callback: () => void | Promise<void>,
  options: UsePollingOptions
) {
  const { interval, enabled = true } = options;
  const savedCallback = useRef(callback);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Update ref if callback changes
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const start = useCallback(() => {
    stop();
    intervalRef.current = setInterval(() => {
      savedCallback.current();
    }, interval);
  }, [interval, stop]);

  useEffect(() => {
    if (enabled) {
      start();
    } else {
      stop();
    }

    return () => {
      stop();
    };
  }, [enabled, interval, start, stop]);

  return { stop, start };
}