"use client";
import { inputCls, inputClsLarge } from "../../lib/inputCls";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "../../lib/api";
import { Plus, Wallet, TrendingUp, Target, PieChart, Edit2, Trash2, X, Download, RotateCcw } from "lucide-react";
import { formatRupiah, formatRupiahInput, cleanRupiahInput } from "../../utils/formatter";
import { downloadBlob } from "../../utils/download";
import Modal from "../Modal";
import Toast from "../Toast";
import Pagination from "../Pagination";

interface WalletData {
  id: number;
  name: string;
  balance: number;
  icon: string | null;
  color: string | null;
}

interface TransactionData {
  id: number;
  wallet_id: number;
  type: string;
  amount: number;
  category: string | null;
  date: string;
  notes: string | null;
  lead_id: number | null;
  is_billed: boolean;
  is_archived: boolean;
  lead_name: string | null;
}

interface ReportData {
  total_balance: number;
  break_even_point: number;
  financial_runway_months: number;
  expense_by_category: { category: string; amount: number }[];
}

interface ClientData {
  id: number;
  lead_id: number;
  business_name: string;
}


const COLORS = ["#737373", "#a3a3a3", "#525252", "#d4d4d4", "#78716c", "#94a3b8", "#71717a", "#9ca3af"];

export default function FinancePanel() {
  const [wallets, setWallets] = useState<WalletData[]>([]);
  const [transactions, setTransactions] = useState<TransactionData[]>([]);
  const [report, setReport] = useState<ReportData | null>(null);
  const [clients, setClients] = useState<ClientData[]>([]);
  const [loading, setLoading] = useState(true);
  const [showArchived, setShowArchived] = useState(false);
  const [txnPage, setTxnPage] = useState(1);
  const TXN_PAGE_SIZE = 20;
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Wallet modal
  const [walletModal, setWalletModal] = useState(false);
  const [editingWallet, setEditingWallet] = useState<WalletData | null>(null);
  const [walletForm, setWalletForm] = useState({ name: "", balance: 0, icon: "", color: "#f59e0b" });

  // Transaction modal
  const [txnModal, setTxnModal] = useState(false);
  const [txnForm, setTxnForm] = useState({ wallet_id: 0, type: "expense", amount: 0, category: "", date: new Date().toISOString().slice(0, 10), notes: "", lead_id: null as number | null, is_billed: false });
  const [linkClient, setLinkClient] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; type: "wallet" | "transaction" } | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const archiveParam = showArchived ? "&include_archived=true" : "";
      const [wRes, tRes, rRes, cRes] = await Promise.all([
        apiFetch("/api/finance/wallets"),
        apiFetch(`/api/finance/transactions?${archiveParam}`),
        apiFetch("/api/finance/reports"),
        apiFetch("/api/contacts"),
      ]);
      if (wRes.ok) setWallets(await wRes.json());
      if (tRes.ok) setTransactions(await tRes.json());
      if (rRes.ok) setReport(await rRes.json());
      if (cRes.ok) {
        const contacts = await cRes.json();
        setClients(
          contacts
            .filter((c: { lead_id?: number | null }) => c.lead_id)
            .map((c: { id: number; lead_id: number; business_name: string }) => ({ id: c.id, lead_id: c.lead_id, business_name: c.business_name }))
        );
      }
    } finally {
      setLoading(false);
    }
  }, [showArchived]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(transactions.length / TXN_PAGE_SIZE));
    if (txnPage > totalPages) setTxnPage(totalPages);
  }, [transactions.length, txnPage]);

  useEffect(() => {
    fetchAll();
    intervalRef.current = setInterval(fetchAll, 30000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchAll]);

  async function saveWallet() {
    if (!walletForm.name.trim()) {
      setToast({ message: "Nama dompet wajib diisi.", type: "error" });
      return;
    }
    const method = editingWallet ? "PUT" : "POST";
    const url = editingWallet ? `/api/finance/wallets/${editingWallet.id}` : "/api/finance/wallets";
    const res = await apiFetch(url, { method, body: JSON.stringify(walletForm) });
    if (res.ok) {
      setToast({ message: "Dompet berhasil disimpan.", type: "success" });
      setWalletModal(false);
      setEditingWallet(null);
      fetchAll();
    }
  }

  async function deleteWallet(id: number) {
    const res = await apiFetch(`/api/finance/wallets/${id}`, { method: "DELETE" });
    if (res.ok) {
      setToast({ message: "Dompet berhasil dihapus.", type: "success" });
      fetchAll();
    } else {
      setToast({ message: "Gagal hapus dompet.", type: "error" });
    }
    setDeleteTarget(null);
  }

  async function saveTransaction() {
    if (!txnForm.amount || txnForm.amount <= 0) {
      setToast({ message: "Jumlah harus lebih dari 0.", type: "error" });
      return;
    }
    if (!txnForm.category?.trim()) {
      setToast({ message: "Kategori wajib diisi.", type: "error" });
      return;
    }
    if (linkClient && !txnForm.lead_id) {
      setToast({ message: "Pilih klien yang sudah terhubung ke lead.", type: "error" });
      return;
    }
    const payload = { ...txnForm, lead_id: linkClient ? txnForm.lead_id : null };
    const res = await apiFetch("/api/finance/transactions", { method: "POST", body: JSON.stringify(payload) });
    if (res.ok) {
      setToast({ message: "Transaksi berhasil disimpan.", type: "success" });
      setTxnModal(false);
      setTxnForm({ wallet_id: 0, type: "expense", amount: 0, category: "", date: new Date().toISOString().slice(0, 10), notes: "", lead_id: null, is_billed: false });
      setLinkClient(false);
      fetchAll();
    }
  }

  async function deleteTransaction(id: number) {
    const res = await apiFetch(`/api/finance/transactions/${id}`, { method: "DELETE" });
    if (res.ok) {
      setToast({ message: "Transaksi berhasil dihapus.", type: "success" });
      fetchAll();
    } else {
      setToast({ message: "Gagal hapus transaksi.", type: "error" });
    }
    setDeleteTarget(null);
  }

  async function restoreTransaction(id: number) {
    const res = await apiFetch(`/api/finance/transactions/restore/${id}`, { method: "POST" });
    if (res.ok) fetchAll();
  }

  async function exportCSV() {
    const res = await apiFetch("/api/export/finance");
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "finance_export.csv";
      a.click();
      URL.revokeObjectURL(url);
    }
  }

  function openEditWallet(w: WalletData) {
    setEditingWallet(w);
    setWalletForm({ name: w.name, balance: w.balance, icon: w.icon || "", color: w.color || "#f59e0b" });
    setWalletModal(true);
  }

  function openNewWallet() {
    setEditingWallet(null);
    setWalletForm({ name: "", balance: 0, icon: "", color: "#f59e0b" });
    setWalletModal(true);
  }

  function openNewTransaction() {
    setTxnForm({ wallet_id: wallets[0]?.id || 0, type: "expense", amount: 0, category: "", date: new Date().toISOString().slice(0, 10), notes: "", lead_id: null, is_billed: false });
    setLinkClient(false);
    setTxnModal(true);
  }

  const totalExpenseCategory = report?.expense_by_category.reduce((s, c) => s + c.amount, 0) || 0;
  const pagedTransactions = transactions.slice((txnPage - 1) * TXN_PAGE_SIZE, txnPage * TXN_PAGE_SIZE);


  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => <div key={i} className="h-32 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
      <Modal
        open={!!deleteTarget}
        title={deleteTarget?.type === "wallet" ? "Hapus Dompet?" : "Hapus Transaksi?"}
        message={deleteTarget?.type === "wallet" ? "Semua data dompet ini akan dihapus permanen." : "Transaksi yang dihapus tidak bisa dikembalikan."}
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => {
          if (!deleteTarget) return;
          if (deleteTarget.type === "wallet") deleteWallet(deleteTarget.id);
          else deleteTransaction(deleteTarget.id);
        }}
        onCancel={() => setDeleteTarget(null)}
      />
      {/* Action buttons */}
      <div className="flex flex-wrap gap-2 justify-end">
        <button onClick={exportCSV} className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs sm:text-sm font-semibold rounded-xl transition-colors">
          <Download size={14} /> Export CSV
        </button>
        <button onClick={openNewTransaction} className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs sm:text-sm font-semibold rounded-xl transition-colors">
          <Plus size={16} /> Transaksi
        </button>
      </div>

      {/* Top Cards: Runway & BEP */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={20} className="text-neutral-500 dark:text-neutral-400" />
            <span className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Financial Runway</span>
          </div>
          <p className="text-3xl font-bold text-neutral-900 dark:text-neutral-50">{report?.financial_runway_months ?? 0} Bulan</p>
          <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">Aman sebelum kehabisan dana</p>
        </div>

        <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Target size={20} className="text-neutral-500 dark:text-neutral-400" />
            <span className="text-sm font-medium text-neutral-500 dark:text-neutral-400">BEP Bulan Ini</span>
          </div>
          <p className="text-3xl font-bold text-neutral-900 dark:text-neutral-50">{formatRupiah(report?.break_even_point ?? 0)}</p>
          <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">Target omzet minimum</p>
        </div>

        <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Wallet size={20} className="text-neutral-500 dark:text-neutral-400" />
            <span className="text-sm font-medium text-neutral-500 dark:text-neutral-400">Total Saldo</span>
          </div>
          <p className="text-3xl font-bold text-neutral-900 dark:text-neutral-50">{formatRupiah(report?.total_balance ?? 0)}</p>
          <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">Semua dompet digabung</p>
        </div>
      </div>

      {/* Wallets Grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-50">Dompet Virtual</h2>
          <button onClick={openNewWallet} className="flex items-center gap-1 text-sm text-brand-yellow hover:text-amber-600 font-semibold transition-colors">
            <Plus size={14} /> Tambah Dompet
          </button>
        </div>
        {wallets.length === 0 ? (
          <div className="text-center py-12 bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] text-gray-400 text-sm">
            Belum ada dompet. Buat dompet pertamamu.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {wallets.map(w => (
              <div key={w.id} className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-4 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: w.color || "#f59e0b" }}>
                      {w.icon || w.name.charAt(0).toUpperCase()}
                    </div>
                    <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{w.name}</span>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => openEditWallet(w)} className="p-1.5 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors"><Edit2 size={13} /></button>
                    <button onClick={() => setDeleteTarget({ id: w.id, type: "wallet" })} className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors"><Trash2 size={13} /></button>
                  </div>
                </div>
                <p className={`text-xl font-bold ${w.balance >= 0 ? "text-neutral-900 dark:text-neutral-50" : "text-red-500"}`}>{formatRupiah(w.balance)}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Expense by Category Chart */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <PieChart size={18} className="text-brand-yellow" />
          <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-50">Pengeluaran Bulan Ini</h2>
        </div>
        {(!report?.expense_by_category || report.expense_by_category.length === 0) ? (
          <p className="text-sm text-gray-400 text-center py-6">Belum ada data pengeluaran bulan ini.</p>
        ) : (
          <div className="space-y-3">
            {report.expense_by_category.map((cat, idx) => {
              const pct = totalExpenseCategory > 0 ? (cat.amount / totalExpenseCategory) * 100 : 0;
              return (
                <div key={cat.category}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{cat.category}</span>
                    <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">{formatRupiah(cat.amount)}</span>
                  </div>
                  <div className="w-full h-3 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: COLORS[idx % COLORS.length] }} />
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">{pct.toFixed(1)}%</p>
                </div>
              );
            })}
            <div className="pt-2 border-t border-[var(--border-default)] flex justify-between">
              <span className="text-sm font-semibold text-gray-500">Total</span>
              <span className="text-sm font-bold text-neutral-900 dark:text-neutral-50">{formatRupiah(totalExpenseCategory)}</span>
            </div>
          </div>
        )}
      </div>

      {/* Recent Transactions */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] shadow-card overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
          <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-50">Transaksi Terbaru</h2>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={showArchived} onChange={e => { setShowArchived(e.target.checked); setTxnPage(1); }} className="w-4 h-4 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
            <span className="text-xs text-gray-500 font-medium">Tampilkan Archived</span>
          </label>
        </div>
        {transactions.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">Belum ada transaksi.</p>
        ) : (
          <div className="divide-y divide-[var(--border-subtle)]">
            {pagedTransactions.map(t => (
              <div key={t.id} className={`flex items-center justify-between px-5 py-3 hover:bg-[var(--bg-surface-hover)] transition-colors ${t.is_archived ? "opacity-40" : ""}`}>
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold ${t.type === "income" ? "bg-emerald-500" : "bg-red-400"}`}>
                    {t.type === "income" ? "+" : "−"}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{t.category || "Tanpa Kategori"}{t.is_archived ? " (Archived)" : ""}</p>
                    <p className="text-xs text-gray-400">{t.date}{t.lead_name ? ` · ${t.lead_name}` : ""}{t.notes ? ` · ${t.notes}` : ""}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-sm font-bold ${t.type === "income" ? "text-emerald-600" : "text-red-500"}`}>
                    {t.type === "income" ? "+" : "−"}{formatRupiah(t.amount)}
                  </span>
                  {t.is_archived ? (
                    <button onClick={() => restoreTransaction(t.id)} className="p-1 text-blue-400 hover:text-blue-600 transition-colors" title="Restore"><RotateCcw size={13} /></button>
                  ) : (
                    <button onClick={() => setDeleteTarget({ id: t.id, type: "transaction" })} className="p-1 text-gray-300 hover:text-red-500 transition-colors"><Trash2 size={13} /></button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        <Pagination page={txnPage} pageSize={TXN_PAGE_SIZE} total={transactions.length} onPageChange={setTxnPage} itemLabel="transaksi" />
      </div>

      {/* Wallet Modal */}
      {walletModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setWalletModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editingWallet ? "Edit Dompet" : "Tambah Dompet"}</h3>
              <button onClick={() => setWalletModal(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Dompet</label>
                <input value={walletForm.name} onChange={e => setWalletForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Contoh: BCA, Cash, Dana Operasional" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Saldo Awal (Rp)</label>
                <input type="text" value={formatRupiahInput(walletForm.balance)} onChange={e => setWalletForm(f => ({ ...f, balance: cleanRupiahInput(e.target.value) }))} className={inputCls} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Icon (opsional)</label>
                  <input value={walletForm.icon} onChange={e => setWalletForm(f => ({ ...f, icon: e.target.value }))} className={inputCls} placeholder="Mis: Bank, Tunai, GoPay" />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Warna</label>
                  <input type="color" value={walletForm.color} onChange={e => setWalletForm(f => ({ ...f, color: e.target.value }))} className="w-full h-10 rounded-xl border border-gray-200 dark:border-gray-700 cursor-pointer" />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setWalletModal(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={saveWallet} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
            </div>
          </div>
        </div>
      )}

      {/* Transaction Modal */}
      {txnModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setTxnModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Tambah Transaksi</h3>
              <button onClick={() => setTxnModal(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Tipe</label>
                <div className="flex gap-2">
                  <button onClick={() => setTxnForm(f => ({ ...f, type: "expense" }))} className={`flex-1 py-2 text-sm font-semibold rounded-xl transition-colors ${txnForm.type === "expense" ? "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400" : "bg-gray-100 dark:bg-gray-800 text-gray-500"}`}>Pengeluaran</button>
                  <button onClick={() => setTxnForm(f => ({ ...f, type: "income" }))} className={`flex-1 py-2 text-sm font-semibold rounded-xl transition-colors ${txnForm.type === "income" ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-gray-100 dark:bg-gray-800 text-gray-500"}`}>Pemasukan</button>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Dompet</label>
                <select value={txnForm.wallet_id} onChange={e => setTxnForm(f => ({ ...f, wallet_id: Number(e.target.value) }))} className={inputCls}>
                  {wallets.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Jumlah (Rp)</label>
                <input type="text" value={txnForm.amount ? formatRupiahInput(txnForm.amount) : ""} onChange={e => setTxnForm(f => ({ ...f, amount: cleanRupiahInput(e.target.value) }))} className={inputCls} placeholder="Rp 0" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Kategori</label>
                <input value={txnForm.category} onChange={e => setTxnForm(f => ({ ...f, category: e.target.value }))} className={inputCls} placeholder="Contoh: Internet, Gaji, Tools, dll" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Tanggal</label>
                <input type="date" value={txnForm.date} onChange={e => setTxnForm(f => ({ ...f, date: e.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Catatan</label>
                <input value={txnForm.notes} onChange={e => setTxnForm(f => ({ ...f, notes: e.target.value }))} className={inputCls} placeholder="Opsional" />
              </div>

              {txnForm.type === "expense" && (
                <div className="border-t border-[var(--border-default)] pt-3">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={linkClient} onChange={e => setLinkClient(e.target.checked)} className="w-4 h-4 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
                    <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">Tautkan ke Klien (Dana Talangan)</span>
                  </label>
                  {linkClient && (
                    <div className="mt-2">
                      <select value={txnForm.lead_id || ""} onChange={e => setTxnForm(f => ({ ...f, lead_id: Number(e.target.value) || null }))} className={inputCls}>
                        <option value="">— Pilih Klien —</option>
                        {clients.map(c => <option key={c.id} value={c.lead_id}>{c.business_name}</option>)}
                      </select>
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setTxnModal(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={saveTransaction} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
