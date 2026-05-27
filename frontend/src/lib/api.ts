const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)kt_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export function setToken(token: string, name: string, email: string, role: string = "admin") {
  const expires = new Date(Date.now() + 24 * 60 * 60 * 1000).toUTCString();
  document.cookie = `kt_token=${encodeURIComponent(token)}; expires=${expires}; path=/; SameSite=Lax`;
  localStorage.setItem("kt_name", name);
  localStorage.setItem("kt_email", email);
  localStorage.setItem("kt_role", role);
}

export function clearToken() {
  document.cookie = "kt_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
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
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return fetch(`${API_BASE}${path}`, { ...options, headers });
}

export async function apiFetchJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}
