const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)kt_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export function setToken(token: string, name: string, email: string) {
  const expires = new Date(Date.now() + 24 * 60 * 60 * 1000).toUTCString();
  document.cookie = `kt_token=${encodeURIComponent(token)}; expires=${expires}; path=/; SameSite=Lax`;
  localStorage.setItem("kt_name", name);
  localStorage.setItem("kt_email", email);
}

export function clearToken() {
  document.cookie = "kt_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
  localStorage.removeItem("kt_name");
  localStorage.removeItem("kt_email");
}

export function getUserInfo() {
  return {
    name: localStorage.getItem("kt_name") ?? "Admin",
    email: localStorage.getItem("kt_email") ?? "",
  };
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
