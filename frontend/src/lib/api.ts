// When NEXT_PUBLIC_API_URL is empty (production on Vercel), requests go
// same-origin (`/api/...`) and the kt_token cookie travels. In local dev
// we default to http://localhost:8000 where the fastapi backend runs.
const RAW_API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";
const IS_BROWSER_LOCAL =
  typeof window !== "undefined" &&
  /^(localhost|127\.0\.0\.1)(:\d+)?$/.test(window.location.host);
const API_BASE = RAW_API_BASE || (IS_BROWSER_LOCAL ? "http://localhost:8000" : "");

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) { onUnauthorized = fn; }

export function setToken(_token: string, name: string, email: string, role: string = "admin") {
  localStorage.setItem("kt_name", name);
  localStorage.setItem("kt_email", email);
  localStorage.setItem("kt_role", role);
}

export async function clearToken() {
  try {
    await fetch(`${API_BASE}/api/auth/logout`, { method: "POST", credentials: "include" });
  } catch { /* ignore */ }
  clearLocalAuthCache();
}

/** Drop only the in-browser auth markers — does NOT hit the backend.
 * Used by the 401 auto-logout path so the chain works even when the
 * backend is unreachable.
 */
export function clearLocalAuthCache() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("kt_name");
  localStorage.removeItem("kt_email");
  localStorage.removeItem("kt_role");
  localStorage.setItem("kt_unauth_at", String(Date.now()));
}

export function getUserInfo() {
  return {
    name: localStorage.getItem("kt_name") ?? "Admin",
    email: localStorage.getItem("kt_email") ?? "",
    role: localStorage.getItem("kt_role") ?? "admin",
  };
}

export function getUserRole(): "admin" | "member" {
  if (typeof window === "undefined") return "admin";
  const r = localStorage.getItem("kt_role");
  return r === "member" ? "member" : "admin";
}

/** Read+consume the kt_unauth_at timestamp set by the 401 auto-logout
 * flow. Returns the timestamp (ms) if set within the last 30s, else 0.
 * The login page reads this to show a "Sesi Anda habis" toast.
 */
export function consumeUnauthToast(): number {
  if (typeof window === "undefined") return 0;
  const raw = localStorage.getItem("kt_unauth_at");
  if (!raw) return 0;
  const ts = Number(raw);
  localStorage.removeItem("kt_unauth_at");
  // Only show once within 30s of being set.
  if (!Number.isFinite(ts) || Date.now() - ts > 30_000) return 0;
  return ts;
}

/**
 * Force any SWR cache from lib/swr.ts to drop. SWR exposes a global
 * mutate() that accepts no key to invalidate every cache entry. Imported
 * lazily because this module is loaded on every page (including /login)
 * and SWR isn't needed there.
 */
async function flushSwrCache() {
  if (typeof window === "undefined") return;
  try {
    const { mutate } = await import("swr");
    mutate(() => true, undefined, { revalidate: false });
  } catch { /* ignore — SWR not loaded yet */ }
}

let autoLogoutInFlight = false;

/**
 * Drain localStorage + SWR cache + (best-effort) call /api/auth/logout
 * to invalidate the server-side token_version, then trigger the
 * registered redirect handler.
 */
function fireAutoLogout(reason: "401" | "manual" = "401") {
  if (typeof window === "undefined") return;
  // Re-entrancy guard — many parallel 401s should not spam logout POSTs.
  if (autoLogoutInFlight && reason === "401") return;
  autoLogoutInFlight = true;
  clearLocalAuthCache();
  void flushSwrCache();
  // Best-effort server-side logout to invalidate the token_version.
  if (reason === "401" || reason === "manual") {
    fetch(`${API_BASE}/api/auth/logout`, { method: "POST", credentials: "include" })
      .catch(() => { /* offline? still log out locally */ })
      .finally(() => {
        if (onUnauthorized) onUnauthorized();
        else window.location.href = "/login";
      });
  } else {
    if (onUnauthorized) onUnauthorized();
    else window.location.href = "/login";
  }
}

// Expose for manual logout buttons if they want a unified helper.
export async function logoutLocally() { fireAutoLogout("manual"); }

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> ?? {}),
  };
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: "include" });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "network error";
    throw new Error(`Tidak bisa menghubungi API KantorTeman (${API_BASE}). Cek koneksi, CORS, atau status backend. Detail: ${detail}`);
  }
  if (res.status === 401 && typeof window !== "undefined" && !path.includes("/auth/")) {
    fireAutoLogout("401");
  }
  return res;
}

export async function apiFetchJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, options);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let detail = text;
    try {
      const err = JSON.parse(text);
      detail = err.detail || err.message || err.error || text;
    } catch { /* keep text */ }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}
