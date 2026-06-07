"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "../../lib/api";
import type { Contact, ClientNote } from "../../types";

interface NotesModalProps {
  contact: Contact | null;
  open: boolean;
  onClose: () => void;
}

const NOTE_CATEGORIES = ["BISNIS", "TEKNIS", "PENTING"] as const;

const CATEGORY_STYLES: Record<typeof NOTE_CATEGORIES[number], { border: string; header: string }> = {
  BISNIS: { border: "border-blue-200 dark:border-blue-800", header: "text-blue-600 dark:text-blue-400" },
  TEKNIS: { border: "border-purple-200 dark:border-purple-800", header: "text-purple-600 dark:text-purple-400" },
  PENTING: { border: "border-red-200 dark:border-red-800", header: "text-red-600 dark:text-red-400" },
};

export default function NotesModal({ contact, open, onClose }: NotesModalProps) {
  const [notes, setNotes] = useState<ClientNote[]>([]);
  const [form, setForm] = useState({ category: "BISNIS", content: "" });
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const effectiveLeadId = contact?.lead_id;

  useEffect(() => {
    if (!open || !effectiveLeadId) return;
    setLoading(true);
    apiFetch(`/api/client-notes?lead_id=${effectiveLeadId}`)
      .then(r => r.ok ? r.json() : [])
      .then(setNotes)
      .catch(() => setNotes([]))
      .finally(() => setLoading(false));
  }, [open, effectiveLeadId]);

  async function handleSaveNote() {
    if (!form.content || !effectiveLeadId) return;
    await apiFetch("/api/client-notes", {
      method: "POST",
      body: JSON.stringify({ lead_id: effectiveLeadId, category: form.category, content: form.content }),
    });
    setForm({ category: "BISNIS", content: "" });
    // Refresh notes
    const r = await apiFetch(`/api/client-notes?lead_id=${effectiveLeadId}`);
    if (r.ok) setNotes(await r.json());
  }

  async function handleDeleteNote(noteId: string) {
    if (!effectiveLeadId) return;
    await apiFetch(`/api/client-notes/${noteId}`, { method: "DELETE" });
    setDeleteNoteId(null);
    const r = await apiFetch(`/api/client-notes?lead_id=${effectiveLeadId}`);
    if (r.ok) setNotes(await r.json());
  }

  if (!open || !contact) return null;

  // If contact has no lead_id, show error state
  if (!effectiveLeadId) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
        <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Catatan — {contact.business_name}</h3>
            <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
          <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-red-500 flex-shrink-0"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
            <div>
              <p className="text-sm font-semibold text-red-700 dark:text-red-400">Kontak belum terhubung ke Lead</p>
              <p className="text-xs text-red-600 dark:text-red-500 mt-1">Hubungi admin untuk memperbaiki data kontak ini.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-3xl p-6 space-y-4 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Catatan — {contact.business_name}</h3>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>

        {/* Add note form */}
        <div className="flex gap-2">
          <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
            className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-xs bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50">
            {NOTE_CATEGORIES.map(cat => <option key={cat} value={cat}>{cat}</option>)}
          </select>
          <input value={form.content} onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
            onKeyDown={e => { if (e.key === "Enter") handleSaveNote(); }}
            className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50"
            placeholder="Tulis catatan baru..." />
          <button onClick={handleSaveNote}
            className="px-4 py-2 bg-brand-yellow hover:bg-amber-600 text-white text-xs font-semibold rounded-xl transition-colors">
            Tambahkan
          </button>
        </div>

        {/* Notes columns */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {NOTE_CATEGORIES.map(cat => {
            const catNotes = notes.filter(n => n.category === cat);
            const styles = CATEGORY_STYLES[cat];
            return (
              <div key={cat} className={`border ${styles.border} rounded-xl p-3`}>
                <p className={`text-xs font-bold uppercase tracking-wide mb-2 ${styles.header}`}>{cat}</p>
                {loading ? (
                  <p className="text-xs text-gray-400 italic">Memuat...</p>
                ) : catNotes.length === 0 ? (
                  <p className="text-xs text-gray-400 italic">Belum ada catatan.</p>
                ) : (
                  <div className="space-y-2">
                    {catNotes.map(n => (
                      <div key={n.id} className="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-2 group">
                        <p className="text-xs text-gray-700 dark:text-gray-300">{n.content}</p>
                        <div className="flex items-center justify-between mt-1">
                          <span className="text-[10px] text-gray-400">{n.actor} · {new Date(n.timestamp).toLocaleDateString("id-ID", { day: "2-digit", month: "short" })}</span>
                          <button onClick={() => setDeleteNoteId(n.id)}
                            className="text-[10px] text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity">
                            Hapus
                          </button>
                        </div>
                        {deleteNoteId === n.id && (
                          <div className="mt-1 flex gap-1">
                            <button onClick={() => handleDeleteNote(n.id)} className="text-[10px] text-red-500 font-semibold">Ya, hapus</button>
                            <button onClick={() => setDeleteNoteId(null)} className="text-[10px] text-gray-400">Batal</button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}