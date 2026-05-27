"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import { Plus, Edit2, Trash2, X, Star, RefreshCw, CheckCircle2, XCircle } from "lucide-react";

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

interface Combo {
  name: string;
  display_name: string;
}

interface HealthState {
  status: "connected" | "offline" | "loading";
  proxy_url: string;
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
  const [toast, setToast] = useState<string | null>(null);

  const [combos, setCombos] = useState<Combo[]>([]);
  const [activeCombo, setActiveCombo] = useState<string>("");
  const [switching, setSwitching] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthState>({ status: "loading", proxy_url: "" });

  const fetchModels = useCallback(async () => {
    try {
      const res = await apiFetch("/api/ai-models");
      if (res.ok) setModels(await res.json());
    } finally { setLoading(false); }
  }, []);

  const fetchCombos = useCallback(async () => {
    const [combosRes, activeRes] = await Promise.all([
      apiFetch("/api/ai/combos"),
      apiFetch("/api/ai/active-combo"),
    ]);
    if (combosRes.ok) setCombos(await combosRes.json());
    if (activeRes.ok) {
      const data = await activeRes.json();
      setActiveCombo(data.combo);
    }
  }, []);

  const checkHealth = useCallback(async () => {
    setHealth(h => ({ ...h, status: "loading" }));
    try {
      const res = await apiFetch("/api/ai/health");
      if (res.ok) setHealth(await res.json());
    } catch {
      setHealth({ status: "offline", proxy_url: "" });
    }
  }, []);

  useEffect(() => { fetchModels(); fetchCombos(); checkHealth(); }, [fetchModels, fetchCombos, checkHealth]);

  async function selectCombo(name: string) {
    if (name === activeCombo || switching) return;
    if (!confirm(`Ganti combo aktif ke "${name}"?`)) return;
    setSwitching(name);
    try {
      const res = await apiFetch("/api/ai/active-combo", {
        method: "POST",
        body: JSON.stringify({ combo: name }),
      });
      if (res.ok) {
        setActiveCombo(name);
        showToast(`Combo diubah ke ${name}`);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Gagal mengubah combo");
      }
    } finally { setSwitching(null); }
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
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Semua AI call routes through 9router. Pilih combo aktif di bawah.</p>
      </div>

      {/* Section 1: Proxy Status */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">9router Proxy</h2>
            <p className="text-xs text-neutral-500 font-mono mt-1">{health.proxy_url || "—"}</p>
          </div>
          <div className="flex items-center gap-3">
            {health.status === "connected" && (
              <span className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 rounded-xl text-xs font-semibold">
                <CheckCircle2 size={14} /> Connected
              </span>
            )}
            {health.status === "offline" && (
              <span className="flex items-center gap-1.5 px-3 py-1.5 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-xl text-xs font-semibold">
                <XCircle size={14} /> Offline
              </span>
            )}
            {health.status === "loading" && (
              <span className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 text-gray-500 rounded-xl text-xs font-semibold">
                Mengecek...
              </span>
            )}
            <button onClick={checkHealth} className="p-2 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors" title="Refresh">
              <RefreshCw size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Section 2: Active Combo */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 space-y-4">
        <div>
          <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Combo Aktif</h2>
          <p className="text-xs text-neutral-500 mt-1">Klik combo untuk mengaktifkannya. Semua AI call CRM akan langsung pakai combo ini tanpa restart.</p>
        </div>
        {combos.length === 0 ? (
          <div className="p-6 text-center text-sm text-neutral-400">Memuat combo...</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {combos.map(c => {
              const isActive = c.name === activeCombo;
              const isSwitching = switching === c.name;
              return (
                <button
                  key={c.name}
                  onClick={() => selectCombo(c.name)}
                  disabled={isSwitching || isActive}
                  className={`text-left p-4 rounded-xl border-2 transition-all ${
                    isActive
                      ? "border-[#f5a700] bg-amber-50/50 dark:bg-amber-900/10"
                      : "border-[var(--border-subtle)] hover:border-amber-300 hover:bg-amber-50/30 dark:hover:bg-amber-900/5"
                  } ${isSwitching ? "opacity-60" : ""}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{c.display_name}</p>
                      <p className="text-[11px] text-neutral-400 font-mono mt-0.5">{c.name}</p>
                    </div>
                    {isActive && (
                      <span className="shrink-0 px-2 py-0.5 bg-[#f5a700] text-white text-[10px] font-bold uppercase rounded">Aktif</span>
                    )}
                    {isSwitching && (
                      <span className="shrink-0 text-[10px] text-amber-600">Switching...</span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Section 3: Model Registry (simplified) */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-subtle)]">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Model Registry ({models.length})</h2>
            <button onClick={openNew} className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs font-semibold rounded-xl transition-colors">
              <Plus size={14} /> Tambah Model
            </button>
          </div>
          <p className="text-xs text-neutral-500 mt-2">Optional: override capability tertentu (image gen, dll). Kosong = pakai active combo.</p>
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-neutral-400">Memuat...</div>
        ) : models.length === 0 ? (
          <div className="p-8 text-center text-sm text-neutral-400">Belum ada override. Default pakai combo aktif.</div>
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
                <input value={form.model_id} onChange={e => setForm(f => ({ ...f, model_id: e.target.value }))} className={inputCls} placeholder="claude-haiku-4-5-20251001" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Deskripsi (opsional)</label>
                <input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} className={inputCls} placeholder="Override khusus untuk image gen" />
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
