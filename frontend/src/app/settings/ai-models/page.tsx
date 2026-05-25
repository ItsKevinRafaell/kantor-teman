"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import { Plus, Edit2, Trash2, X, Star } from "lucide-react";

interface AIModel {
  id: string;
  name: string;
  model_id: string;
  description: string | null;
  capabilities: string[];
  is_active: boolean;
  is_default_chat: boolean;
  is_default_image: boolean;
  is_default_article: boolean;
  is_default_analysis: boolean;
}

const CAPABILITIES = ["chat", "image", "article", "analysis"] as const;
const CAP_LABELS: Record<string, string> = { chat: "Chat", image: "Image", article: "Artikel", analysis: "Analisa" };
const CAP_COLORS: Record<string, string> = {
  chat: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  image: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  article: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  analysis: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
};

export default function AIModelsPage() {
  const [models, setModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<AIModel | null>(null);
  const [form, setForm] = useState({ name: "", model_id: "", description: "", capabilities: ["chat"] as string[], is_active: true });
  const [globalKey, setGlobalKey] = useState("");
  const [globalBaseUrl, setGlobalBaseUrl] = useState("");
  const [savingGlobal, setSavingGlobal] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const fetchModels = useCallback(async () => {
    try {
      const res = await apiFetch("/api/ai-models");
      if (res.ok) setModels(await res.json());
    } finally { setLoading(false); }
  }, []);

  const fetchGlobalSettings = useCallback(async () => {
    try {
      const res = await apiFetch("/api/settings");
      if (res.ok) {
        const data = await res.json();
        setGlobalKey(data.ai_api_key || data.openai_api_key || "");
        setGlobalBaseUrl(data.ai_base_url || "");
      }
    } catch { /* silent */ }
  }, []);

  useEffect(() => { fetchModels(); fetchGlobalSettings(); }, [fetchModels, fetchGlobalSettings]);

  async function saveGlobal() {
    setSavingGlobal(true);
    try {
      const res = await apiFetch("/api/settings", {
        method: "PUT",
        body: JSON.stringify({ ai_api_key: globalKey, ai_base_url: globalBaseUrl }),
      });
      if (res.ok) showToast("Global AI config tersimpan");
    } finally { setSavingGlobal(false); }
  }

  function openNew() {
    setEditing(null);
    setForm({ name: "", model_id: "", description: "", capabilities: ["chat"], is_active: true });
    setModal(true);
  }

  function openEdit(m: AIModel) {
    setEditing(m);
    setForm({ name: m.name, model_id: m.model_id, description: m.description || "", capabilities: m.capabilities, is_active: m.is_active });
    setModal(true);
  }

  async function save() {
    if (!form.name || !form.model_id) return;
    const method = editing ? "PUT" : "POST";
    const url = editing ? `/api/ai-models/${editing.id}` : "/api/ai-models";
    const res = await apiFetch(url, { method, body: JSON.stringify(form) });
    if (res.ok) { setModal(false); fetchModels(); showToast(editing ? "Model diupdate" : "Model ditambahkan"); }
  }

  async function deleteModel(id: string) {
    const res = await apiFetch(`/api/ai-models/${id}`, { method: "DELETE" });
    if (res.ok) { fetchModels(); showToast("Model dihapus"); }
  }

  async function setDefault(id: string, capability: string) {
    const res = await apiFetch(`/api/ai-models/${id}/set-default?capability=${capability}`, { method: "POST" });
    if (res.ok) { fetchModels(); showToast(`Default ${CAP_LABELS[capability]} diset`); }
  }

  function toggleCapability(cap: string) {
    setForm(f => ({
      ...f,
      capabilities: f.capabilities.includes(cap)
        ? f.capabilities.filter(c => c !== cap)
        : [...f.capabilities, cap],
    }));
  }

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  const inputCls = "w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50 transition";

  return (
    <div className="max-w-4xl space-y-6">
      {toast && (
        <div className="fixed top-5 right-5 z-[60] bg-emerald-600 text-white px-5 py-3 rounded-xl shadow-lg text-sm font-medium animate-slide-up">
          {toast}
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">AI Models</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Kelola model AI dan set default per fitur. Semua model pakai 1 API key (9router).</p>
      </div>

      {/* Global Config */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 space-y-3">
        <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Global API Config</h2>
        <p className="text-xs text-neutral-500">Satu API key untuk semua model (via 9router atau provider langsung).</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-[10px] font-semibold text-neutral-500 uppercase mb-1">API Key</label>
            <input type="password" value={globalKey} onChange={e => setGlobalKey(e.target.value)} className={inputCls} placeholder="sk-..." />
          </div>
          <div>
            <label className="block text-[10px] font-semibold text-neutral-500 uppercase mb-1">Base URL</label>
            <input value={globalBaseUrl} onChange={e => setGlobalBaseUrl(e.target.value)} className={inputCls} placeholder="https://router.9router.ai/v1" />
          </div>
        </div>
        <button onClick={saveGlobal} disabled={savingGlobal}
          className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors disabled:opacity-50">
          {savingGlobal ? "Menyimpan..." : "Simpan Config"}
        </button>
      </div>

      {/* Models List */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Daftar Model ({models.length})</h2>
          <button onClick={openNew} className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs font-semibold rounded-xl transition-colors">
            <Plus size={14} /> Tambah Model
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-neutral-400">Memuat...</div>
        ) : models.length === 0 ? (
          <div className="p-8 text-center text-sm text-neutral-400">Belum ada model. Tambahkan model pertama.</div>
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
                        {(cap === "chat" && m.is_default_chat) || (cap === "image" && m.is_default_image) || (cap === "article" && m.is_default_article) || (cap === "analysis" && m.is_default_analysis) ? " *" : ""}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {m.capabilities.map(cap => (
                    <button key={cap} onClick={() => setDefault(m.id, cap)}
                      title={`Set default ${CAP_LABELS[cap]}`}
                      className={`p-1.5 rounded-lg transition-colors ${
                        (cap === "chat" && m.is_default_chat) || (cap === "image" && m.is_default_image) || (cap === "article" && m.is_default_article) || (cap === "analysis" && m.is_default_analysis)
                          ? "text-brand-yellow" : "text-gray-300 hover:text-brand-yellow"
                      }`}>
                      <Star size={12} fill={(cap === "chat" && m.is_default_chat) || (cap === "image" && m.is_default_image) || (cap === "article" && m.is_default_article) || (cap === "analysis" && m.is_default_analysis) ? "currentColor" : "none"} />
                    </button>
                  ))}
                  <button onClick={() => openEdit(m)} className="p-1.5 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors"><Edit2 size={14} /></button>
                  <button onClick={() => deleteModel(m.id)} className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors"><Trash2 size={14} /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editing ? "Edit Model" : "Tambah Model"}</h3>
              <button onClick={() => setModal(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Display</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Claude Haiku 4.5" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Model ID (dari provider)</label>
                <input value={form.model_id} onChange={e => setForm(f => ({ ...f, model_id: e.target.value }))} className={inputCls} placeholder="claude-haiku-4-5-20251001" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Deskripsi (opsional)</label>
                <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} className={inputCls} placeholder="Model cepat untuk chat" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Capabilities</label>
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
              <button onClick={save} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
