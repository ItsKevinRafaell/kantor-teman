"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../../../lib/api";
import { FileText, Key, ExternalLink, Plus, Trash2, Eye, EyeOff, Copy } from "lucide-react";
import Toast from "../../../../../components/Toast";
import Modal from "../../../../../components/Modal";

// ---------------------------------------------------------------------------
// Shared Types
// ---------------------------------------------------------------------------

interface NoteData {
  id: string;
  category: string;
  content: string;
  actor: string;
  timestamp: string;
}

interface CredentialField {
  key: string;
  value: string;
  is_secret: boolean;
}

interface CredentialData {
  id: string;
  lead_id: number | null;
  category: string;
  title: string;
  fields: CredentialField[];
  created_at: string;
}

interface DocumentData {
  id: string;
  lead_id: number | null;
  title: string;
  cloud_url: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Notes Timeline
// ---------------------------------------------------------------------------

const CATEGORY_BADGE: Record<string, string> = {
  BISNIS: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  TEKNIS: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  PENTING: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

function NotesTimeline({ clientId, initialNotes }: { clientId: number; initialNotes: NoteData[] }) {
  const [notes, setNotes] = useState<NoteData[]>(initialNotes);
  const [filter, setFilter] = useState<"ALL" | "BISNIS" | "TEKNIS" | "PENTING">("ALL");
  const [form, setForm] = useState({ category: "BISNIS", content: "" });
  const [submitting, setSubmitting] = useState(false);
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
  const [noteToast, setNoteToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  useEffect(() => { setNotes(initialNotes); }, [initialNotes]);

  async function submitNote() {
    if (!form.content.trim()) return;
    setSubmitting(true);
    try {
      const res = await apiFetch("/api/clients/notes", {
        method: "POST",
        body: JSON.stringify({ lead_id: clientId, category: form.category, content: form.content }),
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

      {/* Input Form */}
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
            <button onClick={submitNote} disabled={submitting || !form.content.trim()} className="btn-primary text-xs px-3 py-2 disabled:opacity-50">
              {submitting ? "..." : "Kirim"}
            </button>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="px-5 py-3 border-b border-[var(--border-subtle)] flex items-center gap-2">
        {(["ALL", "BISNIS", "TEKNIS", "PENTING"] as const).map(cat => (
          <button key={cat} onClick={() => setFilter(cat)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${filter === cat ? "bg-brand-yellow/10 text-brand-yellow" : "text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}>
            {cat === "ALL" ? "Semua" : cat.charAt(0) + cat.slice(1).toLowerCase()}
          </button>
        ))}
        <span className="ml-auto text-[11px] text-neutral-400">{filtered.length} catatan</span>
      </div>

      {/* Notes Feed */}
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

// ---------------------------------------------------------------------------
// Credentials Tab
// ---------------------------------------------------------------------------

function CredentialsTab({ clientId }: { clientId: number }) {
  const [credentials, setCredentials] = useState<CredentialData[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [visibleFields, setVisibleFields] = useState<Set<string>>(new Set());
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [formCategory, setFormCategory] = useState("");
  const [formTitle, setFormTitle] = useState("");
  const [formFields, setFormFields] = useState<CredentialField[]>([{ key: "", value: "", is_secret: false }]);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [catDropdownOpen, setCatDropdownOpen] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [editingCat, setEditingCat] = useState<string | null>(null);
  const [editingCatValue, setEditingCatValue] = useState("");
  const [deleteCredId, setDeleteCredId] = useState<string | null>(null);
  const [credToast, setCredToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await apiFetch("/api/credential-categories");
      if (res.ok) setCategories(await res.json());
    } catch { /* non-critical */ }
  }, []);

  async function deleteCategory(cat: string) {
    const updated = categories.filter(c => c !== cat);
    setCategories(updated);
    await apiFetch("/api/credential-categories", { method: "PUT", body: JSON.stringify(updated) });
  }

  async function renameCategory(oldName: string, newName: string) {
    if (!newName.trim() || newName.trim() === oldName) { setEditingCat(null); return; }
    const updated = categories.map(c => c === oldName ? newName.trim() : c);
    setCategories(updated);
    setEditingCat(null);
    await apiFetch("/api/credential-categories", { method: "PUT", body: JSON.stringify(updated) });
  }

  const fetchCredentials = useCallback(async () => {
    try {
      const res = await apiFetch(`/api/credentials?lead_id=${clientId}`);
      if (res.ok) setCredentials(await res.json());
    } finally { setLoading(false); }
  }, [clientId]);

  useEffect(() => { fetchCredentials(); fetchCategories(); }, [fetchCredentials, fetchCategories]);

  function toggleFieldVisibility(fieldKey: string) {
    setVisibleFields(prev => {
      const next = new Set(prev);
      if (next.has(fieldKey)) next.delete(fieldKey); else next.add(fieldKey);
      return next;
    });
  }

  async function copyToClipboard(text: string, id: string) {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  function openNew() {
    setEditingId(null);
    setFormCategory("");
    setFormTitle("");
    setFormFields([{ key: "Username", value: "", is_secret: false }, { key: "Password", value: "", is_secret: true }]);
    setShowModal(true);
  }

  function openEdit(cred: CredentialData) {
    setEditingId(cred.id);
    setFormCategory(cred.category);
    setFormTitle(cred.title);
    setFormFields(cred.fields.length > 0 ? cred.fields.map(f => ({ ...f })) : [{ key: "", value: "", is_secret: false }]);
    setShowModal(true);
  }

  function addField() {
    setFormFields(prev => [...prev, { key: "", value: "", is_secret: false }]);
  }

  function removeField(idx: number) {
    setFormFields(prev => prev.filter((_, i) => i !== idx));
  }

  function updateField(idx: number, patch: Partial<CredentialField>) {
    setFormFields(prev => prev.map((f, i) => i === idx ? { ...f, ...patch } : f));
  }

  async function saveCredential() {
    if (!formTitle || !formCategory || formFields.length === 0) return;
    const validFields = formFields.filter(f => f.key.trim() && f.value.trim());
    if (validFields.length === 0) return;
    setSaving(true);
    try {
      const method = editingId ? "PUT" : "POST";
      const url = editingId ? `/api/credentials/${editingId}` : "/api/credentials";
      const payload = { category: formCategory, title: formTitle, fields: validFields, lead_id: clientId };
      const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
      if (res.ok) {
        setShowModal(false);
        fetchCredentials();
      }
    } finally { setSaving(false); }
  }

  async function deleteCredential(id: string) {
    const res = await apiFetch(`/api/credentials/${id}`, { method: "DELETE" });
    if (res.ok) {
      setCredToast({ message: "Kredensial dihapus.", type: "success" });
      setCredentials(prev => prev.filter(c => c.id !== id));
    } else {
      setCredToast({ message: "Gagal hapus kredensial.", type: "error" });
    }
    setDeleteCredId(null);
  }

  if (loading) {
    return <div className="p-6"><div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl animate-pulse" /></div>;
  }

  return (
    <div>
      <Toast message={credToast?.message ?? null} type={credToast?.type} onClose={() => setCredToast(null)} />
      <Modal
        open={!!deleteCredId}
        title="Hapus Kredensial?"
        message="Kredensial yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteCredId && deleteCredential(deleteCredId)}
        onCancel={() => setDeleteCredId(null)}
      />
      <div className="px-5 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Kredensial & Akses</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">Akun login milik klien ini (terenkripsi).</p>
        </div>
        <button onClick={openNew} className="btn-primary flex items-center gap-1.5 text-xs">
          <Plus size={14} /> Tambah
        </button>
      </div>

      {credentials.length === 0 ? (
        <div className="text-center py-12 text-neutral-400 text-sm">Belum ada kredensial tersimpan.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-5">
          {credentials.map(cred => (
            <div key={cred.id} className="card p-4 space-y-3 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                    {cred.category}
                  </span>
                  <h3 className="text-sm font-bold text-neutral-900 dark:text-neutral-50 mt-1.5">{cred.title}</h3>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(cred)} className="p-1.5 text-neutral-400 hover:text-brand-yellow rounded-lg transition-colors">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                  </button>
                  <button onClick={() => setDeleteCredId(cred.id)} className="p-1.5 text-neutral-400 hover:text-red-500 rounded-lg transition-colors">
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                {cred.fields.map((field, idx) => (
                  <div key={idx}>
                    <span className="text-[10px] text-neutral-400 uppercase font-semibold">{field.key}</span>
                    <div className="flex items-center gap-2">
                      <p className="text-sm text-neutral-800 dark:text-neutral-200 font-mono break-all">
                        {field.is_secret && !visibleFields.has(`${cred.id}-${idx}`) ? "••••••••" : field.value}
                      </p>
                      {field.is_secret && (
                        <button onClick={() => toggleFieldVisibility(`${cred.id}-${idx}`)} className="p-1 text-neutral-400 hover:text-brand-yellow transition-colors">
                          {visibleFields.has(`${cred.id}-${idx}`) ? <EyeOff size={12} /> : <Eye size={12} />}
                        </button>
                      )}
                      <button onClick={() => copyToClipboard(field.value, `${cred.id}-${idx}`)} className="p-1 text-neutral-400 hover:text-brand-yellow transition-colors">
                        <Copy size={12} />
                      </button>
                      {copiedId === `${cred.id}-${idx}` && <span className="text-[10px] text-emerald-500">Copied!</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Credential Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-modal border border-[var(--border-default)] w-full max-w-lg p-6 space-y-4 animate-slide-up max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editingId ? "Edit Kredensial" : "Tambah Kredensial"}</h3>
              <button onClick={() => setShowModal(false)} className="p-1 text-neutral-400 hover:text-neutral-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Kategori</label>
                <div className="relative">
                  <input
                    value={formCategory}
                    onChange={e => { setFormCategory(e.target.value); setCatDropdownOpen(true); }}
                    onFocus={() => setCatDropdownOpen(true)}
                    onBlur={() => { if (!editingCat) setTimeout(() => setCatDropdownOpen(false), 150); }}
                    className="input-field"
                    placeholder="Ketik atau pilih kategori..."
                  />
                  {catDropdownOpen && (() => {
                    const filtered = categories.filter(c => c.toLowerCase().includes(formCategory.toLowerCase()));
                    const showAddNew = formCategory.trim() && !categories.some(c => c.toLowerCase() === formCategory.trim().toLowerCase());
                    if (filtered.length === 0 && !showAddNew) return null;
                    return (
                      <div className="absolute z-10 top-full left-0 right-0 mt-1 bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl shadow-lg max-h-40 overflow-y-auto">
                        {filtered.map(cat => (
                          <div key={cat} className="flex items-center justify-between px-3 py-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
                            {editingCat === cat ? (
                              <input
                                autoFocus
                                value={editingCatValue}
                                onChange={e => setEditingCatValue(e.target.value)}
                                onBlur={() => renameCategory(cat, editingCatValue)}
                                onKeyDown={e => { if (e.key === "Enter") renameCategory(cat, editingCatValue); if (e.key === "Escape") setEditingCat(null); }}
                                onMouseDown={e => e.stopPropagation()}
                                className="flex-1 text-sm px-1 py-0.5 border border-brand-yellow rounded bg-transparent text-neutral-800 dark:text-neutral-200 outline-none"
                              />
                            ) : (
                              <button type="button" onMouseDown={() => { setFormCategory(cat); setCatDropdownOpen(false); }}
                                className="flex-1 text-left text-sm text-neutral-700 dark:text-neutral-300">
                                {cat}
                              </button>
                            )}
                            <div className="flex items-center gap-0.5 shrink-0 ml-1">
                              <button type="button" onMouseDown={e => { e.preventDefault(); e.stopPropagation(); setEditingCat(cat); setEditingCatValue(cat); }}
                                className="p-1 text-neutral-300 hover:text-brand-yellow transition-colors">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                              </button>
                              <button type="button" onMouseDown={e => { e.preventDefault(); e.stopPropagation(); deleteCategory(cat); }}
                                className="p-1 text-neutral-300 hover:text-red-500 transition-colors">
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </div>
                        ))}
                        {showAddNew && (
                          <button type="button" onMouseDown={() => { const updated = [...categories, formCategory.trim()]; setCategories(updated); apiFetch("/api/credential-categories", { method: "PUT", body: JSON.stringify(updated) }); setCatDropdownOpen(false); }}
                            className="w-full text-left px-3 py-2 text-sm text-brand-yellow font-semibold hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors">
                            + Tambah &quot;{formCategory.trim()}&quot;
                          </button>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Judul / Label</label>
                <input value={formTitle} onChange={e => setFormTitle(e.target.value)} className="input-field" placeholder="cPanel Hosting Utama" />
              </div>

              {/* Dynamic Key-Value Fields */}
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-2">Fields</label>
                <div className="space-y-2">
                  {formFields.map((field, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <input
                        value={field.key}
                        onChange={e => updateField(idx, { key: e.target.value })}
                        className="input-field flex-1"
                        placeholder="Key (Username, Password, API Key...)"
                      />
                      <input
                        type={field.is_secret ? "password" : "text"}
                        value={field.value}
                        onChange={e => updateField(idx, { value: e.target.value })}
                        className="input-field flex-[2]"
                        placeholder="Value"
                      />
                      <button
                        type="button"
                        onClick={() => updateField(idx, { is_secret: !field.is_secret })}
                        className={`p-2 rounded-lg border transition-colors shrink-0 ${field.is_secret ? "border-amber-300 bg-amber-50 dark:bg-amber-900/20 text-amber-600" : "border-neutral-200 dark:border-neutral-700 text-neutral-400 hover:text-neutral-600"}`}
                        title={field.is_secret ? "Sensitif (terenkripsi)" : "Biasa (tidak terenkripsi)"}
                      >
                        {field.is_secret ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                      {formFields.length > 1 && (
                        <button type="button" onClick={() => removeField(idx)} className="p-2 text-neutral-400 hover:text-red-500 transition-colors shrink-0">
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                <button type="button" onClick={addField} className="mt-2 text-xs text-brand-yellow hover:text-amber-600 font-semibold flex items-center gap-1">
                  <Plus size={12} /> Tambah Field
                </button>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowModal(false)} className="btn-ghost">Batal</button>
              <button onClick={saveCredential} disabled={saving} className="btn-primary">
                {saving ? "Menyimpan..." : "Simpan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Documents Tab
// ---------------------------------------------------------------------------

function DocumentsTab({ clientId }: { clientId: number }) {
  const [documents, setDocuments] = useState<DocumentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ title: "", cloud_url: "" });
  const [saving, setSaving] = useState(false);
  const [deleteDocId, setDeleteDocId] = useState<string | null>(null);
  const [docToast, setDocToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await apiFetch(`/api/documents?lead_id=${clientId}`);
      if (res.ok) setDocuments(await res.json());
    } finally { setLoading(false); }
  }, [clientId]);

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

  async function saveDocument() {
    if (!form.title || !form.cloud_url) return;
    setSaving(true);
    try {
      const res = await apiFetch("/api/documents", {
        method: "POST",
        body: JSON.stringify({ ...form, lead_id: clientId }),
      });
      if (res.ok) {
        setShowModal(false);
        setForm({ title: "", cloud_url: "" });
        fetchDocuments();
      }
    } finally { setSaving(false); }
  }

  async function deleteDocument(id: string) {
    const res = await apiFetch(`/api/documents/${id}`, { method: "DELETE" });
    if (res.ok) {
      setDocToast({ message: "Dokumen dihapus.", type: "success" });
      setDocuments(prev => prev.filter(d => d.id !== id));
    } else {
      setDocToast({ message: "Gagal hapus dokumen.", type: "error" });
    }
    setDeleteDocId(null);
  }

  if (loading) {
    return <div className="p-6"><div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl animate-pulse" /></div>;
  }

  return (
    <div>
      <Toast message={docToast?.message ?? null} type={docToast?.type} onClose={() => setDocToast(null)} />
      <Modal
        open={!!deleteDocId}
        title="Hapus Dokumen?"
        message="Dokumen yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteDocId && deleteDocument(deleteDocId)}
        onCancel={() => setDeleteDocId(null)}
      />
      <div className="px-5 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Dokumen & Media</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">Link dokumen cloud milik klien ini.</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-1.5 text-xs">
          <Plus size={14} /> Tambah
        </button>
      </div>

      {documents.length === 0 ? (
        <div className="text-center py-12 text-neutral-400 text-sm">Belum ada dokumen tersimpan.</div>
      ) : (
        <div className="divide-y divide-[var(--border-subtle)]">
          {documents.map(doc => (
            <div key={doc.id} className="px-5 py-4 flex items-center justify-between hover:bg-[var(--bg-surface-hover)] transition-colors group">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center shrink-0">
                  <FileText size={16} className="text-blue-600 dark:text-blue-400" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{doc.title}</p>
                  <a href={doc.cloud_url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 dark:text-blue-400 hover:underline truncate block">
                    {doc.cloud_url}
                  </a>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[10px] text-neutral-400">
                  {new Date(doc.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}
                </span>
                <button onClick={() => setDeleteDocId(doc.id)} className="p-1.5 text-neutral-400 hover:text-red-500 rounded-lg transition-colors opacity-0 group-hover:opacity-100">
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Document Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-modal border border-[var(--border-default)] w-full max-w-md p-6 space-y-4 animate-slide-up">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Tambah Dokumen</h3>
              <button onClick={() => setShowModal(false)} className="p-1 text-neutral-400 hover:text-neutral-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Judul Dokumen</label>
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} className="input-field" placeholder="Desain Logo Final" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Cloud URL</label>
                <input value={form.cloud_url} onChange={e => setForm(f => ({ ...f, cloud_url: e.target.value }))} className="input-field" placeholder="https://drive.google.com/..." />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowModal(false)} className="btn-ghost">Batal</button>
              <button onClick={saveDocument} disabled={saving} className="btn-primary">
                {saving ? "Menyimpan..." : "Simpan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ClientTabs
// ---------------------------------------------------------------------------

interface ClientTabsProps {
  clientId: number;
  initialNotes: NoteData[];
}

export default function ClientTabs({ clientId, initialNotes }: ClientTabsProps) {
  const [activeTab, setActiveTab] = useState<"notes" | "credentials" | "documents">("notes");

  const tabs = [
    { key: "notes" as const, label: "Timeline Notes", icon: <FileText size={14} /> },
    { key: "credentials" as const, label: "Kredensial & Akses", icon: <Key size={14} /> },
    { key: "documents" as const, label: "Dokumen & Media", icon: <ExternalLink size={14} /> },
  ];

  return (
    <div className="card overflow-hidden">
      {/* Tab Headers */}
      <div className="px-5 py-3 border-b border-[var(--border-default)] flex items-center gap-1 bg-neutral-50/50 dark:bg-neutral-800/30">
        {tabs.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 ${activeTab === tab.key ? "bg-brand-yellow/10 text-brand-yellow shadow-sm" : "text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-700 dark:hover:text-neutral-200"}`}>
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "notes" && <NotesTimeline clientId={clientId} initialNotes={initialNotes} />}
      {activeTab === "credentials" && <CredentialsTab clientId={clientId} />}
      {activeTab === "documents" && <DocumentsTab clientId={clientId} />}
    </div>
  );
}