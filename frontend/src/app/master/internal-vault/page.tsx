"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import Modal from "../../../components/Modal";
import Toast from "../../../components/Toast";
import { Plus, Eye, EyeOff, Copy, Key, Trash2, ExternalLink } from "lucide-react";

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

export default function InternalVaultPage() {
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
  const [search, setSearch] = useState("");
  const [catDropdownOpen, setCatDropdownOpen] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [editingCat, setEditingCat] = useState<string | null>(null);
  const [editingCatValue, setEditingCatValue] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

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
      const res = await apiFetch("/api/credentials?lead_id=internal");
      if (res.ok) setCredentials(await res.json());
    } finally { setLoading(false); }
  }, []);

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
      const payload = { category: formCategory, title: formTitle, fields: validFields, lead_id: null };
      const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
      if (res.ok) {
        setShowModal(false);
        fetchCredentials();
      }
    } finally { setSaving(false); }
  }

  async function deleteCredential(id: string) {
    const res = await apiFetch(`/api/credentials/${id}`, { method: "DELETE" });
    if (res.ok) { setToast({ message: "Berhasil dihapus.", type: "success" }); setCredentials(prev => prev.filter(c => c.id !== id)); }
    else { setToast({ message: "Gagal hapus.", type: "error" }); }
    setDeleteId(null);
  }

  const filtered = credentials.filter(c =>
    c.title.toLowerCase().includes(search.toLowerCase()) ||
    c.category.toLowerCase().includes(search.toLowerCase()) ||
    c.fields.some(f => f.key.toLowerCase().includes(search.toLowerCase()) || (!f.is_secret && f.value.toLowerCase().includes(search.toLowerCase())))
  );

  if (loading) {
    return (
      <div className="max-w-5xl space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
      <Modal
        open={!!deleteId}
        title="Hapus Kredensial?"
        message="Item yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteId !== null && deleteCredential(deleteId!)}
        onCancel={() => setDeleteId(null)}
      />
        <div className="h-8 bg-neutral-100 dark:bg-neutral-800 rounded w-48 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-40 bg-neutral-100 dark:bg-neutral-800 rounded-2xl animate-pulse" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center">
              <Key size={20} className="text-brand-yellow" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Brankas Internal</h1>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">Kredensial pribadi & internal (terenkripsi)</p>
            </div>
          </div>
        </div>
        <button onClick={openNew} className="btn-primary flex items-center gap-1.5 text-white">
          <Plus size={16} /> Tambah Kredensial
        </button>
      </div>

      {/* Search */}
      <div className="card p-4">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="input-field"
          placeholder="Cari kredensial berdasarkan judul, kategori, atau key..."
        />
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <div className="card text-center py-16">
          <Key size={40} className="mx-auto text-neutral-300 dark:text-neutral-600 mb-4" />
          <p className="text-neutral-500 dark:text-neutral-400 text-sm">
            {search ? "Tidak ada kredensial yang cocok." : "Belum ada kredensial internal tersimpan."}
          </p>
          {!search && (
            <button onClick={openNew} className="btn-primary mt-4 text-white">
              <Plus size={14} className="inline mr-1" /> Tambah Pertama
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map(cred => (
            <div key={cred.id} className="card p-4 space-y-3 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                    {cred.category}
                  </span>
                  <h3 className="text-sm font-bold text-neutral-900 dark:text-neutral-50 mt-1.5">{cred.title}</h3>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(cred)} className="p-1.5 text-neutral-400 hover:text-brand-yellow rounded-lg transition-colors">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                  </button>
                  <button onClick={() => setDeleteId(cred.id)} className="p-1.5 text-neutral-400 hover:text-red-500 rounded-lg transition-colors">
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

              <div className="pt-2 border-t border-[var(--border-subtle)]">
                <span className="text-[10px] text-neutral-400">
                  Ditambahkan {new Date(cred.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}
                </span>
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
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editingId ? "Edit Kredensial" : "Tambah Kredensial Internal"}</h3>
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
                <input value={formTitle} onChange={e => setFormTitle(e.target.value)} className="input-field" placeholder="cPanel Server Utama" />
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
              <button onClick={saveCredential} disabled={saving} className="btn-primary text-white">
                {saving ? "Menyimpan..." : "Simpan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
