"use client";
import NativeSelect from "../../components/ui/NativeSelect";

import { useEffect, useState } from "react";
import { Plus, Save, Trash2, Users } from "lucide-react";
import { apiFetch } from "../../lib/api";
import Toast from "../../components/Toast";

interface TeamUser {
  id: number;
  name: string;
  email: string;
  role: "admin" | "member";
}

const emptyForm = { name: "", email: "", password: "", role: "member" as "admin" | "member" };

export default function TeamTab() {
  const [users, setUsers] = useState<TeamUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editPassword, setEditPassword] = useState<Record<number, string>>({});
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  async function fetchUsers() {
    setLoading(true);
    try {
      const res = await apiFetch("/api/users");
      if (!res.ok) throw new Error("Gagal memuat user");
      setUsers(await res.json());
    } catch (e: unknown) {
      setToast({ message: e instanceof Error ? e.message : "Gagal memuat user", type: "error" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchUsers();
  }, []);

  async function createUser() {
    if (!form.name.trim() || !form.email.trim() || form.password.length < 8) {
      setToast({ message: "Nama, email, dan password minimal 8 karakter wajib diisi.", type: "error" });
      return;
    }
    setSaving(true);
    try {
      const res = await apiFetch("/api/users", { method: "POST", body: JSON.stringify(form) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Gagal membuat user");
      setForm(emptyForm);
      setToast({ message: "User tim berhasil dibuat.", type: "success" });
      await fetchUsers();
    } catch (e: unknown) {
      setToast({ message: e instanceof Error ? e.message : "Gagal membuat user", type: "error" });
    } finally {
      setSaving(false);
    }
  }

  async function updateUser(user: TeamUser) {
    const password = editPassword[user.id]?.trim();
    setSaving(true);
    try {
      const payload: Record<string, string> = { name: user.name, email: user.email, role: user.role };
      if (password) payload.password = password;
      const res = await apiFetch(`/api/users/${user.id}`, { method: "PUT", body: JSON.stringify(payload) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Gagal menyimpan user");
      setEditPassword(prev => ({ ...prev, [user.id]: "" }));
      setToast({ message: "User diperbarui.", type: "success" });
      await fetchUsers();
    } catch (e: unknown) {
      setToast({ message: e instanceof Error ? e.message : "Gagal menyimpan user", type: "error" });
    } finally {
      setSaving(false);
    }
  }

  async function deleteUser(user: TeamUser) {
    const ok = window.confirm(`Hapus user ${user.name}?`);
    if (!ok) return;
    setSaving(true);
    try {
      const res = await apiFetch(`/api/users/${user.id}`, { method: "DELETE" });
      if (!res.ok && res.status !== 204) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Gagal menghapus user");
      }
      setToast({ message: "User dihapus.", type: "success" });
      setUsers(prev => prev.filter(u => u.id !== user.id));
    } catch (e: unknown) {
      setToast({ message: e instanceof Error ? e.message : "Gagal menghapus user", type: "error" });
    } finally {
      setSaving(false);
    }
  }

  function patchUser(id: number, patch: Partial<TeamUser>) {
    setUsers(prev => prev.map(u => u.id === id ? { ...u, ...patch } : u));
  }

  return (
    <div className="max-w-4xl space-y-5">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />

      <section className="rounded-2xl border border-[var(--border-default)] bg-white p-5 shadow-sm dark:bg-[var(--bg-canvas)]">
        <div className="mb-4 flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600 dark:bg-amber-950/20 dark:text-amber-300">
            <Users size={18} />
          </div>
          <div>
            <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Tim & Role</h2>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">MVP HCM untuk bikin akun tim dan mengatur akses admin/member.</p>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-[1fr_1fr_160px_130px_auto]">
          <input value={form.name} onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))}
            className="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-900"
            placeholder="Nama tim" />
          <input value={form.email} onChange={e => setForm(prev => ({ ...prev, email: e.target.value }))}
            className="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-900"
            placeholder="email@domain.com" />
          <input type="password" value={form.password} onChange={e => setForm(prev => ({ ...prev, password: e.target.value }))}
            className="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-900"
            placeholder="Password awal" />
          <NativeSelect value={form.role} onChange={v => setForm(prev => ({ ...prev, role: v as any }))} clearable={false} options={[{value:"admin",label:"Admin"},{value:"member",label:"Member"}]} />
          <button onClick={createUser} disabled={saving}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-amber-500 px-4 py-2 text-sm font-bold text-white hover:bg-amber-600 disabled:opacity-50">
            <Plus size={15} /> Buat
          </button>
        </div>
      </section>

      <section className="overflow-hidden rounded-2xl border border-[var(--border-default)] bg-white shadow-sm dark:bg-[var(--bg-canvas)]">
        {loading ? (
          <div className="p-5 text-sm text-neutral-400">Memuat user...</div>
        ) : (
          <div className="divide-y divide-[var(--border-subtle)]">
            {users.map(user => (
              <div key={user.id} className="grid gap-3 p-4 md:grid-cols-[1fr_1.2fr_130px_160px_auto_auto] md:items-center">
                <input value={user.name} onChange={e => patchUser(user.id, { name: e.target.value })}
                  className="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-900" />
                <input value={user.email} onChange={e => patchUser(user.id, { email: e.target.value })}
                  className="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-900" />
                <NativeSelect value={user.role} onChange={v => patchUser(user.id, { role: v as any })} clearable={false} options={[{value:"admin",label:"Admin"},{value:"member",label:"Member"}]} />
                <input type="password" value={editPassword[user.id] || ""} onChange={e => setEditPassword(prev => ({ ...prev, [user.id]: e.target.value }))}
                  className="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-900"
                  placeholder="Reset password" />
                <button onClick={() => updateUser(user)} disabled={saving}
                  className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-neutral-900 px-3 py-2 text-xs font-bold text-white hover:bg-neutral-700 disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900">
                  <Save size={13} /> Simpan
                </button>
                <button onClick={() => deleteUser(user)} disabled={saving}
                  className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-red-50 px-3 py-2 text-xs font-bold text-red-600 hover:bg-red-100 disabled:opacity-50 dark:bg-red-950/20 dark:text-red-300">
                  <Trash2 size={13} /> Hapus
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="rounded-2xl border border-amber-100 bg-amber-50/50 p-4 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/10 dark:text-amber-200">
        <p className="font-semibold">Aturan MVP role:</p>
        <p className="mt-1">Admin bisa mengatur sistem dan menghapus data. Member bisa kerja di operasional seperti board, workspace, klien, dan dokumen tanpa akses menu admin-only.</p>
      </div>
    </div>
  );
}
