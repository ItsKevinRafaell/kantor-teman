"use client";

import { useState, useEffect, useCallback } from "react";
import { useApi } from "../../lib/swr";
import type { ContentGeneration, Tool } from "./types";
import { TOOL_COLORS, formatDate, markdownToHtml } from "./types";

interface Props {
  generations: ContentGeneration[];
  generationsLoading: boolean;
  sharedContext: string[];
  toggleContext: (id: string) => void;
  onDeleteGeneration: (id: string) => Promise<void>;
  onSetViewResult: (r: { title: string; meta_description: string; body: string; focus_keyword: string; secondary_keywords: string[]; id?: string } | null) => void;
}

function getGenerationPreview(g: ContentGeneration): string {
  const out = g.output_data as Record<string, unknown> | null;
  if (!out) return g.error_msg || "—";
  if (g.tool_type === "seo_article") return `${out.title || ""} — ${String(out.meta_description || "").slice(0, 80)}`;
  if (g.tool_type === "image") return String((g.input_data as Record<string, unknown>).prompt || "").slice(0, 100) || "gambar";
  if (g.tool_type === "caption") return String(out.caption || "").slice(0, 100) || "caption";
  return "—";
}

export default function ContentHistory({
  generations, generationsLoading, sharedContext, toggleContext,
  onDeleteGeneration, onSetViewResult,
}: Props) {
  const [searchQuery, setSearchQuery] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<ContentGeneration | null>(null);

  return (
    <div className="bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
      <div className="flex items-center gap-3 mb-3">
        <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 shrink-0">History</h3>
        <div className="flex-1 relative">
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Cari keyword, judul, prompt..."
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-gray-100 dark:bg-gray-800 border-0 rounded-lg focus:ring-2 focus:ring-yellow-400 outline-none"
          />
          <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-400" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          {searchQuery && (
            <button onClick={() => setSearchQuery("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          )}
        </div>
        <span className="text-xs text-neutral-400 shrink-0">{generations.length}</span>
      </div>

      {generationsLoading ? (
        <p className="text-xs text-neutral-400 text-center py-6">Memuat histori...</p>
      ) : generations.length === 0 ? (
        <p className="text-xs text-neutral-400 text-center py-6">
          {searchQuery ? `Tidak ada hasil untuk "${searchQuery}"` : "Belum ada konten yang dibuat."}
        </p>
      ) : (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {generations
            .filter(g => !searchQuery || getGenerationPreview(g).toLowerCase().includes(searchQuery.toLowerCase()))
            .map(g => {
              const isCtx = sharedContext.includes(g.id);
              return (
                <div key={g.id} className={`flex items-start gap-3 p-3 rounded-xl transition-colors
                  ${isCtx ? "bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800" : "bg-gray-50 dark:bg-gray-800/50"}`}>
                  <span className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full ${TOOL_COLORS[g.tool_type as Tool] || "bg-gray-100 text-gray-600"}`}>
                    {g.tool_type === "seo_article" ? "Article" : g.tool_type === "image" ? "Image" : "Caption"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-neutral-600 dark:text-neutral-400 truncate">{getGenerationPreview(g)}</p>
                    <p className="text-[10px] text-neutral-400 mt-0.5">{formatDate(g.created_at)}</p>
                  </div>
                  {g.tool_type === "seo_article" && (
                    <button onClick={() => {
                      const out = g.output_data as Record<string, unknown> | null;
                      if (out) {
                        onSetViewResult({
                          title: String(out.title || ""),
                          meta_description: String(out.meta_description || ""),
                          body: String(out.body || ""),
                          focus_keyword: String(out.focus_keyword || ""),
                          secondary_keywords: (out.secondary_keywords as string[]) || [],
                          id: g.id,
                        });
                        window.scrollTo({ top: 0, behavior: "smooth" });
                      }
                    }}
                      className="shrink-0 text-xs px-2 py-1 rounded bg-gray-200 dark:bg-gray-700 text-neutral-500 hover:bg-blue-100 hover:text-blue-700 transition-all">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/></svg>
                    </button>
                  )}
                  <button onClick={() => toggleContext(g.id)}
                    className={`shrink-0 text-xs px-2 py-1 rounded font-medium transition-all
                      ${isCtx ? "bg-amber-200 dark:bg-amber-800 text-amber-800 dark:text-amber-200" : "bg-gray-200 dark:bg-gray-700 text-neutral-500 hover:bg-amber-100 hover:text-amber-700"}`}>
                    {isCtx ? "−" : "+"}
                  </button>
                  <button onClick={() => setDeleteTarget(g)}
                    className="shrink-0 text-xs px-2 py-1 rounded bg-gray-200 dark:bg-gray-700 text-neutral-400 hover:bg-red-100 hover:text-red-600 transition-all">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                  </button>
                </div>
              );
            })}
        </div>
      )}

      {/* Delete confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setDeleteTarget(null)}>
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
          <div className="relative bg-white dark:bg-[var(--bg-canvas)] rounded-2xl shadow-2xl max-w-sm w-full p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Hapus Artikel</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">Yakin hapus artikel ini?</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setDeleteTarget(null)} className="px-4 py-2 text-sm rounded-lg bg-gray-100 dark:bg-gray-800 text-neutral-600">Batal</button>
              <button onClick={async () => { await onDeleteGeneration(deleteTarget.id); setDeleteTarget(null); }}
                className="px-4 py-2 text-sm rounded-lg bg-red-500 hover:bg-red-600 text-white">Hapus</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
