"use client";
import { Plus, Archive, ArchiveRestore } from "lucide-react";

const COLORS = {
  primary: "bg-amber-500 hover:bg-amber-600 text-white",
  secondary: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700",
};

interface BoardHeaderProps {
  viewMode: "overview" | "board";
  currentProject: any;
  isAdmin: boolean;
  showArchivedProjects: boolean;
  setShowArchivedProjects: (v: boolean) => void;
  showArchived: boolean;
  setShowArchived: (v: boolean) => void;
  board: any;
  onNewProject: () => void;
  onNewColumn: () => void;
  onBackToOverview: () => void;
}

export default function BoardHeader({
  viewMode, currentProject, isAdmin, showArchivedProjects, setShowArchivedProjects,
  showArchived, setShowArchived, board, onNewProject, onNewColumn, onBackToOverview,
}: BoardHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        {viewMode === "board" && currentProject ? (
          <div>
            <button onClick={onBackToOverview} className="flex items-center gap-1 text-sm text-neutral-500 hover:text-amber-600 dark:hover:text-yellow-400 mb-1 transition-colors">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"/></svg>
              Semua Proyek
            </button>
            <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">{currentProject.name}</h1>
          </div>
        ) : (
          <div>
            <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Project Board</h1>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Kelola task proyek dengan kanban board</p>
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 flex-wrap justify-end">
        {viewMode === "overview" && (
          <label className="flex items-center gap-2 px-3 py-2 text-sm rounded-xl cursor-pointer select-none bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
            <input type="checkbox" checked={showArchivedProjects} onChange={e => setShowArchivedProjects(e.target.checked)} className="accent-amber-500 w-4 h-4" />
            Tampilkan arsip
          </label>
        )}
        {isAdmin && (
          <button onClick={onNewProject} className={`px-3 py-2 text-sm rounded-xl flex items-center gap-1 ${COLORS.secondary}`}>
            <Plus className="w-4 h-4" /> Proyek Baru
          </button>
        )}
        {board && (
          <>
            <button onClick={() => setShowArchived(!showArchived)} className={`px-3 py-2 text-sm rounded-xl flex items-center gap-1 ${showArchived ? COLORS.primary : COLORS.secondary}`}>
              {showArchived ? <ArchiveRestore className="w-4 h-4" /> : <Archive className="w-4 h-4" />}
              {showArchived ? "Card Aktif" : "Card Arsip"}
            </button>
            <button onClick={onNewColumn} className={`px-3 py-2 text-sm rounded-xl flex items-center gap-1 ${COLORS.primary}`}>
              <Plus className="w-4 h-4" /> Kolom
            </button>
          </>
        )}
      </div>
    </div>
  );
}