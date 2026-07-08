import useSWR, { mutate, SWRConfiguration } from "swr";
import { apiFetch } from "./api";

// Runtime hostname-based resolver: never trust the Vercel project env
// NEXT_PUBLIC_API_URL=https://api.kantorteman.my.id (it stays baked in
// at build time and would push every dashboard fetch cross-site).
// Both Vercel-served custom domains (e.g. www.kantorteman.my.id) and
// preview/prod subdomains are routed same-origin (API_BASE = "") so the
// Next rewrites() proxy at /api/* can carry the kt_token cookie.
function resolveApiBase(): string {
  if (typeof window === "undefined") {
    return process.env.NEXT_PUBLIC_API_URL || "";
  }
  const host = window.location.hostname;
  if (host.endsWith(".vercel.app") || host === "vercel.app") return "";
  if (/^(localhost|127\.0\.0\.1)(:\d+)?$/.test(host)) return "http://localhost:8000";
  if (host.endsWith("kantorteman.my.id")) return "";
  return process.env.NEXT_PUBLIC_API_URL || "";
}
let API_BASE = "";
let apiBaseInitialized = false;
function ensureApiBase(): string {
  if (!apiBaseInitialized) {
    API_BASE = resolveApiBase();
    apiBaseInitialized = true;
  }
  return API_BASE;
}

export type { SWRConfiguration };

/**
 * SWR-based data fetching hook with automatic JSON parsing
 */
export function useApi<T>(path: string | null, config?: Partial<SWRConfiguration<T>>) {
  const url = path ? `${ensureApiBase()}${path}` : null;

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
  const res = await apiFetch(url.replace(ensureApiBase(), ""));
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
  mutate(`${ensureApiBase()}${path}`);
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