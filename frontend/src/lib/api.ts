// When running in the browser, derive API_BASE from the hostname instead
// of trusting `NEXT_PUBLIC_API_URL`. The Vercel project env has
// NEXT_PUBLIC_API_URL=https://api.kantorteman.my.id baked in at build
// time. If we trust that env value at runtime, every dashboard fetch
// goes cross-site and samesite=lax blocks the kt_token cookie → 401s.
//
// Resolution rules (browser side):
//   1. Any Vercel-served host (kantor-teman-five.vercel.app,
//      www.kantorteman.my.id / kantorteman.my.id via custom domain,
//      preview-* subdomains, etc) -> API_BASE = "" (same-origin).
//      Vercel's next.config.js rewrites() proxies /api/* to
//      api.kantorteman.my.id with the kt_token cookie attached (it's
//      not a CORS preflight — same-origin fetch keeps all cookies).
//   2. window.location.hostname is localhost / 127.0.0.1
//      -> API_BASE = "http://localhost:8000" (local FastAPI dev).
//   3. SSR / Node fallback: trust NEXT_PUBLIC_API_URL env (server has
//      to reach the backend over the public internet for OG image
//      rendering, etc).

function resolveApiBase(): string {
  if (typeof window === "undefined") {
    // SSR build-time / Node — trust Vercel's NEXT_PUBLIC_API_URL so the
    // server can fetch the backend over the public internet.
    return process.env.NEXT_PUBLIC_API_URL || "";
  }
  const host = window.location.hostname;
  // Vercel preview + production domains
  if (host.endsWith(".vercel.app") || host === "vercel.app") return "";
  // Local FastAPI dev
  if (/^(localhost|127\.0\.0\.1)(:\d+)?$/.test(host)) return "http://localhost:8000";
  // Custom domain on Vercel (the SPA is fronted by Cloudflare -> Vercel
  // and served from the same deployment bundle). Treat as same-origin.
  if (host.endsWith("kantorteman.my.id")) return "";
  // Fallback: trust env, else empty (same-origin)
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

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) { onUnauthorized = fn; }

export function setToken(_token: string, name: string, email: string, role: string = "admin") {
  localStorage.setItem("kt_name", name);
  localStorage.setItem("kt_email", email);
  localStorage.setItem("kt_role", role);
}

export async function clearToken() {
  const base = ensureApiBase();
  try {
    await fetch(`${base}/api/auth/logout`, { method: "POST", credentials: "include" });
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
let autoLogoutFiredOnce = false;  // prevent self-inflicted loop after the
                                   // server-side token_version bump

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
  // Idempotent guard: after the first auto-logout in a tab, do NOT
  // POST /api/auth/logout again — that increments server-side
  // token_version and turns every cached kt_token into a 401-triggering
  // token, trapping the user in an infinite redirect loop.
  if (reason === "401" && autoLogoutFiredOnce) {
    if (onUnauthorized) onUnauthorized();
    else window.location.href = "/login";
    return;
  }
  if (reason === "401") autoLogoutFiredOnce = true;
  const base = ensureApiBase();
  if (reason === "401" || reason === "manual") {
    fetch(`${base}/api/auth/logout`, { method: "POST", credentials: "include" })
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

/**
 * Reset the auto-logout latches so the next tab session starts clean.
 * Called after a successful /api/auth/login so a manual login doesn't
 * appear as already-firing-auto-logout.
 */
export function resetAutoLogoutLatch() {
  autoLogoutFiredOnce = false;
}

// Expose for manual logout buttons if they want a unified helper.
export async function logoutLocally() { fireAutoLogout("manual"); }

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const base = ensureApiBase();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> ?? {}),
  };
  let res: Response;
  try {
    res = await fetch(`${base}${path}`, { ...options, headers, credentials: "include" });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "network error";
    throw new Error(`Tidak bisa menghubungi API KantorTeman (${base}). Cek koneksi, CORS, atau status backend. Detail: ${detail}`);
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
