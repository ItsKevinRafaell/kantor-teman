import useSWR, { mutate, SWRConfiguration } from "swr";
import { apiFetch } from "./api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type { SWRConfiguration };

/**
 * SWR-based data fetching hook with automatic JSON parsing
 */
export function useApi<T>(path: string | null, config?: Partial<SWRConfiguration<T>>) {
  const url = path ? `${API_BASE}${path}` : null;

  return useSWR<T>(url, (url) => apiFetchJson<T>(url), {
    revalidateOnFocus: false,
    revalidateOnReconnect: true,
    dedupingInterval: 30000,
    ...config,
  });
}

/**
 * Fetch JSON with error handling
 */
export async function apiFetchJson<T>(url: string): Promise<T> {
  const res = await apiFetch(url.replace(API_BASE, ""));
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Trigger SWR revalidation for a specific path
 * Use for optimistic updates or after mutations
 */
export function apiMutate(path: string) {
  mutate(`${API_BASE}${path}`);
}

/**
 * Revalidate multiple paths at once
 */
export function apiMutateAll(paths: string[]) {
  paths.forEach((path) => apiMutate(path));
}

/**
 * Helper to build query string from params object
 */
export function buildQueryString(params: Record<string, string | number | boolean | undefined | null>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value));
    }
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}