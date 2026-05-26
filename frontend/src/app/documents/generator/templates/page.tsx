"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../../lib/api";
import { Plus, Pencil, Trash2, X } from "lucide-react";
import Toast from "../../../../components/Toast";

interface DocTemplate {
  id: string;
  name: string;
  type: string;
  html_template: string;
  variables: string[];
  is_active: boolean;
  created_at: string;
}

const TYPES = [
  { value: "invoice", label: "Invoice" },
  { value: "proposal_pdf", label: "Proposal PDF" },
  { value: "surat_penawaran", label: "Surat Penawaran" },
  { value: "kontrak", label: "Kontrak / MoU" },
  { value: "custom", label: "Custom" },
];

export default function DocumentTemplatesPage() {
  const [templates, setTemplates] = useState<DocTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<DocTemplate | null>(null);
  const [form, setForm] = useState({ name: "", type: "invoice", html_template: "", variables: "" });
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await apiFetch("/api/document-templates");
      if (res.ok) setTemplates(await res.json());
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchTemplates(); }, [fetchTemplates]);

  function openNew() {
    setEditing(null);
    setForm({ name: "", type: "invoice", html_template: "", variables: "" });
    setModal(true);
  }

  function openEdit(t: DocTemplate) {
    setEditing(t);
    setForm({ name: t.name, type: t.type, html_template: t.html_template, variables: t.variables.join(", ") });
    setModal(true);
  }

  async function handleSave() {
    if (!form.name.trim() || !form.html_template.trim()) return;
    setSaving(true);
    try {
      const vars = form.variables.split(",").map(v => v.trim()).filter(Boolean);
      const payload = { name: form.name, type: form.type, html_template: form.html_template, variables: vars };
      const url = editing ? `/api/document-templates/${editing.id}` : "/api/document-templates";
      const method = editing ? "PUT" : "POST";
      const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
      if (!res.ok) throw new Error();
      await fetchTemplates();
      setModal(false);
      setToast({ message: editing ? "Template diupdate" : "Template dibuat", type: "success" });
    } catch { setToast({ message: "Gagal simpan", type: "error" }); }
    finally { setSaving(false); }
  }

  async function handleDelete(id: string) {
    if (!confirm("Hapus template ini?")) return;
    const res = await apiFetch(`/api/document-templates/${id}`, { method: "DELETE" });
    if (res.ok || res.status === 204) {
      setTemplates(prev => prev.filter(t => t.id !== id));
      setToast({ message: "Template dihapus", type: "success" });
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Document Templates</h1>
          <p className="text-sm text-gray-500 mt-1">Kelola template HTML untuk generate PDF.</p>
        </div>
        <button onClick={openNew}
          className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-lg transition-colors">
          <Plus size={14} /> Buat Template
        </button>
      </div>

      {loading ? <p className="text-sm text-gray-400">Memuat...</p> : (
        <div className="space-y-2">
          {templates.map(t => (
            <div key={t.id} className="flex items-center justify-between p-4 bg-white dark:bg-neutral-900 border border-[var(--border-default)] rounded-xl">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{t.name}</p>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 font-bold uppercase">{t.type}</span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">Variabel: {t.variables.length > 0 ? t.variables.join(", ") : "—"}</p>
              </div>
              <div className="flex gap-1 ml-3">
                <button onClick={() => openEdit(t)} className="p-2 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-lg"><Pencil size={14} className="text-gray-500" /></button>
                <button onClick={() => handleDelete(t.id)} className="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"><Trash2 size={14} className="text-red-400" /></button>
              </div>
            </div>
          ))}
          {templates.length === 0 && <p className="text-sm text-gray-400 text-center py-8">Belum ada template.</p>}
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-neutral-900 rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-xl">
            <div className="flex items-center justify-between p-5 border-b border-[var(--border-default)]">
              <h3 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">{editing ? "Edit Template" : "Buat Template"}</h3>
              <button onClick={() => setModal(false)} className="p-2 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-lg"><X size={18} /></button>
            </div>
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Nama Template</label>
                  <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Type</label>
                  <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800">
                    {TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Variables (comma-separated)</label>
                <input type="text" value={form.variables} onChange={e => setForm({ ...form, variables: e.target.value })}
                  placeholder="klien, tanggal, total, items_rows"
                  className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 font-mono" />
              </div>
              <div>
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">HTML Template</label>
                <textarea value={form.html_template} onChange={e => setForm({ ...form, html_template: e.target.value })}
                  rows={16}
                  className="mt-1 w-full px-3 py-2 text-xs border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 font-mono resize-y" />
              </div>
            </div>
            <div className="flex justify-end gap-3 p-5 border-t border-[var(--border-default)]">
              <button onClick={() => setModal(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-lg">Batal</button>
              <button onClick={handleSave} disabled={saving || !form.name.trim() || !form.html_template.trim()}
                className="px-4 py-2 text-sm font-bold bg-amber-500 hover:bg-amber-600 text-white rounded-lg disabled:opacity-50">
                {saving ? "Menyimpan..." : "Simpan"}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
