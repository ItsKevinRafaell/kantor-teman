"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { useRouter } from "next/navigation";

type UserRole = "admin" | "member";

interface User {
  name: string;
  email: string;
  role: UserRole;
}

interface AuthContextType {
  user: User | null;
  role: UserRole;
  isAdmin: boolean;
  isLoading: boolean;
  login: (name: string, email: string, role?: UserRole) => void;
  logout: () => void;
  refreshUser: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Runtime API base — same logic as lib/api.ts but kept separate to avoid
// pulling in the full auth module (this context loads on every page).
const API_BASE = (() => {
  if (typeof window === "undefined") return process.env.NEXT_PUBLIC_API_URL || "";
  const host = window.location.hostname;
  if (host.endsWith(".vercel.app") || host === "vercel.app") return "";
  if (/^(localhost|127\.0\.0\.1)(:\d+)?$/.test(host)) return "http://localhost:8000";
  if (host.endsWith("kantorteman.my.id")) return "";
  return process.env.NEXT_PUBLIC_API_URL || "";
})();

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const loadUser = useCallback(() => {
    if (typeof window === "undefined") return;
    const name = localStorage.getItem("kt_name");
    const email = localStorage.getItem("kt_email");
    const role = (localStorage.getItem("kt_role") as UserRole) || "admin";

    if (name) {
      setUser({ name, email: email || "", role });
    } else {
      setUser(null);
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  // Listen for storage changes (e.g., from other tabs)
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key === "kt_name" || e.key === "kt_email" || e.key === "kt_role") {
        loadUser();
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, [loadUser]);

  const login = useCallback((name: string, email: string, role: UserRole = "admin") => {
    localStorage.setItem("kt_name", name);
    localStorage.setItem("kt_email", email);
    localStorage.setItem("kt_role", role);
    setUser({ name, email, role });
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/api/auth/logout/`, { method: "POST", credentials: "include" });
    } catch { /* ignore */ }
    localStorage.removeItem("kt_name");
    localStorage.removeItem("kt_email");
    localStorage.removeItem("kt_role");
    setUser(null);
    router.push("/login");
  }, [router]);

  const refreshUser = useCallback(() => {
    loadUser();
  }, [loadUser]);

  const role: UserRole = user?.role || "admin";

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        isAdmin: role === "admin",
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

// Legacy helper - kept for backward compatibility during migration
export function getUserInfo(): { name: string; email: string; role: string } {
  if (typeof window === "undefined") {
    return { name: "Admin", email: "", role: "admin" };
  }
  return {
    name: localStorage.getItem("kt_name") ?? "Admin",
    email: localStorage.getItem("kt_email") ?? "",
    role: localStorage.getItem("kt_role") ?? "admin",
  };
}