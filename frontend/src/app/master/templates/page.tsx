"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "../../../lib/api";
import { Plus, Edit2, Trash2, X, FileText } from "lucide-react";

interface DynTemplate {
  id: string;
  name: string;
  type: string;
  content: string;
  is_active: boolean;
  category_id: string | null;
  category_name: string | null;
}

interface CategoryOption {
  id: string;
  name: string;
}

const TEMPLATE_TYPES = [
  { value: "WA_BLAST", label: "WA Blast" },
  { value: "PROPOSAL_TEXT", label: "Proposal Text" },
  { value: "PROPOSAL_INTRO", label: "Proposal Intro" },
  { value: "PROPOSAL_OUTRO", label: "Proposal Outro" },
  { value: "FOLLOW_UP", label: "Follow Up" },
  { value: "GENERAL", label: "General" },
];

const TYPE_COLORS: Record<string, string> = {
  WA_BLAST: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  PROPOSAL_TEXT: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
  PROPOSAL_INTRO: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  PROPOSAL_OUTRO: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  FOLLOW_UP: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  GENERAL: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
};

export default function DynamicTemplatesPage() {
  const [templates, setTemplates] = useState<DynTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<DynTemplate | null>(null);
  const [form, setForm] = useState({ name: "", type: "WA_BLAST", content: "", is_active: true, category_id: "" });
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await apiFetch("/api/dynamic-templates");
      if (res.ok) setTemplates(await res.json());
    } finally { setLoading(false); }
  }, []);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await apiFetch("/api/categories?active_only=true");
      if (res.ok) setCategories(await res.json());
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchTemplates();
    fetchCategories();
    intervalRef.current = setInterval(fetchTemplates, 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchTemplates, fetchCategories]);

  function openNew() {
    setEditing(null);
    setForm({ name: "", type: "WA_BLAST", content: "", is_active: true, category_id: "" });
    setModal(true);
  }

  function openEdit(t: DynTemplate) {
    setEditing(t);
    setForm({ name: t.name, type: t.type, content: t.content, is_active: t.is_active, category_id: t.category_id || "" });
    setModal(true);
  }

  async function save() {
    const payload = { ...form, category_id: form.category_id || null };
    const method = editing ? "PUT" : "POST";
    const url = editing ? `/api/dynamic-templates/${editing.id}` : "/api/dynamic-templates";
    const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
    if (res.ok) { setModal(false); fetchTemplates(); }
  }

  async function deleteTemplate(id: string) {
    const res = await apiFetch(`/api/dynamic-templates/${id}`, { method: "DELETE" });
    if (res.ok) fetchTemplates();
  }

  const inputCls = "w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50 transition";

  if (loading) {
    return (
      <div className="max-w-6xl space-y-6">
        <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded w-48 animate-pulse" />
        <div className="space-y-3">{[1, 2, 3].map(i => <div key={i} className="h-20 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />)}</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Template Teks</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Master template dinamis untuk WA Blast, Proposal, dan lainnya.</p>
        </div>
        <button onClick={openNew} className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs sm:text-sm font-semibold rounded-xl transition-colors">
          <Plus size={16} /> Tambah Template
        </button>
      </div>

      {templates.length === 0 ? (
        <div className="text-center py-12 bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] text-gray-400 text-sm">
          Belum ada template. Tambahkan template pertamamu.
        </div>
      ) : (
        <div className="space-y-3">
          {templates.map(t => (
            <div key={t.id} className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] shadow-sm p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-brand-yellow/10 flex items-center justify-center shrink-0 mt-0.5"><FileText size={15} className="text-brand-yellow" /></div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{t.name}</p>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${TYPE_COLORS[t.type] || TYPE_COLORS.GENERAL}`}>{TEMPLATE_TYPES.find(tt => tt.value === t.type)?.label || t.type}</span>
                      {!t.is_active && <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-200 dark:bg-gray-700 text-gray-500">Nonaktif</span>}
                    </div>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2 font-mono whitespace-pre-wrap">{t.content}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0 ml-3">
                  <button onClick={() => openEdit(t)} className="p-1.5 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors"><Edit2 size={14} /></button>
                  <button onClick={() => deleteTemplate(t.id)} className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors"><Trash2 size={14} /></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-lg p-6 space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editing ? "Edit Template" : "Tambah Template"}</h3>
              <button onClick={() => setModal(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Template</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Contoh: Blast SEO Promo" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Tipe</label>
                <select value={form.type} onChange={e => setForm(f => ({ ...f, type: e.target.value }))} className={inputCls}>
                  {TEMPLATE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Kategori Produk</label>
                <select value={form.category_id} onChange={e => setForm(f => ({ ...f, category_id: e.target.value }))} className={inputCls}>
                  <option value="">— Tanpa Kategori —</option>
                  {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <p className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1">Untuk WA Blast: template akan difilter berdasarkan kategori saat eksekusi.</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Isi Konten</label>
                <textarea value={form.content} onChange={e => setForm(f => ({ ...f, content: e.target.value }))} rows={6} className={inputCls + " resize-none font-mono"} placeholder="Halo {{client_name}}, kami ingin menawarkan {{product_name}}..." />
                <div className="mt-1.5 p-2.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-lg">
                  <p className="text-[11px] text-blue-600 dark:text-blue-400 font-medium">Variabel yang tersedia:</p>
                  <p className="text-[11px] text-blue-500 dark:text-blue-300 mt-0.5 font-mono">{"{{client_name}}"} · {"{{business_name}}"} · {"{{product_name}}"}</p>
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} className="w-4 h-4 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
                <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">Aktif</span>
              </label>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setModal(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={save} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
