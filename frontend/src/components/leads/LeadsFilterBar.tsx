"use client";
import { useState } from "react";
import { Calculator, HelpCircle, Search, Download, Plus, RefreshCw, Trash2 } from "lucide-react";

interface LeadFilters {
  status: string;
  batch: string;
  rating: number;
  score: string;
}

interface LeadsFilterBarProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  filters: LeadFilters;
  batches: string[];
  onStatusChange: (s: string) => void;
  onBatchChange: (b: string) => void;
  onScoreChange: (s: "" | "hot" | "warm" | "cold") => void;
  onRatingChange: (r: number) => void;
  onAddLead: () => void;
  onExportCSV: () => void;
  onOpenBlast: () => void;
  onRecalculate: () => void;
  onRefresh: () => void;
  recalculating: boolean;
  showArchived: boolean;
  onShowArchivedChange: (v: boolean) => void;
  onDeleteBatch: () => void;
}

const STATUSES = [
  "Scraped", "Siap Blast", "WA Terkirim", "Laporan Dibuka", "Mulai Membaca",
  "Membaca Serius", "Prospek Hangat", "Prospek Panas", "Follow Up",
  "Proposal Dikirim", "Replied", "Closed/Lost", "Closed/Client",
];
const STATUS_LABELS: Record<string, string> = {
  Scraped: "Baru Discrape",
  Contacted: "Sudah Dihubungi",
  Replied: "Sudah Membalas",
  "Closed/Lost": "Tidak Tertarik",
  "Closed/Client": "Klien Aktif",
  "Siap Blast": "Siap Blast",
  "WA Terkirim": "WA Terkirim",
  "Laporan Dibuka": "Laporan Dibuka",
  "Mulai Membaca": "Mulai Membaca",
  "Membaca Serius": "Membaca Serius",
  "Prospek Hangat": "Prospek Hangat",
  "Prospek Panas": "Prospek Panas",
  "Follow Up": "Follow Up",
  "Proposal Dikirim": "Proposal Dikirim",
};

