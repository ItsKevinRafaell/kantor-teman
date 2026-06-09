"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "../../lib/api";
import { downloadBlob } from "../../utils/download";
import Toast from "../../components/Toast";
import { Download, RotateCcw, AlertTriangle, Database, Lock } from "lucide-react";

type ActionKey = "seed" | "soft" | "nuclear";

const ACTION_CONFIG: Record<ActionKey, {
  title: string;
  endpoint: string;
  description: string;
  confirmPhrase: string;
  danger: boolean;
}> = {
  seed: {
    title: "Re-seed Demo Data",
    endpoint: "/api/admin/data/seed-demo",
    description: "Isi ulang categories, products, templates, wallets, dan sample clients. Aman dijalankan beberapa kali.",
    confirmPhrase: "SEED",
    danger: false,
  },
  soft: {
    title: "Soft Reset",
    endpoint: "/api/admin/data/reset-soft",
    description: "Hapus data dev/test (leads non-client, boards, content, documents, blast). PERTAHANKAN: users, settings, clients (Closed/Client), products, wallets, transactions.",
    confirmPhrase: "RESET SOFT",
    danger: true,
  },
  nuclear: {
    title: "Nuclear Reset",
    endpoint: "/api/admin/data/reset-nuclear",
    description: "Hapus SEMUA data termasuk clients, transactions, products. Hanya pertahankan users, system settings, AI config, brand kit. Auto-jalankan basic seed setelah reset.",
    confirmPhrase: "RESET NUCLEAR",
    danger: true,
  },
};

