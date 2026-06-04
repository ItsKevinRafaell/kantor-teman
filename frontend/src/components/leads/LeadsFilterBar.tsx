"use client";

import { RefreshCw } from "lucide-react";

interface LeadFilters {
  status: string;
  batch: string;
  rating: number;
  score: string;
}

interface LeadsFilterBarProps {
  filters: LeadFilters;
  batches: string[];
  onStatusChange: (status: string) => void;
  onBatchChange: (batch: string) => void;
  onRatingChange: (rating: number) => void;
  onScoreChange: (score: string) => void;
  onRecalculate: () => void;
  recalculating: boolean;
  onRefresh: () => void;
  showArchived: boolean;
  onShowArchivedChange: (show: boolean) => void;
  onDeleteBatch: () => void;
}

const STATUSES = ["Scraped", "Contacted", "Replied", "Closed/Lost", "Closed/Client"];

export default function LeadsFilterBar({
  filters,
  batches,
  onStatusChange,
  onBatchChange,
  onRatingChange,
  onScoreChange,
  onRecalculate,
  recalculating,
  onRefresh,
  showArchived,
  onShowArchivedChange,
  onDeleteBatch,
}: LeadsFilterBarProps) {
  return (
    <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Status:</span>
      <button onClick={() => onStatusChange("")}
        className={`px-2.5 sm:px-3 py-1 rounded-full text-xs font-semibold transition-colors ${filters.status === "" ? "bg-amber-500 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"}`}>
        Semua
      </button>
      {STATUSES.map((s) => (
        <button key={s} onClick={() => onStatusChange(s)}
          className={`px-2.5 sm:px-3 py-1 rounded-full text-xs font-semibold transition-colors ${filters.status === s ? "bg-amber-500 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"}`}>
          {s}
        </button>
      ))}

      <div className="flex items-center gap-2 w-full sm:w-auto sm:ml-2">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Batch:</span>
        <select value={filters.batch} onChange={(e) => onBatchChange(e.target.value)}
          className="text-xs border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 bg-white dark:bg-[var(--bg-surface)] text-gray-700 dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition max-w-[200px] flex-1 sm:flex-none">
          <option value="">Semua Batch</option>
          {batches.map((b) => <option key={b} value={b}>{b}</option>)}
        </select>
        {filters.batch && (
          <button onClick={onDeleteBatch}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white text-xs font-semibold rounded-lg transition-colors whitespace-nowrap">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14H6L5 6" /><path d="M10 11v6" /><path d="M14 11v6" /><path d="M9 6V4h6v2" />
            </svg>
            Arsipkan Batch
          </button>
        )}
      </div>

      {/* Blast button */}
      <button onClick={() => {/* trigger blast from parent */}}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-lg transition-all shadow-sm whitespace-nowrap">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
        WA Blast
      </button>

      <div className="flex items-center gap-2 w-full sm:w-auto">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Rating:</span>
        <select value={filters.rating} onChange={(e) => onRatingChange(Number(e.target.value))}
          className="text-xs border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 bg-white dark:bg-[var(--bg-surface)] text-gray-700 dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition">
          <option value={0}>Semua</option>
          <option value={5}>5 Bintang</option>
          <option value={4}>Min. 4 Bintang</option>
          <option value={3}>Min. 3 Bintang</option>
          <option value={2}>Min. 2 Bintang</option>
          <option value={1}>Min. 1 Bintang</option>
        </select>
      </div>

      <div className="flex items-center gap-2 w-full sm:w-auto">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Score:</span>
        {([["", "Semua"], ["hot", "Siap Closing"], ["warm", "Perlu Pendekatan"], ["cold", "Belum Match"]] as const).map(([val, label]) => (
          <button key={val} onClick={() => onScoreChange(val)}
            className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors ${filters.score === val ? "bg-amber-500 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"}`}>
            {label}
          </button>
        ))}
      </div>

      <button onClick={onRecalculate} disabled={recalculating}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-neutral-800 hover:bg-gray-200 dark:hover:bg-neutral-700 text-gray-700 dark:text-neutral-200 text-xs font-semibold rounded-lg transition-colors disabled:opacity-50 whitespace-nowrap">
        {recalculating ? "..." : "Recalculate Scores"}
      </button>

      <button onClick={onRefresh}
        className="sm:ml-auto px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-[var(--bg-surface)] border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
        <RefreshCw size={12} className="inline -mt-0.5 mr-1" />Refresh
      </button>

      <label className="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" checked={showArchived} onChange={(e) => onShowArchivedChange(e.target.checked)} className="w-3.5 h-3.5 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
        <span className="text-xs text-gray-500 font-medium">Archived</span>
      </label>
    </div>
  );
}