export default function LeadsFilterBar({
  searchQuery, onSearchChange, filters, batches,
  onStatusChange, onBatchChange, onScoreChange, onRatingChange,
  onAddLead, onExportCSV, onOpenBlast, onRecalculate, onRefresh,
  recalculating, showArchived, onShowArchivedChange, onDeleteBatch,
}: LeadsFilterBarProps) {
  const [scoreHelpOpen, setScoreHelpOpen] = useState(false);

  return (
    <>
      {/* Search & Actions bar */}
      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[150px] max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input type="text" value={searchQuery} onChange={e => onSearchChange(e.target.value)}
            placeholder="Cari nama bisnis, alamat, atau nomor..."
            className="w-full pl-9 pr-3 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg text-xs bg-white dark:bg-[var(--bg-surface)] dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-amber-300/50 transition" />
        </div>
        <button onClick={onAddLead}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs font-semibold rounded-lg transition-colors">
          <Plus size={12} /> <span className="hidden sm:inline">Tambah Prospek</span><span className="sm:hidden">Tambah</span>
        </button>
        <button onClick={onExportCSV}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-neutral-800 hover:bg-gray-200 dark:hover:bg-neutral-700 text-gray-700 dark:text-neutral-200 text-xs font-semibold rounded-lg transition-colors">
          <Download size={12} /> <span className="hidden sm:inline">Export CSV</span><span className="sm:hidden">Export</span>
        </button>
      </div>

      {/* Filter bar */}
      <div className="rounded-2xl border border-gray-100 bg-white p-3 shadow-sm dark:border-gray-700 dark:bg-[var(--bg-canvas)]">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label className="space-y-1">
            <span className="block text-[11px] font-semibold uppercase tracking-wide text-gray-400">Status</span>
            <select value={filters.status} onChange={e => onStatusChange(e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-2 py-2 text-xs text-gray-700 outline-none transition focus:ring-2 focus:ring-amber-300 dark:border-gray-700 dark:bg-[var(--bg-surface)] dark:text-neutral-50">
              <option value="">Semua status</option>
              {STATUSES.map(s => <option key={s} value={s}>{STATUS_LABELS[s] || s}</option>)}
            </select>
          </label>

          <label className="space-y-1">
            <span className="block text-[11px] font-semibold uppercase tracking-wide text-gray-400">Batch</span>
            <select value={filters.batch} onChange={e => onBatchChange(e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-2 py-2 text-xs text-gray-700 outline-none transition focus:ring-2 focus:ring-amber-300 dark:border-gray-700 dark:bg-[var(--bg-surface)] dark:text-neutral-50">
              <option value="">Semua batch</option>
              {batches.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </label>

          <label className="space-y-1">
            <span className="block text-[11px] font-semibold uppercase tracking-wide text-gray-400">Rating</span>
            <select value={filters.rating} onChange={e => onRatingChange(Number(e.target.value))}
              className="w-full rounded-lg border border-gray-200 bg-white px-2 py-2 text-xs text-gray-700 outline-none transition focus:ring-2 focus:ring-amber-300 dark:border-gray-700 dark:bg-[var(--bg-surface)] dark:text-neutral-50">
              <option value={0}>Semua rating</option>
              {[5,4,3,2,1].map(v => <option key={v} value={v}>{v === 5 ? "5 bintang" : `Minimal ${v} bintang`}</option>)}
            </select>
          </label>

          <label className="space-y-1">
            <span className="block text-[11px] font-semibold uppercase tracking-wide text-gray-400">Score</span>
            <select value={filters.score} onChange={e => onScoreChange(e.target.value as "" | "hot" | "warm" | "cold")}
              className="w-full rounded-lg border border-gray-200 bg-white px-2 py-2 text-xs text-gray-700 outline-none transition focus:ring-2 focus:ring-amber-300 dark:border-gray-700 dark:bg-[var(--bg-surface)] dark:text-neutral-50">
              <option value="">Semua score</option>
              <option value="hot">Siap closing</option>
              <option value="warm">Perlu pendekatan</option>
              <option value="cold">Belum match</option>
            </select>
          </label>

          <div className="flex flex-wrap items-end gap-2 lg:justify-end">
            <button onClick={onOpenBlast}
              className="flex items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-2 text-xs font-bold text-white shadow-sm transition-all hover:bg-amber-600">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
              WA Blast
            </button>
            <button onClick={onRefresh}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-600 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-[var(--bg-surface)] dark:text-gray-300 dark:hover:bg-gray-800">
              <RefreshCw size={12} className="inline -mt-0.5 mr-1" />Refresh
            </button>
            <label className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-700">
              <input type="checkbox" checked={showArchived} onChange={e => onShowArchivedChange(e.target.checked)} className="h-3.5 w-3.5 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
              <span className="text-xs font-medium text-gray-500">Arsip</span>
            </label>
            {filters.batch && (
              <button onClick={onDeleteBatch}
                className="flex items-center gap-1.5 rounded-lg bg-red-500 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-red-600">
                <Trash2 size={12} />
                Arsipkan Batch
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-amber-100 bg-amber-50/50 p-3 dark:border-amber-900/50 dark:bg-amber-950/10">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-amber-800 dark:text-amber-300">Aksi analitik:</span>
          <button onClick={onRecalculate} disabled={recalculating}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold rounded-lg transition-colors disabled:opacity-50 whitespace-nowrap">
            <Calculator size={12} /> {recalculating ? "Menghitung..." : "Hitung Ulang Score"}
          </button>
          <button type="button" onClick={() => setScoreHelpOpen(v => !v)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-amber-200 bg-white text-xs font-semibold text-amber-800 hover:bg-amber-50 dark:border-amber-800 dark:bg-neutral-900 dark:text-amber-300">
            <HelpCircle size={12} /> Cara hitung
          </button>
        </div>
        {scoreHelpOpen && (
          <div className="mt-3 grid gap-2 text-xs text-amber-900 dark:text-amber-200 sm:grid-cols-3">
            <div className="rounded-xl bg-white/70 p-3 dark:bg-neutral-900/60"><strong>Minat layanan</strong><br/>Prospek yang punya target layanan jelas mendapat nilai dasar lebih tinggi.</div>
            <div className="rounded-xl bg-white/70 p-3 dark:bg-neutral-900/60"><strong>Kualitas Maps</strong><br/>Rating, jumlah review, website, dan kelengkapan kontak menaikkan prioritas.</div>
            <div className="rounded-xl bg-white/70 p-3 dark:bg-neutral-900/60"><strong>Sinyal follow-up</strong><br/>Klik report, balasan WA, dan status pipeline membantu menentukan mana yang perlu didekati dulu.</div>
          </div>
        )}
      </div>
    </>
  );
}