export default function DataTab() {
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [openAction, setOpenAction] = useState<ActionKey | null>(null);
  const [backupConfirmOpen, setBackupConfirmOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [phrase, setPhrase] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [isProduction, setIsProduction] = useState(false);

  useEffect(() => {
    apiFetch("/api/settings/production-mode")
      .then(r => r.json())
      .then(d => setIsProduction(d.is_production ?? false))
      .catch(() => {});
  }, []);

  function showToast(message: string, type: "success" | "error" = "success") {
    setToast({ message, type });
  }

  function closeModal() {
    setOpenAction(null);
    setPassword("");
    setPhrase("");
    setSubmitting(false);
  }

  async function runAction() {
    if (!openAction) return;
    const config = ACTION_CONFIG[openAction];
    if (phrase.trim() !== config.confirmPhrase) {
      showToast(`Ketik "${config.confirmPhrase}" persis untuk konfirmasi.`, "error");
      return;
    }
    if (!password) {
      showToast("Password admin wajib diisi.", "error");
      return;
    }
    setSubmitting(true);
    try {
      const res = await apiFetch(config.endpoint, {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail ?? "Gagal");
      }
      showToast(data.message ?? "Berhasil");
      closeModal();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal", "error");
      setSubmitting(false);
    }
  }

  async function downloadBackup() {
    setDownloading(true);
    try {
      const res = await apiFetch("/api/admin/data/backup");
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Backup gagal");
      }
      const blob = await res.blob();
      const disposition = res.headers.get("Content-Disposition") ?? "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : `kantorteman-backup-${Date.now()}.zip`;
      downloadBlob(blob, filename);
      showToast("Backup terunduh.");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Backup gagal", "error");
    } finally {
      setDownloading(false);
    }
  }

  const currentConfig = openAction ? ACTION_CONFIG[openAction] : null;

  return (
    <div className="bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-[var(--border-default)] shadow-sm p-6 space-y-6 max-w-2xl">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />

      {isProduction && (
        <div className="flex items-start gap-3 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl">
          <Lock size={16} className="text-amber-600 mt-0.5 shrink-0" />
          <div className="text-sm text-amber-800 dark:text-amber-300">
            <strong>Mode Production Aktif.</strong> Aksi Re-seed, Soft Reset, dan Nuclear Reset{' '}
            <strong>dinonaktifkan</strong> untuk melindungi data production. Hubungi admin server
            jika Anda butuh akses ke environment dev/staging.
          </div>
        </div>
      )}

      {/* Backup */}
      <section>
        <div className="flex items-center gap-2 mb-2">
          <Database size={18} className="text-emerald-600" />
          <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Backup Data</h3>
        </div>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-3">
          Download dump SQL database + folder <code className="font-mono">uploads/</code> sebagai .zip. Simpan rutin sebelum reset atau update besar.
        </p>
        <button
          onClick={() => setBackupConfirmOpen(true)}
          disabled={downloading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl disabled:opacity-50 transition-colors shadow-sm"
        >
          <Download size={16} />
          Download Backup (.zip)
        </button>
      </section>

      {/* Seed Demo */}
      <section className="border-t border-[var(--border-default)] pt-5">
        <div className="flex items-center gap-2 mb-2">
          <RotateCcw size={18} className="text-amber-600" />
          <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Re-seed Demo Data</h3>
        </div>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-3">
          {ACTION_CONFIG.seed.description}
        </p>
        <button
          onClick={() => setOpenAction("seed")}
          disabled={isProduction}
          className="inline-flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold rounded-xl transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RotateCcw size={16} />
          Re-seed Demo
        </button>
      </section>

      {/* Soft Reset */}
      <section className="border-t border-[var(--border-default)] pt-5">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle size={18} className="text-orange-600" />
          <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Soft Reset</h3>
        </div>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-3">
          {ACTION_CONFIG.soft.description}
        </p>
        <button
          onClick={() => setOpenAction("soft")}
          disabled={isProduction}
          className="inline-flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-xl transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <AlertTriangle size={16} />
          Soft Reset
        </button>
      </section>

      {/* Nuclear Reset */}
      <section className="border-t border-[var(--border-default)] pt-5">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle size={18} className="text-red-600" />
          <h3 className="text-sm font-bold text-red-600 dark:text-red-400">Nuclear Reset</h3>
        </div>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-3">
          {ACTION_CONFIG.nuclear.description}
        </p>
        <p className="text-xs text-red-600 dark:text-red-400 mb-3 font-semibold">
          ⚠ Tidak bisa di-undo. Pastikan sudah download backup.
        </p>
        <button
          onClick={() => setOpenAction("nuclear")}
          disabled={isProduction}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-xl transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <AlertTriangle size={16} />
          Nuclear Reset
        </button>
      </section>

      {/* Backup Confirmation Modal */}
      {backupConfirmOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" onClick={() => setBackupConfirmOpen(false)}>
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
          <div className="relative bg-white dark:bg-[var(--bg-canvas)] rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2">
              <Database size={20} className="text-emerald-600" />
              <h3 className="font-bold text-neutral-900 dark:text-neutral-50">Download Backup</h3>
            </div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Backup akan berisi <strong>dump database SQL</strong> dan folder <code className="font-mono text-xs">uploads/</code> dalam format .zip.
              File cukup besar (bisa puluhan MB) dan proses preparation di server mungkin butuh beberapa detik.
            </p>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              Simpan backup secara rutin, terutama sebelum menjalankan <strong>Soft Reset</strong> atau <strong>Nuclear Reset</strong> yang bersifat irreversible.
            </p>
            <div className="flex gap-2 justify-end pt-2">
              <button
                onClick={() => setBackupConfirmOpen(false)}
                className="px-4 py-2 text-sm rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
                Batal
              </button>
              <button
                onClick={() => { setBackupConfirmOpen(false); downloadBackup(); }}
                className="px-4 py-2 text-sm rounded-xl font-semibold bg-emerald-600 hover:bg-emerald-700 text-white transition-colors">
                Download Sekarang
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {currentConfig && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" onClick={closeModal}>
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
          <div className="relative bg-white dark:bg-[var(--bg-canvas)] rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-2">
              {currentConfig.danger ? (
                <AlertTriangle className="text-red-600" size={20} />
              ) : (
                <RotateCcw className="text-amber-600" size={20} />
              )}
              <h3 className="font-bold text-neutral-900 dark:text-neutral-50">{currentConfig.title}</h3>
            </div>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">{currentConfig.description}</p>

            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
                Ketik <span className="font-mono text-red-600">{currentConfig.confirmPhrase}</span> untuk konfirmasi
              </label>
              <input
                value={phrase}
                onChange={(e) => setPhrase(e.target.value)}
                placeholder={currentConfig.confirmPhrase}
                className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 font-mono transition"
                autoFocus
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">
                Password admin
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password login admin"
                className="w-full px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition"
              />
            </div>

            <div className="flex gap-2 justify-end pt-2">
              <button
                onClick={closeModal}
                disabled={submitting}
                className="px-4 py-2 text-sm rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
              >
                Batal
              </button>
              <button
                onClick={runAction}
                disabled={submitting || phrase.trim() !== currentConfig.confirmPhrase || !password}
                className={`px-4 py-2 text-sm rounded-xl font-semibold text-white transition-colors disabled:opacity-50 ${
                  currentConfig.danger ? "bg-red-600 hover:bg-red-700" : "bg-amber-500 hover:bg-amber-600"
                }`}
              >
                {submitting ? "Memproses..." : `Konfirmasi ${currentConfig.title}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
