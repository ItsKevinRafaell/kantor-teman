"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { setToken } from "../../lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/brand-kit/public`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data?.assets) return;
        const logo = data.assets.find((a: { asset_type: string }) => a.asset_type === "logo_primary");
        if (logo?.file_url) setLogoUrl(`${API_BASE}${logo.file_url}`);
      })
      .catch(() => {});
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
        credentials: "include",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? "Login gagal");
      }
      const data = await res.json();
      setToken(data.access_token, data.name, data.email, data.role || "admin");
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Terjadi kesalahan.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-canvas)] dark:bg-[var(--bg-canvas)] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          {logoUrl ? (
            <img src={logoUrl} alt="Kantor Teman" className="h-16 w-auto mx-auto object-contain" />
          ) : (
            <h1 className="text-3xl font-bold text-neutral-900 dark:text-neutral-50">
              Kantor Teman
            </h1>
          )}
          <p className="text-gray-400 dark:text-gray-500 text-sm mt-2">CRM Internal · Masuk untuk melanjutkan</p>
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-neutral-900 rounded-2xl shadow-xl border border-gray-100 dark:border-neutral-800 p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
                autoComplete="email"
                className="w-full px-4 py-3 border border-gray-200 dark:border-neutral-700 rounded-xl text-sm bg-gray-50 dark:bg-neutral-800 dark:text-gray-100 focus:bg-white dark:focus:bg-neutral-900 focus:outline-none focus:ring-2 focus:ring-amber-300 focus:border-amber-400 disabled:opacity-60 transition"
                placeholder="admin@kantorteman.com"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1.5">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                autoComplete="current-password"
                className="w-full px-4 py-3 border border-gray-200 dark:border-neutral-700 rounded-xl text-sm bg-gray-50 dark:bg-neutral-800 dark:text-gray-100 focus:bg-white dark:focus:bg-neutral-900 focus:outline-none focus:ring-2 focus:ring-amber-300 focus:border-amber-400 disabled:opacity-60 transition"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/40 text-red-600 dark:text-red-400 rounded-xl px-4 py-3 text-sm" role="alert">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full py-3 bg-brand-yellow hover:bg-amber-600 text-white font-semibold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm hover:shadow-md text-sm"
            >
              {loading ? "Masuk..." : "Masuk"}
            </button>
          </form>

        </div>
      </div>
    </div>
  );
}
