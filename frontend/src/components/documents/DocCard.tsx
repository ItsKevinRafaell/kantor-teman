"use client";

import { ExternalLink, Edit2, Trash2, Eye, FolderInput } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Document {
  id: string;
  folder_id: string | null;
  title: string;
  body: string | null;
  url: string | null;
  tags: string[];
  file_size?: number | null;
  lead_id?: number | null;
  lead_name?: string | null;
  created_at: string;
  updated_at: string | null;
}

interface DocCardProps {
  doc: Document;
  folderColor?: string;
  folderName?: string;
  clientName?: string | null;
  onView: () => void;
  onEdit: () => void;
  onDelete?: () => void;
  onMove?: () => void;
}

export function DocCard({ doc, folderColor, folderName, clientName, onView, onEdit, onDelete, onMove }: DocCardProps) {
  const dateStr = new Date(doc.updated_at || doc.created_at).toLocaleDateString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
  const isLocalFile = !!doc.url?.startsWith("/uploads/");
  const documentUrl = doc.url ? (doc.url.startsWith("/") ? `${API_BASE}${doc.url}` : doc.url) : null;
  const linkLabel = doc.url ? (isLocalFile ? "File tersimpan" : doc.url.replace(/^https?:\/\//, "")) : "";

  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", doc.id);
        e.dataTransfer.effectAllowed = "move";
      }}
      onClick={onView}
      className="group relative flex flex-col gap-2 rounded-2xl border border-amber-100 bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:border-amber-900/40 dark:bg-[var(--bg-surface)] cursor-pointer"
    >
      {folderColor && (
        <div className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl" style={{ backgroundColor: folderColor }} />
      )}

      <div className="flex items-start justify-between gap-2 mt-1">
        <h3 className="text-sm font-bold text-neutral-900 dark:text-neutral-50 leading-snug line-clamp-2 flex-1">{doc.title}</h3>
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" onClick={e => e.stopPropagation()}>
          <button type="button" onClick={onView} title="Lihat" className="p-1.5 text-neutral-400 hover:text-amber-600 rounded-lg transition-colors">
            <Eye size={13} />
          </button>
          {onMove && (
            <button type="button" onClick={onMove} title="Pindah ke folder…" className="p-1.5 text-neutral-400 hover:text-blue-500 rounded-lg transition-colors">
              <FolderInput size={13} />
            </button>
          )}
          <button type="button" onClick={onEdit} title="Edit" className="p-1.5 text-neutral-400 hover:text-amber-500 rounded-lg transition-colors">
            <Edit2 size={13} />
          </button>
          {onDelete && (
            <button type="button" onClick={onDelete} title="Hapus" className="p-1.5 text-neutral-400 hover:text-red-500 rounded-lg transition-colors">
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      {documentUrl && (
        <a href={documentUrl} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 text-xs font-medium hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors w-fit max-w-full">
          <ExternalLink size={10} />
          <span className="truncate max-w-[180px]">{linkLabel}</span>
        </a>
      )}

      {doc.body && (
        <p className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2 leading-relaxed">
          {doc.body.slice(0, 120)}{doc.body.length > 120 ? "…" : ""}
        </p>
      )}

      {(doc.tags.length > 0 || clientName || doc.lead_name) && (
        <div className="flex flex-wrap gap-1">
          {(clientName || doc.lead_name) && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300">
              {clientName || doc.lead_name}
            </span>
          )}
          {doc.tags.map(tag => (
            <span key={tag} className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between mt-auto pt-1 border-t border-gray-100 dark:border-gray-800">
        {folderName ? (
          <span className="flex items-center gap-1 text-[10px] text-neutral-400">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: folderColor }} />
            {folderName}
          </span>
        ) : (
          <span className="text-[10px] text-neutral-300 dark:text-neutral-600">Tanpa folder</span>
        )}
        <span className="text-[10px] text-neutral-400">{dateStr}</span>
      </div>
    </div>
  );
}
