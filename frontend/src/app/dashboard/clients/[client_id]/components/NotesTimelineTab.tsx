"use client";
import { useState, useEffect } from "react";
import { apiFetch } from "../../../../../lib/api";
import Toast from "../../../../../components/Toast";
import Modal from "../../../../../components/Modal";

interface NoteData {
  id: string;
  category: string;
  content: string;
  actor: string;
  timestamp: string;
}

const CATEGORY_BADGE: Record<string, string> = {
  BISNIS: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  TEKNIS: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  PENTING: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

export default function NotesTimelineTab({ leadId, initialNotes }: { leadId: number | null; initialNotes: NoteData[] }) {
  const [notes, setNotes] = useState<NoteData[]>(initialNotes);
  const [filter, setFilter] = useState<"ALL" | "BISNIS" | "TEKNIS" | "PENTING">("ALL");
  const [form, setForm] = useState({ category: "BISNIS", content: "" });
  const [submitting, setSubmitting] = useState(false);
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
  const [noteToast, setNoteToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  useEffect(() => { setNotes(initialNotes); }, [initialNotes]);

  async function submitNote() {
    if (!leadId || !form.content.trim()) return;
    setSubmitting(true);
    try {
      const res = await apiFetch("/api/clients/notes", {
        method: "POST",
        body: JSON.stringify({ lead_id: leadId, category: form.category, content: form.content }),
      });
      if (res.ok) {
        const newNote = await res.json();
        setNotes(prev => [newNote, ...prev]);
        setForm(f => ({ ...f, content: "" }));
      }
    } finally { setSubmitting(false); }
  }

  async function deleteNote(noteId: string) {
    const res = await apiFetch(`/api/client-notes/${noteId}`, { method: "DELETE" });
    if (res.ok) {
      setNoteToast({ message: "Catatan dihapus.", type: "success" });
      setNotes(prev => prev.filter(n => n.id !== noteId));
    } else {
      setNoteToast({ message: "Gagal hapus catatan.", type: "error" });
    }
    setDeleteNoteId(null);
  }

  const filtered = filter === "ALL" ? notes : notes.filter(n => n.category === filter);

  return (
    <div>
      <Toast message={noteToast?.message ?? null} type={noteToast?.type} onClose={() => setNoteToast(null)} />
      <Modal
        open={!!deleteNoteId}
        title="Hapus Catatan?"
        message="Catatan yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteNoteId && deleteNote(deleteNoteId)}
        onCancel={() => setDeleteNoteId(null)}
      />
      <div className="px-5 py-4 border-b border-[var(--border-default)]">
        <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Catatan & Timeline</h2>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">Riwayat catatan kronologis untuk klien ini.</p>
      </div>

      <div className="px-5 py-4 border-b border-[var(--border-subtle)] bg-neutral-50/50 dark:bg-neutral-800/30">
        <div className="flex gap-3">
          <div className="flex-1">
            <textarea
              value={form.content}
              onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submitNote(); } }}
              rows={2}
              placeholder="Tulis catatan baru... (Enter untuk kirim, Shift+Enter untuk baris baru)"
              className="input-field resize-none"
            />
          </div>
          <div className="flex flex-col gap-2 shrink-0">
            <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
              className="px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-xl text-xs bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 focus:outline-none focus:ring-2 focus:ring-amber-300">
              <option value="BISNIS">Bisnis</option>
              <option value="TEKNIS">Teknis</option>
              <option value="PENTING">Penting</option>
            </select>
            <button onClick={submitNote} disabled={submitting || !leadId || !form.content.trim()} className="btn-primary text-xs px-3 py-2 disabled:opacity-50">
              {!leadId ? "Lead belum terkait" : submitting ? "..." : "Kirim"}
            </button>
          </div>
        </div>
      </div>

      {!leadId && (
        <div className="px-5 py-3 border-b border-[var(--border-subtle)] text-xs text-amber-600 dark:text-amber-400">
          Kontak ini belum memiliki relasi lead, jadi catatan belum bisa ditambahkan.
        </div>
      )}

      <div className="px-5 py-3 border-b border-[var(--border-subtle)] flex items-center gap-2">
        {(["ALL", "BISNIS", "TEKNIS", "PENTING"] as const).map(cat => (
          <button key={cat} onClick={() => setFilter(cat)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${filter === cat ? "bg-brand-yellow/10 text-brand-yellow" : "text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}>
            {cat === "ALL" ? "Semua" : cat.charAt(0) + cat.slice(1).toLowerCase()}
          </button>
        ))}
        <span className="ml-auto text-[11px] text-neutral-400">{filtered.length} catatan</span>
      </div>

      <div className="divide-y divide-[var(--border-subtle)] max-h-[400px] overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="text-center py-10 text-neutral-400 text-sm">Belum ada catatan.</div>
        ) : (
          filtered.map(note => (
            <div key={note.id} className="px-5 py-4 hover:bg-[var(--bg-surface-hover)] transition-colors group">
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <div className={`w-2.5 h-2.5 rounded-full ${note.category === "BISNIS" ? "bg-emerald-500" : note.category === "TEKNIS" ? "bg-blue-500" : "bg-red-500"}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${CATEGORY_BADGE[note.category] || CATEGORY_BADGE.BISNIS}`}>
                      {note.category}
                    </span>
                    <span className="text-[11px] text-neutral-400">{note.actor}</span>
                  </div>
                  <p className="text-sm text-neutral-800 dark:text-neutral-200 leading-relaxed whitespace-pre-wrap">{note.content}</p>
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <span className="text-[10px] text-neutral-400">
                    {new Date(note.timestamp).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}
                  </span>
                  <span className="text-[10px] text-neutral-400">
                    {new Date(note.timestamp).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}
                  </span>
                  <button onClick={() => setDeleteNoteId(note.id)} className="text-[10px] text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity mt-1">
                    Hapus
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
