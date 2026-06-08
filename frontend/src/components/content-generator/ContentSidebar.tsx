"use client";

import { useState, useRef, useEffect } from "react";
import { apiFetch } from "../../lib/api";
import type { ContentSession, ContentGeneration, Tool } from "./types";
import { TOOL_COLORS, formatDate } from "./types";

const TOOL_LABELS: Record<Tool, string> = {
  seo_article: "SEO Article Generator",
  image: "Image Generator",
  caption: "Caption Sosmed",
};

interface Props {
  sessions: ContentSession[];
  sessionsLoading: boolean;
  selectedSession: ContentSession | null;
  setSelectedSession: (s: ContentSession | null) => void;
  generations: ContentGeneration[];
  generationsLoading: boolean;
  sharedContext: string[];
  toggleContext: (id: string) => void;
  onClearContext: () => void;
  onDeleteGeneration: (id: string) => Promise<void>;
  onCreateSession: (data: { name: string; description?: string }) => Promise<void>;
  onDeleteSession: (id: string) => Promise<void>;
  onRenameSession: (id: string, name: string) => Promise<void>;
  onManageProviders: () => void;
  activeTool: Tool;
  onToolChange: (tool: Tool) => void;
}

function getGenerationPreview(g: ContentGeneration): string {
  const out = g.output_data as Record<string, unknown> | null;
  if (!out) return g.error_msg || "—";
  if (g.tool_type === "seo_article") return `${out.title || ""} — ${String(out.meta_description || "").slice(0, 80)}`;
  if (g.tool_type === "image") return String((g.input_data as Record<string, unknown>).prompt || "").slice(0, 100) || "gambar";
  if (g.tool_type === "caption") return String(out.caption || "").slice(0, 100) || "caption";
  return "—";
}

export default function ContentSidebar({
  sessions, sessionsLoading, selectedSession, setSelectedSession,
  generations, generationsLoading, sharedContext, toggleContext,
  onClearContext,
  onDeleteGeneration, onCreateSession, onDeleteSession, onRenameSession,
  onManageProviders, activeTool, onToolChange,
}: Props) {
  const [showNewSessionModal, setShowNewSessionModal] = useState(false);
  const [sessionForm, setSessionForm] = useState({ name: "", description: "" });
  const [renamingSession, setRenamingSession] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  async function commitCreate() {
    if (!sessionForm.name.trim()) return;
    await onCreateSession(sessionForm);
    setShowNewSessionModal(false);
    setSessionForm({ name: "", description: "" });
  }

  async function commitRename(s: ContentSession) {
    if (!renameValue.trim()) { setRenamingSession(null); return; }
    await onRenameSession(s.id, renameValue.trim());
    setRenamingSession(null);
  }

  return (
    <aside className="w-full md:w-52 shrink-0 flex flex-col gap-3 overflow-x-auto md:overflow-y-auto">
      {/* Tools */}
      <div>
        <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-2">Tools</p>
        {(["seo_article", "image", "caption"] as Tool[]).map(t => (
          <button key={t} onClick={() => onToolChange(t)}
            className={`w-full text-left px-3 py-2 rounded-xl text-sm font-medium mb-1 transition-all
              ${activeTool === t ? "bg-neutral-500 text-white shadow-sm" : "text-neutral-500 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-neutral-800 dark:hover:text-neutral-200"}`}>
            {TOOL_LABELS[t]}
          </button>
        ))}
      </div>

      {/* Sessions */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest">Sesi</p>
          <button onClick={() => setShowNewSessionModal(true)} className="text-xs text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 font-medium">+ Baru</button>
        </div>
        <button onClick={() => setSelectedSession(null)}
          className={`w-full text-left px-3 py-2 rounded-xl text-sm mb-1 transition-all
            ${!selectedSession ? "bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 font-medium" : "text-neutral-500 hover:bg-gray-100 dark:hover:bg-gray-800"}`}>
          Semua
        </button>
        {sessions.map(s => (
          <div key={s.id} className={`group flex items-center gap-1 px-3 py-2 rounded-xl text-sm mb-1 transition-all
            ${selectedSession?.id === s.id ? "bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 font-medium" : "text-neutral-500 hover:bg-gray-100 dark:hover:bg-gray-800"}`}>
            {renamingSession === s.id ? (
              <input
                value={renameValue}
                onChange={e => setRenameValue(e.target.value)}
                onBlur={() => commitRename(s)}
                onKeyDown={e => { if (e.key === "Enter") commitRename(s); if (e.key === "Escape") setRenamingSession(null); }}
                autoFocus
                className="flex-1 bg-transparent outline-none border-b border-neutral-400 text-sm min-w-0"
                onClick={e => e.stopPropagation()}
              />
            ) : (
              <span className="flex-1 truncate cursor-pointer" onClick={() => setSelectedSession(s)}>{s.name}</span>
            )}
            {renamingSession !== s.id && (
              <>
                <button onClick={e => { e.stopPropagation(); setRenameValue(s.name); setRenamingSession(s.id); }}
                  className="opacity-0 group-hover:opacity-100 text-neutral-400 hover:text-neutral-600 text-xs shrink-0" title="Rename">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                </button>
                <button onClick={e => { e.stopPropagation(); onDeleteSession(s.id); }}
                  className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 text-xs shrink-0" title="Hapus">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                </button>
              </>
            )}
          </div>
        ))}
      </div>

      {/* Context indicator */}
      {sharedContext.length > 0 && (
        <div className="bg-neutral-50 dark:bg-neutral-900/20 border border-neutral-200 dark:border-neutral-800 rounded-xl p-3">
          <p className="text-xs font-semibold text-neutral-700 dark:text-neutral-400 mb-1">{sharedContext.length} konteks aktif</p>
          <button onClick={onClearContext} className="text-xs text-neutral-500 hover:text-neutral-700">Hapus semua</button>
        </div>
      )}

      {/* Image provider link */}
      {activeTool === "image" && (
        <button onClick={onManageProviders}
          className="text-xs text-neutral-500 hover:text-neutral-600 px-3 py-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-left">
          Kelola Image Provider
        </button>
      )}

      {/* New Session Modal */}
      {showNewSessionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setShowNewSessionModal(false)}>
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
          <div className="relative bg-white dark:bg-[var(--bg-canvas)] rounded-2xl shadow-2xl max-w-sm w-full p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Sederet Baru</h3>
            <input type="text" value={sessionForm.name} onChange={e => setSessionForm(p => ({ ...p, name: e.target.value }))}
              placeholder="Nama sesi"
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none" />
            <input type="text" value={sessionForm.description} onChange={e => setSessionForm(p => ({ ...p, description: e.target.value }))}
              placeholder="Deskripsi (opsional)"
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none" />
            <div className="flex gap-2">
              <button onClick={() => setShowNewSessionModal(false)} className="flex-1 py-2 text-sm rounded-lg bg-gray-100 dark:bg-gray-800 text-neutral-600">Batal</button>
              <button onClick={commitCreate} disabled={!sessionForm.name.trim()} className="flex-1 py-2 text-sm rounded-lg bg-neutral-500 text-white disabled:opacity-50">Buat</button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
