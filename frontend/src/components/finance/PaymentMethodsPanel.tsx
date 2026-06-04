"use client";
import { inputCls, inputClsLarge } from "../../lib/inputCls";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../lib/api";
import { Plus, Edit2, Trash2, X, CreditCard } from "lucide-react";
import Modal from "../Modal";
import Toast from "../Toast";

interface PaymentMethod {
  id: number;
  name: string;
  account_number: string | null;
  account_name: string | null;
  notes: string | null;
  is_active: boolean;
  position: number;
}

export default function PaymentMethodsPanel() {
  const [items, setItems] = useState<PaymentMethod[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<PaymentMethod | null>(null);
  const [form, setForm] = useState({ name: "", account_number: "", account_name: "", notes: "", is_active: true, position: 0 });
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch("/api/finance/payment-methods");
      if (res.ok) setItems(await res.json());
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  function openNew() {
    setEditing(null);
    setForm({ name: "", account_number: "", account_name: "", notes: "", is_active: true, position: items.length });
    setModal(true);
  }

  function openEdit(pm: PaymentMethod) {
    setEditing(pm);
    setForm({
      name: pm.name,
      account_number: pm.account_number || "",
      account_name: pm.account_name || "",
      notes: pm.notes || "",
      is_active: pm.is_active,
      position: pm.position,
    });
    setModal(true);
  }

  async function save() {
    if (!form.name.trim()) {
      setToast({ message: "Nama wajib diisi.", type: "error" });
      return;
    }
    const method = editing ? "PUT" : "POST";
    const url = editing ? `/api/finance/payment-methods/${editing.id}` : "/api/finance/payment-methods";
    const res = await apiFetch(url, { method, body: JSON.stringify(form) });
    if (res.ok) {
      setToast({ message: "Berhasil disimpan.", type: "success" });
      setModal(false);
      setEditing(null);
      fetchAll();
    } else {
      setToast({ message: "Gagal simpan.", type: "error" });
    }
  }

  async function deleteItem(id: number) {
    const res = await apiFetch(`/api/finance/payment-methods/${id}`, { method: "DELETE" });
    if (res.ok) {
      setToast({ message: "Berhasil dihapus.", type: "success" });
      fetchAll();
    } else {
      setToast({ message: "Gagal hapus.", type: "error" });
    }
    setDeleteId(null);
  }


  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map(i => <div key={i} className="h-20 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />)}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
      <Modal
        open={!!deleteId}
        title="Hapus Metode Pembayaran?"
        message="Item yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteId !== null && deleteItem(deleteId!)}
        onCancel={() => setDeleteId(null)}
      />

      <div className="flex justify-between items-center">
        <p className="text-sm text-gray-500">Atur rekening / metode pembayaran yang muncul otomatis di invoice.</p>
        <button onClick={openNew} className="flex items-center gap-1.5 px-4 py-2 bg-brand-yellow hover:bg-amber-600 text-white text-sm font-semibold rounded-xl transition-colors">
          <Plus size={16} /> Tambah
        </button>
      </div>

      {items.length === 0 ? (
        <div className="text-center py-12 bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] text-gray-400 text-sm">
          Belum ada metode pembayaran. Tambahkan rekening / e-wallet pertama.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map(pm => (
            <div key={pm.id} className={`bg-[var(--bg-surface)] rounded-2xl border shadow-sm p-4 ${pm.is_active ? "border-[var(--border-default)]" : "border-gray-200 dark:border-neutral-700 opacity-60"}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/30 text-amber-600 flex items-center justify-center">
                    <CreditCard size={18} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{pm.name}</p>
                      {!pm.is_active && <span className="px-2 py-0.5 text-[10px] font-semibold bg-gray-200 dark:bg-gray-700 text-gray-500 rounded-full">Nonaktif</span>}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {pm.account_number || "—"}
                      {pm.account_name && <span> · a.n. {pm.account_name}</span>}
                    </p>
                    {pm.notes && <p className="text-[11px] text-gray-400 mt-0.5">{pm.notes}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(pm)} className="p-1.5 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors"><Edit2 size={14} /></button>
                  <button onClick={() => setDeleteId(pm.id)} className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors"><Trash2 size={14} /></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editing ? "Edit Metode Pembayaran" : "Tambah Metode Pembayaran"}</h3>
              <button onClick={() => setModal(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Bank BCA / GoPay / Cash" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nomor Rekening / Akun</label>
                <input value={form.account_number} onChange={e => setForm(f => ({ ...f, account_number: e.target.value }))} placeholder="1234567890" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Atas Nama</label>
                <input value={form.account_name} onChange={e => setForm(f => ({ ...f, account_name: e.target.value }))} placeholder="PT Teman UMKM Kita" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Catatan (opsional)</label>
                <input value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Mis: konfirmasi via WA setelah transfer" className={inputCls} />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} className="w-4 h-4 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
                <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">Aktif (tampilkan di invoice)</span>
              </label>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setModal(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={save} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
