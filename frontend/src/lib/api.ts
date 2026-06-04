const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
  localStorage.removeItem("kt_name");
  localStorage.removeItem("kt_email");
  localStorage.removeItem("kt_role");
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

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> ?? {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: "include" });
  if (res.status === 401 && typeof window !== "undefined" && !path.includes("/auth/")) {
    localStorage.removeItem("kt_name");
    localStorage.removeItem("kt_email");
    localStorage.removeItem("kt_role");
    if (onUnauthorized) {
      onUnauthorized();
    } else {
      window.location.href = "/login";
    }
  }
  return res;
}

export async function apiFetchJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
