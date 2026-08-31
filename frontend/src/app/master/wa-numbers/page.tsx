"use client";
import { inputCls } from "../../../lib/inputCls";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import { Plus, Edit2, Trash2, X, Phone, Send, ShieldAlert, Info } from "lucide-react";
import Breadcrumb from "../../../components/Breadcrumb";
import Modal from "../../../components/Modal";
import Toast from "../../../components/Toast";

interface WaNumber {
  id: string;
  label: string;
  phone_number: string;
  token_preview: string;
  is_active: boolean;
  created_at: string;
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
  } catch { return iso; }
}

export default function WaNumbersPage() {
  const [numbers, setNumbers] = useState<WaNumber[]>([]);
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<WaNumber | null>(null);
  const [form, setForm] = useState({ label: "", phone_number: "", token: "" });
  const [saving, setSaving] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  async function fetchNumbers() {
    try {
      const res = await apiFetch("/api/settings/wa-numbers");
      if (res.status === 403) { setForbidden(true); return; }
      if (res.ok) setNumbers(await res.json());
      else {
        const d = await res.json().catch(() => ({}));
        setToast({ message: d.detail || `Gagal memuat daftar nomor (HTTP ${res.status}).`, type: "error" });
      }
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Gagal memuat daftar nomor.", type: "error" });
    } finally { setLoading(false); }
  }

  useEffect(() => { fetchNumbers(); }, []);

  function openNew() {
    setEditing(null);
    setForm({ label: "", phone_number: "", token: "" });
    setModal(true);
  }

  function openEdit(n: WaNumber) {
    setEditing(n);
    setForm({ label: n.label, phone_number: n.phone_number, token: "" });
    setModal(true);
  }

  async function save() {
    if (!form.label.trim() || !form.phone_number.trim()) { setToast({ message: "Label dan nomor WA wajib diisi.", type: "error" }); return; }
    if (!editing && !form.token.trim()) { setToast({ message: "Token Fonnte wajib diisi.", type: "error" }); return; }
    setSaving(true);
    try {
      const payload: Record<string, string> = { label: form.label.trim(), phone_number: form.phone_number.trim() };
      // Edit: token kosong = token tetap. Tambah: token wajib (1 token = 1 device/nomor).
      if (form.token.trim()) payload.token = form.token.trim();
      const res = await apiFetch(editing ? `/api/settings/wa-numbers/${editing.id}` : "/api/settings/wa-numbers", {
        method: editing ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `Gagal menyimpan nomor (HTTP ${res.status}).`);
      }
      setToast({ message: editing ? "Nomor berhasil diperbarui." : "Nomor berhasil ditambahkan.", type: "success" });
      setModal(false);
      fetchNumbers();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Gagal menyimpan nomor.", type: "error" });
    } finally { setSaving(false); }
  }

  async function toggleActive(n: WaNumber) {
    setTogglingId(n.id);
    try {
      const res = await apiFetch(`/api/settings/wa-numbers/${n.id}`, { method: "PUT", body: JSON.stringify({ is_active: !n.is_active }) });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `Gagal mengubah status (HTTP ${res.status}).`);
      }
      fetchNumbers();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Gagal mengubah status.", type: "error" });
    } finally { setTogglingId(null); }
  }

  async function testSend(n: WaNumber) {
    setTestingId(n.id);
    try {
      const res = await apiFetch(`/api/settings/wa-numbers/${n.id}/test-send`, { method: "POST", body: JSON.stringify({}) });
      const d = await res.json().catch(() => ({}));
      if (res.ok) setToast({ message: `Tes terkirim ke ${d.target || "nomor admin"}.`, type: "success" });
      else setToast({ message: d.detail || `Gagal tes kirim (HTTP ${res.status}).`, type: "error" });
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Gagal tes kirim.", type: "error" });
    } finally { setTestingId(null); }
  }

  async function deleteNumber(id: string) {
    setDeleteId(null);
    try {
      const res = await apiFetch(`/api/settings/wa-numbers/${id}`, { method: "DELETE" });
      if (res.ok) {
        setToast({ message: "Nomor berhasil dihapus.", type: "success" });
        fetchNumbers();
      } else {
        // 409: nomor masih dipakai campaign — tampilkan detail dari body.
        const d = await res.json().catch(() => ({}));
        setToast({ message: d.detail || `Gagal hapus nomor (HTTP ${res.status}).`, type: "error" });
      }
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Gagal hapus nomor.", type: "error" });
    }
  }

  if (forbidden) {
    return (
      <div className="max-w-6xl space-y-6">
        <Breadcrumb items={[{ label: "Master" }, { label: "Nomor WA" }]} showBack backHref="/master" />
        <div className="text-center py-16 bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] space-y-3">
          <ShieldAlert size={28} className="mx-auto text-neutral-400" />
          <p className="text-sm font-semibold text-neutral-600 dark:text-neutral-300">Halaman ini khusus admin.</p>
          <p className="text-xs text-neutral-400">Hubungi admin untuk mengelola nomor WA (Fonnte).</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl space-y-6">
      <Breadcrumb items={[{ label: "Master" }, { label: "Nomor WA" }]} showBack backHref="/master" />
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
      <Modal
        open={!!deleteId}
        title="Hapus Nomor WA?"
        message="Nomor yang dihapus tidak bisa dikembalikan. Nomor yang masih dipakai campaign tidak bisa dihapus."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteId !== null && deleteNumber(deleteId!)}
        onCancel={() => setDeleteId(null)}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Kelola Nomor WA (Fonnte)</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Daftar nomor pengirim WhatsApp untuk blast dan pesan keluar.</p>
        </div>
        <button onClick={openNew} className="flex items-center gap-1.5 px-4 py-2.5 bg-brand-yellow hover:bg-amber-600 text-white text-sm font-semibold rounded-xl transition-colors">
          <Plus size={16} /> Tambah Nomor
        </button>
      </div>

      <div className="flex items-start gap-2 rounded-2xl border border-amber-100 bg-amber-50 p-3 dark:border-amber-900/40 dark:bg-amber-900/20">
        <Info size={14} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <p className="text-[11px] leading-relaxed text-amber-700 dark:text-amber-300 font-medium">
          1 token Fonnte = 1 device/nomor. Token ambil dari dashboard Fonnte (Devices). Blast tanpa pilih nomor = pakai nomor utama.
        </p>
      </div>

      {loading ? (
        <div className="space-y-3">{[1, 2, 3].map(i => <div key={i} className="h-20 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />)}</div>
      ) : numbers.length === 0 ? (
        <div className="text-center py-12 bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] text-gray-400 text-sm">
          Belum ada nomor WA. Tambahkan nomor pertamamu dengan token dari dashboard Fonnte.
        </div>
      ) : (
        <div className="space-y-3">
          {numbers.map(n => (
            <div key={n.id} className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] shadow-sm p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 min-w-0 flex-1">
                  <div className="w-9 h-9 rounded-lg bg-brand-yellow/10 flex items-center justify-center shrink-0 mt-0.5"><Phone size={15} className="text-brand-yellow" /></div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{n.label}</p>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${n.is_active ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : "bg-gray-200 dark:bg-gray-700 text-gray-500"}`}>
                        {n.is_active ? "Aktif" : "Nonaktif"}
                      </span>
                    </div>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">{n.phone_number || "—"}</p>
                    <p className="text-[11px] text-neutral-400 dark:text-neutral-500 font-mono mt-0.5 truncate">Token: {n.token_preview || "—"}</p>
                    <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-1">Ditambahkan {formatDate(n.created_at)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0 ml-3 flex-wrap justify-end">
                  <button onClick={() => testSend(n)} disabled={testingId === n.id}
                    className="flex items-center gap-1 px-2 py-1 text-[10px] font-semibold border border-gray-200 dark:border-gray-700 rounded-lg text-neutral-500 dark:text-neutral-400 hover:text-brand-yellow hover:border-brand-yellow/40 disabled:opacity-50 transition-colors">
                    <Send size={11} /> {testingId === n.id ? "Mengirim…" : "Tes kirim"}
                  </button>
                  <button onClick={() => toggleActive(n)} disabled={togglingId === n.id}
                    className="px-2 py-1 text-[10px] font-semibold border border-gray-200 dark:border-gray-700 rounded-lg text-neutral-500 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200 disabled:opacity-50 transition-colors">
                    {togglingId === n.id ? "…" : n.is_active ? "Nonaktifkan" : "Aktifkan"}
                  </button>
                  <button onClick={() => openEdit(n)} className="p-1.5 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors"><Edit2 size={14} /></button>
                  <button onClick={() => setDeleteId(n.id)} className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors"><Trash2 size={14} /></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Tambah/Edit */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-lg p-6 space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editing ? "Edit Nomor WA" : "Tambah Nomor WA"}</h3>
              <button onClick={() => setModal(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Label</label>
                <input value={form.label} onChange={e => setForm(f => ({ ...f, label: e.target.value }))} className={inputCls} placeholder="Contoh: Nomor Sales Utama" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nomor WhatsApp</label>
                <input value={form.phone_number} onChange={e => setForm(f => ({ ...f, phone_number: e.target.value }))} className={inputCls} placeholder="6281234567890" />
                <p className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1">Format internasional tanpa tanda +, contoh: 6281234567890.</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Token Fonnte {editing ? "(opsional)" : "*"}</label>
                <input value={form.token} onChange={e => setForm(f => ({ ...f, token: e.target.value }))} className={inputCls + " font-mono"} placeholder="Token dari dashboard Fonnte (Devices)" />
                <p className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1">
                  {editing ? "Kosongkan bila tidak ingin mengganti token." : "1 token = 1 device/nomor. Ambil dari dashboard Fonnte → Devices."}
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setModal(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={save} disabled={saving} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors disabled:opacity-50">{saving ? "Menyimpan…" : "Simpan"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
