"use client";

import { FormEvent, useEffect, useState } from "react";

const API_BASE = (() => {
  if (typeof window === "undefined") return process.env.NEXT_PUBLIC_API_URL || "";
  const host = window.location.hostname;
  if (host.endsWith(".vercel.app") || host === "vercel.app") return "";
  if (/^(localhost|127\.0\.0\.1)(:\d+)?$/.test(host)) return "http://localhost:8000";
  if (host.endsWith("kantorteman.my.id")) return "";
  return process.env.NEXT_PUBLIC_API_URL || "";
})();

export default function ResetPasswordPage() {
  const [token, setToken] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setToken(params.get("token") ?? "");
  }, []);

  async function submitRequest(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE}/api/auth/password/forgot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail ?? "Gagal meminta reset password.");
      setMessage(body.message ?? "Jika email terdaftar, instruksi reset password akan dikirim.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal meminta reset password.");
    } finally {
      setLoading(false);
    }
  }

  async function submitReset(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch(`${API_BASE}/api/auth/password/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail ?? "Reset password gagal.");
      setMessage("Password berhasil diganti. Silakan login dengan password baru.");
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset password gagal.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[var(--bg-canvas)] flex items-center justify-center p-4">
      <section className="w-full max-w-md rounded-2xl border border-gray-100 bg-white p-8 shadow-xl dark:border-neutral-800 dark:bg-neutral-900">
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Reset Password</h1>
        <p className="mt-2 text-sm text-neutral-500">
          {token ? "Masukkan password baru untuk akun KantorTeman." : "Masukkan email akun KantorTeman untuk menerima link reset."}
        </p>

        <form onSubmit={token ? submitReset : submitRequest} className="mt-6 space-y-4">
          {token ? (
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password baru"
              className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm outline-none focus:border-amber-400 focus:bg-white focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-50"
            />
          ) : (
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin@kantorteman.com"
              className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm outline-none focus:border-amber-400 focus:bg-white focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-50"
            />
          )}

          {error && <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
          {message && <p className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">{message}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-brand-yellow py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-amber-600 disabled:opacity-50"
          >
            {loading ? "Memproses..." : token ? "Ganti Password" : "Kirim Link Reset"}
          </button>
          <a href="/login" className="block text-center text-xs font-semibold text-amber-700 hover:text-amber-800">
            Kembali ke login
          </a>
        </form>
      </section>
    </main>
  );
}
