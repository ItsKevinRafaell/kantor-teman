"use client";

import { Search, Download, Plus } from "lucide-react";

interface LeadsSearchActionsProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onAddLead: () => void;
  onExportCSV: () => void;
}

export default function LeadsSearchActions({
  searchQuery,
  onSearchChange,
  onAddLead,
  onExportCSV,
}: LeadsSearchActionsProps) {
  return (
    <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
      <div className="relative flex-1 min-w-[150px] max-w-xs">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input type="text" value={searchQuery} onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Cari nama, alamat, atau nomor..."
          className="w-full pl-9 pr-3 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg text-xs bg-white dark:bg-[var(--bg-surface)] dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-amber-300/50 transition" />
      </div>
      <button onClick={onAddLead}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs font-semibold rounded-lg transition-colors">
        <Plus size={12} /> <span className="hidden sm:inline">Tambah Lead</span><span className="sm:hidden">Tambah</span>
      </button>
      <button onClick={onExportCSV}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-neutral-800 hover:bg-gray-200 dark:hover:bg-neutral-700 text-gray-700 dark:text-neutral-200 text-xs font-semibold rounded-lg transition-colors">
        <Download size={12} /> <span className="hidden sm:inline">Export CSV</span><span className="sm:hidden">Export</span>
      </button>
    </div>
  );
}