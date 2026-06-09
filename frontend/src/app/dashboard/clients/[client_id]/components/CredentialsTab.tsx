"use client";
import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../../../lib/api";
import { Plus, Trash2, Eye, EyeOff, Copy } from "lucide-react";
import Toast from "../../../../../components/Toast";
import Modal from "../../../../../components/Modal";

interface CredentialField { key: string; value: string; is_secret: boolean; }
interface CredentialData {
  id: string; lead_id: number | null; category: string; title: string;
  fields: CredentialField[]; created_at: string;
}

export default function CredentialsTab({ leadId }: { leadId: number | null }) {
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
    } catch {}
  }, []);

  async function deleteCategory(cat: string) {
    const updated = categories.filter(c => c !== cat);
    setCategories(updated);
    await apiFetch("/api/credential-categories", { method: "PUT", body: JSON.stringify(updated) });
  }

  async function renameCategory(oldName: string, newName: string) {
    if (!newName.trim() || newName.trim() === oldName) { setEditingCat(null); return; }
    setCategories(prev => prev.map(c => c === oldName ? newName.trim() : c));
    setEditingCat(null);
    await apiFetch("/api/credential-categories", { method: "PUT", body: JSON.stringify(categories.map(c => c === oldName ? newName.trim() : c)) });
  }

  const fetchCredentials = useCallback(async () => {
    if (!leadId) {
      setCredentials([]);
      setLoading(false);
      return;
    }
    try {
      const res = await apiFetch(`/api/credentials?lead_id=${leadId}`);
      if (res.ok) setCredentials(await res.json());
    } finally { setLoading(false); }
  }, [leadId]);

  useEffect(() => { fetchCredentials(); fetchCategories(); }, [fetchCredentials, fetchCategories]);

  function toggleFieldVisibility(fieldKey: string) {
    setVisibleFields(prev => { const next = new Set(prev); next.has(fieldKey) ? next.delete(fieldKey) : next.add(fieldKey); return next; });
  }

  async function copyToClipboard(text: string, id: string) {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  function openNew() {
    setEditingId(null); setFormCategory(""); setFormTitle("");
    setFormFields([{ key: "Username", value: "", is_secret: false }, { key: "Password", value: "", is_secret: true }]);
    setShowModal(true);
  }

  function openEdit(cred: CredentialData) {
    setEditingId(cred.id); setFormCategory(cred.category); setFormTitle(cred.title);
    setFormFields(cred.fields.length > 0 ? cred.fields.map(f => ({ ...f })) : [{ key: "", value: "", is_secret: false }]);
    setShowModal(true);
  }

  function addField() { setFormFields(prev => [...prev, { key: "", value: "", is_secret: false }]); }
  function removeField(idx: number) { setFormFields(prev => prev.filter((_, i) => i !== idx)); }
  function updateField(idx: number, patch: Partial<CredentialField>) { setFormFields(prev => prev.map((f, i) => i === idx ? { ...f, ...patch } : f)); }

  async function saveCredential() {
    if (!leadId || !formTitle || !formCategory || formFields.length === 0) return;
    const validFields = formFields.filter(f => f.key.trim() && f.value.trim());
    if (validFields.length === 0) return;
    setSaving(true);
    try {
      const method = editingId ? "PUT" : "POST";
      const url = editingId ? `/api/credentials/${editingId}` : "/api/credentials";
      const res = await apiFetch(url, { method, body: JSON.stringify({ category: formCategory, title: formTitle, fields: validFields, lead_id: leadId }) });
      if (res.ok) { setShowModal(false); fetchCredentials(); }
    } finally { setSaving(false); }
  }

  async function deleteCredential(id: string) {
    const res = await apiFetch(`/api/credentials/${id}`, { method: "DELETE" });
    if (res.ok) { setCredToast({ message: "Kredensial dihapus.", type: "success" }); setCredentials(prev => prev.filter(c => c.id !== id)); }
    else { setCredToast({ message: "Gagal hapus kredensial.", type: "error" }); }
    setDeleteCredId(null);
  }

  if (loading) return <div className="p-6"><div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl animate-pulse" /></div>;

  return (
    <div>
      <Toast message={credToast?.message ?? null} type={credToast?.type} onClose={() => setCredToast(null)} />
      <Modal open={!!deleteCredId} title="Hapus Kredensial?" message="Kredensial yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus" confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteCredId && deleteCredential(deleteCredId)} onCancel={() => setDeleteCredId(null)} />
      <div className="px-5 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Kredensial & Akses</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">Akun login milik klien ini (terenkripsi).</p>
        </div>
        <button onClick={openNew} disabled={!leadId} className="btn-primary flex items-center gap-1.5 text-xs disabled:opacity-50"><Plus size={14} /> Tambah</button>
      </div>

      {!leadId ? (
        <div className="text-center py-12 text-amber-600 dark:text-amber-400 text-sm">Kontak ini belum memiliki relasi lead.</div>
      ) : credentials.length === 0 ? (
        <div className="text-center py-12 text-neutral-400 text-sm">Belum ada kredensial tersimpan.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-5">
          {credentials.map(cred => (
            <div key={cred.id} className="card p-4 space-y-3 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">{cred.category}</span>
                  <h3 className="text-sm font-bold text-neutral-900 dark:text-neutral-50 mt-1.5">{cred.title}</h3>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(cred)} className="p-1.5 text-neutral-400 hover:text-brand-yellow rounded-lg transition-colors">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                  </button>
                  <button onClick={() => setDeleteCredId(cred.id)} className="p-1.5 text-neutral-400 hover:text-red-500 rounded-lg transition-colors"><Trash2 size={13} /></button>
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
                      <button onClick={() => copyToClipboard(field.value, `${cred.id}-${idx}`)} className="p-1 text-neutral-400 hover:text-brand-yellow transition-colors"><Copy size={12} /></button>
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
                  <input value={formCategory}
                    onChange={e => { setFormCategory(e.target.value); setCatDropdownOpen(true); }}
                    onFocus={() => setCatDropdownOpen(true)}
                    onBlur={() => { if (!editingCat) setTimeout(() => setCatDropdownOpen(false), 150); }}
                    className="input-field" placeholder="Ketik atau pilih kategori..." />
                  {catDropdownOpen && (() => {
                    const filtered = categories.filter(c => c.toLowerCase().includes(formCategory.toLowerCase()));
                    const showAddNew = formCategory.trim() && !categories.some(c => c.toLowerCase() === formCategory.trim().toLowerCase());
                    if (filtered.length === 0 && !showAddNew) return null;
                    return (
                      <div className="absolute z-10 top-full left-0 right-0 mt-1 bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl shadow-lg max-h-40 overflow-y-auto">
                        {filtered.map(cat => (
                          <div key={cat} className="flex items-center justify-between px-3 py-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
                            {editingCat === cat ? (
                              <input autoFocus value={editingCatValue}
                                onChange={e => setEditingCatValue(e.target.value)}
                                onBlur={() => renameCategory(cat, editingCatValue)}
                                onKeyDown={e => { if (e.key === "Enter") renameCategory(cat, editingCatValue); if (e.key === "Escape") setEditingCat(null); }}
                                onMouseDown={e => e.stopPropagation()}
                                className="flex-1 text-sm px-1 py-0.5 border border-brand-yellow rounded bg-transparent text-neutral-800 dark:text-neutral-200 outline-none" />
                            ) : (
                              <button type="button" onMouseDown={() => { setFormCategory(cat); setCatDropdownOpen(false); }} className="flex-1 text-left text-sm text-neutral-700 dark:text-neutral-300">{cat}</button>
                            )}
                            <div className="flex items-center gap-0.5 shrink-0 ml-1">
                              <button type="button" onMouseDown={e => { e.preventDefault(); e.stopPropagation(); setEditingCat(cat); setEditingCatValue(cat); }} className="p-1 text-neutral-300 hover:text-brand-yellow transition-colors">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                              </button>
                              <button type="button" onMouseDown={e => { e.preventDefault(); e.stopPropagation(); deleteCategory(cat); }} className="p-1 text-neutral-300 hover:text-red-500 transition-colors"><Trash2 size={12} /></button>
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
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-2">Fields</label>
                <div className="space-y-2">
                  {formFields.map((field, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <input value={field.key} onChange={e => updateField(idx, { key: e.target.value })} className="input-field flex-1" placeholder="Key (Username, Password, API Key...)" />
                      <input type={field.is_secret ? "password" : "text"} value={field.value} onChange={e => updateField(idx, { value: e.target.value })} className="input-field flex-[2]" placeholder="Value" />
                      <button type="button" onClick={() => updateField(idx, { is_secret: !field.is_secret })}
                        className={`p-2 rounded-lg border transition-colors shrink-0 ${field.is_secret ? "border-amber-300 bg-amber-50 dark:bg-amber-900/20 text-amber-600" : "border-neutral-200 dark:border-neutral-700 text-neutral-400 hover:text-neutral-600"}`}
                        title={field.is_secret ? "Sensitif (terenkripsi)" : "Biasa (tidak terenkripsi)"}>
                        {field.is_secret ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                      {formFields.length > 1 && (
                        <button type="button" onClick={() => removeField(idx)} className="p-2 text-neutral-400 hover:text-red-500 transition-colors shrink-0"><Trash2 size={14} /></button>
                      )}
                    </div>
                  ))}
                </div>
                <button type="button" onClick={addField} className="mt-2 text-xs text-brand-yellow hover:text-amber-600 font-semibold flex items-center gap-1"><Plus size={12} /> Tambah Field</button>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowModal(false)} className="btn-ghost">Batal</button>
              <button onClick={saveCredential} disabled={saving} className="btn-primary">{saving ? "Menyimpan..." : "Simpan"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
