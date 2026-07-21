"use client";

import Link from "next/link";
import { Archive, ArchiveRestore, Trash2, User } from "lucide-react";
import type { BoardOverview, Project } from "./types";
import { useAuth } from "../../contexts/AuthContext";
import { COLUMN_COLORS } from "./types";

interface Props {
  item: BoardOverview;
  projects: Project[];
  onSelectProject: (projectId: string) => void;
  onArchiveProject: (projectId: string, isArchived: boolean) => void;
  onDeleteProject: (projectId: string, projectName: string) => void;
  onShowConfirm: (title: string, message: string, onConfirm: () => void) => void;
  onEditProject: (project: Project) => void;
}

export function BoardOverviewCard({ item, projects, onSelectProject, onArchiveProject, onDeleteProject, onShowConfirm, onEditProject }: Props) {
  const { isAdmin } = useAuth();
  const itemColor = COLUMN_COLORS[item.color || "gray"] || COLUMN_COLORS.gray;

  return (
    <div className={`rounded-xl border p-4 transition-all hover:shadow-md ${itemColor.bg} ${itemColor.border} ${item.is_archived ? "opacity-60" : ""}`}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3
          className="font-semibold text-neutral-800 dark:text-neutral-200 leading-tight cursor-pointer flex-1"
          onClick={() => !item.is_archived && onSelectProject(item.project_id)}
        >
          {item.project_name}
        </h3>
        {isAdmin && (
          <div className="flex gap-1 shrink-0" onClick={e => e.stopPropagation()}>
            {!item.is_archived && (
              <button
                title="Edit proyek"
                onClick={() => {
                  const p = projects.find(x => x.id === item.project_id);
                  if (p) onEditProject(p);
                }}
                className="p-1.5 text-neutral-400 hover:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-xl transition-colors"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
            )}
            <button
              title={item.is_archived ? "Pulihkan proyek" : "Arsipkan proyek"}
              onClick={() => onArchiveProject(item.project_id, !item.is_archived)}
              className="p-1.5 text-neutral-400 hover:text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-xl transition-colors"
            >
              {item.is_archived ? <ArchiveRestore className="w-3.5 h-3.5" /> : <Archive className="w-3.5 h-3.5" />}
            </button>
            <button
              title="Hapus proyek"
              onClick={() => onShowConfirm("Hapus Proyek", `Proyek "${item.project_name}" beserta semua board, kolom, dan card-nya akan dihapus permanen.`, () => onDeleteProject(item.project_id, item.project_name))}
              className="p-1.5 text-neutral-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {item.client_name && (
        <p className="text-xs font-medium text-neutral-600 dark:text-neutral-300 mb-2 flex items-center gap-1">
          <User className="w-3 h-3" /> {item.client_name}
        </p>
      )}

      <div className="flex items-center gap-3 text-sm text-neutral-500 mb-2">
        <span>{item.cards_count} card</span>
        <span>{item.columns_count} kolom</span>
      </div>

      {((item.overdue_cards?.length || 0) > 0 || (item.due_soon_cards?.length || 0) > 0) && (
        <div className="flex gap-1 flex-wrap mb-2">
          {(item.overdue_cards?.length || 0) > 0 && (
            <span className="text-xs bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400 px-2 py-0.5 rounded-full">{item.overdue_cards?.length} overdue</span>
          )}
          {(item.due_soon_cards?.length || 0) > 0 && (
            <span className="text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 px-2 py-0.5 rounded-full">{item.due_soon_cards?.length} due soon</span>
          )}
        </div>
      )}

      <div className="mt-2 flex flex-wrap gap-2" onClick={e => e.stopPropagation()}>
        <button
          type="button"
          onClick={() => !item.is_archived && onSelectProject(item.project_id)}
          className="rounded-lg bg-white/80 px-2.5 py-1 text-[11px] font-semibold text-amber-800 ring-1 ring-amber-200 hover:bg-amber-50 dark:bg-neutral-900/60 dark:text-amber-200 dark:ring-amber-900/50"
        >
          Buka Board
        </button>
        <Link
          href={`/workspace/${item.project_id}`}
          className="rounded-lg bg-white/80 px-2.5 py-1 text-[11px] font-semibold text-neutral-700 ring-1 ring-neutral-200 hover:bg-neutral-50 dark:bg-neutral-900/60 dark:text-neutral-200 dark:ring-neutral-700"
        >
          Sheet Workspace
        </Link>
      </div>
    </div>
  );
}