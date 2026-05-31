"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../lib/api";
import { Plus, Edit2, Trash2, X, AlertTriangle } from "lucide-react";
import { formatRupiahInput, cleanRupiahInput } from "../../utils/formatter";
import Modal from "../Modal";
import Toast from "../Toast";

interface WalletData {
  id: number;
  name: string;
  balance: number;
}

interface SubscriptionData {
  id: number;
  wallet_id: number;
  name: string;
  amount: number;
  billing_cycle: string;
  next_billing_date: string;
  is_active: boolean;
  wallet_name: string | null;
}

function formatRupiah(num: number): string {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0 }).format(num);
}

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  target.setHours(0, 0, 0, 0);
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

export default function SubscriptionsPanel() {
  const [subscriptions, setSubscriptions] = useState<SubscriptionData[]>([]);
  const [wallets, setWallets] = useState<WalletData[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<SubscriptionData | null>(null);
  const [form, setForm] = useState({ wallet_id: 0, name: "", amount: 0, billing_cycle: "monthly", next_billing_date: "", is_active: true });
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [sRes, wRes] = await Promise.all([
        apiFetch("/api/finance/subscriptions"),
        apiFetch("/api/finance/wallets"),
      ]);
      if (sRes.ok) setSubscriptions(await sRes.json());
      if (wRes.ok) setWallets(await wRes.json());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  function openNew() {
    setEditing(null);
    setForm({ wallet_id: wallets[0]?.id || 0, name: "", amount: 0, billing_cycle: "monthly", next_billing_date: new Date().toISOString().slice(0, 10), is_active: true });
    setModal(true);
  }

  function openEdit(sub: SubscriptionData) {
    setEditing(sub);
    setForm({ wallet_id: sub.wallet_id, name: sub.name, amount: sub.amount, billing_cycle: sub.billing_cycle, next_billing_date: sub.next_billing_date, is_active: sub.is_active });
    setModal(true);
  }

  async function save() {
    if (!form.name.trim()) {
      setToast({ message: "Nama langganan wajib diisi.", type: "error" });
      return;
    }
    if (!form.amount || form.amount <= 0) {
      setToast({ message: "Jumlah harus lebih dari 0.", type: "error" });
      return;
    }
    const method = editing ? "PUT" : "POST";
    const url = editing ? `/api/finance/subscriptions/${editing.id}` : "/api/finance/subscriptions";
    const res = await apiFetch(url, { method, body: JSON.stringify(form) });
    if (res.ok) {
      setToast({ message: "Berhasil disimpan.", type: "success" });
      setModal(false);
      setEditing(null);
      fetchAll();
    }
  }

  async function deleteSub(id: number) {
    const res = await apiFetch(`/api/finance/subscriptions/${id}`, { method: "DELETE" });
    if (res.ok) { setToast({ message: "Berhasil dihapus.", type: "success" }); fetchAll(); }
    else { setToast({ message: "Gagal hapus.", type: "error" }); }
    setDeleteId(null);
  }

  async function runAutoDeduct() {
    const res = await apiFetch("/api/finance/subscriptions/auto-deduct", { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      setToast({ message: `Auto-deduct selesai: ${data.deducted_count} langganan diproses.`, type: "info" });
      fetchAll();
    }
  }

  const inputCls = "w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50 transition";

  const totalMonthly = subscriptions.filter(s => s.is_active).reduce((sum, s) => {
    return sum + (s.billing_cycle === "monthly" ? s.amount : s.amount / 12);
  }, 0);

  if (loading) {
    return (
      <div className="space-y-6">
        <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
        <Modal
          open={!!deleteId}
          title="Hapus Langganan?"
          message="Item yang dihapus tidak bisa dikembalikan."
          confirmLabel="Hapus"
          confirmClass="bg-red-600 hover:bg-red-700"
          onConfirm={() => deleteId !== null && deleteSub(deleteId!)}
          onCancel={() => setDeleteId(null)}
        />
        <div className="h-20 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />
        <div className="space-y-3">
          {[1, 2, 3].map(i => <div key={i} className="h-20 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
      <Modal
        open={!!deleteId}
        title="Hapus Langganan?"
        message="Item yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteId !== null && deleteSub(deleteId!)}
        onCancel={() => setDeleteId(null)}
      />
      {/* Action buttons */}
      <div className="flex gap-2 justify-end">
        <button onClick={runAutoDeduct}
          title="Catat semua langganan yang jatuh tempo bulan ini sebagai pengeluaran otomatis"
          className="px-2.5 py-1.5 sm:px-4 sm:py-2.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs sm:text-sm font-semibold rounded-xl transition-colors">
          Catat Pengeluaran Bulan Ini
        </button>
        <button onClick={openNew} className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs sm:text-sm font-semibold rounded-xl transition-colors">
          <Plus size={16} /> Tambah
        </button>
      </div>

      {/* Summary Card */}
      <div className="bg-gradient-to-r from-amber-500 to-amber-600 rounded-2xl p-5 text-white shadow-lg">
        <p className="text-sm font-medium opacity-90">Total Pengeluaran Rutin / Bulan</p>
        <p className="text-3xl font-bold mt-1">{formatRupiah(totalMonthly)}</p>
        <p className="text-xs opacity-75 mt-1">{subscriptions.filter(s => s.is_active).length} langganan aktif</p>
      </div>

      {/* Subscriptions List */}
      {subscriptions.length === 0 ? (
        <div className="text-center py-12 bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] text-gray-400 text-sm">
          Belum ada langganan. Tambahkan langganan pertamamu.
        </div>
      ) : (
        <div className="space-y-3">
          {subscriptions.map(sub => {
            const days = daysUntil(sub.next_billing_date);
            const isNearDue = days >= 0 && days <= 3;
            const isOverdue = days < 0;
            return (
              <div key={sub.id} className={`bg-[var(--bg-surface)] rounded-2xl border shadow-sm p-4 transition-all ${isNearDue ? "border-amber-300 dark:border-amber-600 bg-amber-50/50 dark:bg-amber-900/10" : isOverdue ? "border-red-300 dark:border-red-600 bg-red-50/50 dark:bg-red-900/10" : "border-[var(--border-default)]"}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold ${sub.is_active ? "bg-amber-500" : "bg-gray-400"}`}>
                      {sub.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{sub.name}</p>
                        {!sub.is_active && <span className="px-2 py-0.5 text-[10px] font-semibold bg-gray-200 dark:bg-gray-700 text-gray-500 rounded-full">Nonaktif</span>}
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {sub.wallet_name} · {sub.billing_cycle === "monthly" ? "Bulanan" : "Tahunan"} · Jatuh tempo: {sub.next_billing_date}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {isNearDue && (
                      <div className="flex items-center gap-1 px-2.5 py-1 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded-lg">
                        <AlertTriangle size={12} />
                        <span className="text-xs font-semibold">Mendekati Jatuh Tempo</span>
                      </div>
                    )}
                    {isOverdue && (
                      <div className="flex items-center gap-1 px-2.5 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg">
                        <AlertTriangle size={12} />
                        <span className="text-xs font-semibold">Jatuh Tempo!</span>
                      </div>
                    )}
                    <span className="text-lg font-bold text-neutral-900 dark:text-neutral-50">{formatRupiah(sub.amount)}</span>
                    <button onClick={() => openEdit(sub)} className="p-1.5 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors"><Edit2 size={14} /></button>
                    <button onClick={() => setDeleteId(sub.id)} className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors"><Trash2 size={14} /></button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editing ? "Edit Langganan" : "Tambah Langganan"}</h3>
              <button onClick={() => setModal(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Langganan</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Contoh: Hosting, Domain, Canva Pro" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Dompet</label>
                <select value={form.wallet_id} onChange={e => setForm(f => ({ ...f, wallet_id: Number(e.target.value) }))} className={inputCls}>
                  {wallets.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Jumlah (Rp)</label>
                <input type="text" value={form.amount ? formatRupiahInput(form.amount) : ""} onChange={e => setForm(f => ({ ...f, amount: cleanRupiahInput(e.target.value) }))} className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Siklus Billing</label>
                <select value={form.billing_cycle} onChange={e => setForm(f => ({ ...f, billing_cycle: e.target.value }))} className={inputCls}>
                  <option value="monthly">Bulanan</option>
                  <option value="yearly">Tahunan</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Tanggal Jatuh Tempo Berikutnya</label>
                <input type="date" value={form.next_billing_date} onChange={e => setForm(f => ({ ...f, next_billing_date: e.target.value }))} className={inputCls} />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} className="w-4 h-4 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
                <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">Aktif</span>
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
