"use client";
import { useState } from "react";
import { Star, Edit2, Trash2, Plus, X } from "lucide-react";
import { inputCls } from "../../../lib/inputCls";

interface AIModel {
  id: string; name: string; model_id: string; description: string | null;
  capabilities: string[]; is_active: boolean;
  is_default_chat: boolean; is_default_image: boolean;
  is_default_article: boolean; is_default_analysis: boolean;
}

interface RouterModel {
  id: string;
  name?: string;
  type?: string;
}

const CAPABILITIES = ["article", "analysis"] as const;
const CAP_LABELS: Record<string, string> = { article: "Artikel SEO", analysis: "Analisa Lead" };
const CAP_COLORS: Record<string, string> = {
  article: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  analysis: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
};

interface ModelRegistrySectionProps {
  models: AIModel[];
  routerModels: RouterModel[];
  loading: boolean;
  onFetchModels: () => void;
  onDeleteModel: (id: string) => void;
  onSetDefault: (id: string, capability: string) => void;
  showToast: (msg: string) => void;
}

export default function ModelRegistrySection({
  models, routerModels, loading, onFetchModels, onDeleteModel, onSetDefault, showToast,
}: ModelRegistrySectionProps) {
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<AIModel | null>(null);
  const [form, setForm] = useState({ name: "", model_id: "", description: "", capabilities: ["chat"] as string[], is_active: true });

  function openNew() { setEditing(null); setForm({ name: "", model_id: "", description: "", capabilities: ["article"], is_active: true }); setModal(true); }
  function openEdit(m: AIModel) { setEditing(m); setForm({ name: m.name, model_id: m.model_id, description: m.description || "", capabilities: m.capabilities.filter(c => CAPABILITIES.includes(c as any)), is_active: m.is_active }); setModal(true); }
  function toggleCapability(cap: string) { setForm(f => ({ ...f, capabilities: f.capabilities.includes(cap) ? f.capabilities.filter(c => c !== cap) : [...f.capabilities, cap] })); }

  return (
    <>
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-subtle)]">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Model Registry ({models.length})</h2>
            <button onClick={openNew} className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs font-semibold rounded-xl transition-colors">
              <Plus size={14} /> Tambah Model
            </button>
          </div>
          <p className="text-xs text-neutral-500 mt-2">Daftar model 9router yang boleh dipilih untuk Artikel SEO dan Analisa Lead.</p>
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-neutral-400">Memuat...</div>
        ) : models.length === 0 ? (
          <div className="p-8 text-center text-sm text-neutral-400">Belum ada model override. Default pakai provider aktif.</div>
        ) : (
          <div className="divide-y divide-[var(--border-subtle)]">
            {models.map(m => (
              <div key={m.id} className="px-5 py-3 flex items-center gap-4 hover:bg-[var(--bg-surface-hover)] transition-colors">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{m.name}</p>
                    {!m.is_active && <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-500">Nonaktif</span>}
                  </div>
                  <p className="text-xs text-neutral-400 font-mono">{m.model_id}</p>
                  <div className="flex items-center gap-1.5 mt-1">
                    {m.capabilities.map(cap => (
                      <span key={cap} className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${CAP_COLORS[cap] || "bg-gray-100 text-gray-600"}`}>
                        {CAP_LABELS[cap] || cap}
                        {(cap === "article" && m.is_default_article) || (cap === "analysis" && m.is_default_analysis) ? " *" : ""}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {m.capabilities.map(cap => (
                    <button key={cap} onClick={() => onSetDefault(m.id, cap)} title={`Set default ${CAP_LABELS[cap]}`}
                      className={`p-1.5 rounded-lg transition-colors ${(cap === "article" && m.is_default_article) || (cap === "analysis" && m.is_default_analysis) ? "text-brand-yellow" : "text-gray-300 hover:text-brand-yellow"}`}>
                      <Star size={12} fill={(cap === "article" && m.is_default_article) || (cap === "analysis" && m.is_default_analysis) ? "currentColor" : "none"} />
                    </button>
                  ))}
                  <button onClick={() => openEdit(m)} className="p-1.5 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors"><Edit2 size={14} /></button>
                  <button onClick={() => onDeleteModel(m.id)} className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors"><Trash2 size={14} /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Model Modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editing ? "Edit Model" : "Tambah Model Override"}</h3>
              <button onClick={() => setModal(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Display</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Claude Haiku 4.5" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Model ID</label>
                {routerModels.length > 0 ? (
                  <select value={form.model_id} onChange={e => setForm(f => ({ ...f, model_id: e.target.value }))} className={inputCls}>
                    <option value="">Pilih model 9router</option>
                    {routerModels.map(model => <option key={model.id} value={model.id}>{model.id}</option>)}
                  </select>
                ) : (
                  <input value={form.model_id} onChange={e => setForm(f => ({ ...f, model_id: e.target.value }))} className={inputCls} placeholder="combo-genflow" />
                )}
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Deskripsi (opsional)</label>
                <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} className={inputCls} placeholder="Contoh: model cepat untuk artikel SEO" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Dipakai untuk</label>
                <div className="flex flex-wrap gap-2 mt-1">
                  {CAPABILITIES.map(cap => (
                    <button key={cap} type="button" onClick={() => toggleCapability(cap)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${form.capabilities.includes(cap) ? CAP_COLORS[cap] : "bg-gray-100 dark:bg-gray-800 text-gray-400"}`}>
                      {CAP_LABELS[cap]}
                    </button>
                  ))}
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} className="w-4 h-4 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
                <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">Aktif</span>
              </label>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setModal(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={async () => {
                if (!form.name || !form.model_id) return;
                const { apiFetch } = await import("../../../lib/api");
                const method = editing ? "PUT" : "POST";
                const url = editing ? `/api/ai-models/${editing.id}` : "/api/ai-models";
                const res = await apiFetch(url, { method, body: JSON.stringify(form) });
                if (res.ok) { setModal(false); onFetchModels(); showToast(editing ? "Model diupdate" : "Model ditambahkan"); }
              }} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
