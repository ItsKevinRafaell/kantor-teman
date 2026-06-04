"use client";

import { useState } from "react";
import { apiFetch } from "../../lib/api";
import { inputCls, inputClsLarge } from "../../lib/inputCls";

interface AddClientModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  setToast: (toast: { message: string; type: "success" | "error" | "info" } | null) => void;
}

export default function AddClientModal({ open, onClose, onSuccess, setToast }: AddClientModalProps) {
  const [form, setForm] = useState({ business_name: "", phone_number: "", owner_name: "", purchased_product: "" });
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  async function handleSave() {
    if (!form.business_name || !form.phone_number) return;
    setSaving(true);
    try {
      const res = await apiFetch("/api/contacts", { method: "POST", body: JSON.stringify(form) });
      if (res.ok) {
        setForm({ business_name: "", phone_number: "", owner_name: "", purchased_product: "" });
        setToast({ message: "Klien berhasil ditambahkan!", type: "success" });
        onSuccess();
        onClose();
      } else {
        const d = await res.json().catch(() => ({}));
        setToast({ message: d.detail || "Gagal menambah klien.", type: "error" });
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Tambah Klien Baru</h3>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Bisnis *</label>
            <input value={form.business_name} onChange={e => setForm(f => ({ ...f, business_name: e.target.value }))} className={inputCls} placeholder="Contoh: PT Maju Jaya" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nomor WhatsApp *</label>
            <input value={form.phone_number} onChange={e => setForm(f => ({ ...f, phone_number: e.target.value }))} className={inputCls} placeholder="628123456789" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Owner</label>
            <input value={form.owner_name} onChange={e => setForm(f => ({ ...f, owner_name: e.target.value }))} className={inputCls} placeholder="Opsional" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Produk/Layanan</label>
            <input value={form.purchased_product} onChange={e => setForm(f => ({ ...f, purchased_product: e.target.value }))} className={inputCls} placeholder="Opsional" />
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
          <button onClick={handleSave} disabled={saving} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors disabled:opacity-50">
            {saving ? "Menyimpan..." : "Simpan"}
          </button>
        </div>
      </div>
    </div>
  );
}