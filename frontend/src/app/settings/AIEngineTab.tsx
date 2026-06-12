"use client";
import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../lib/api";
import { RefreshCw, CheckCircle2, XCircle } from "lucide-react";
import ConfirmModal from "../../components/ConfirmModal";
import ModelRegistrySection from "./ai/ModelRegistrySection";
import ProxiesSection from "./ai/ProxiesSection";
import { inputCls } from "../../lib/inputCls";

interface AIModel {
  id: string; name: string; model_id: string; description: string | null;
  capabilities: string[]; is_active: boolean;
  is_default_chat: boolean; is_default_image: boolean;
  is_default_article: boolean; is_default_analysis: boolean;
}

interface AIProxy {
  id: string; name: string; base_url: string; api_key: string;
  model: string; feature: string | null; is_active: boolean; created_at: string;
  provider?: string;
}

interface RouterModel {
  id: string;
  name?: string;
  type?: string;
  owned_by?: string;
}

interface HealthState { status: "connected" | "offline" | "not_configured" | "loading"; provider: string; base_url: string; model: string; }

const PROVIDER_OPTIONS = [
  { value: "custom", label: "9router (OpenAI-compatible)" },
];

const FEATURES = [
  { key: "article", label: "Generate Artikel SEO" },
  { key: "analysis", label: "Analisa Lead" },
] as const;

export default function AIEngineTab() {
  const [models, setModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<HealthState>({ status: "loading", provider: "", base_url: "", model: "" });
  const [featureDefaults, setFeatureDefaults] = useState<Record<string, string>>({});
  const [savingDefaults, setSavingDefaults] = useState(false);
  const [proxies, setProxies] = useState<AIProxy[]>([]);
  const [routerModels, setRouterModels] = useState<RouterModel[]>([]);
  const [confirmState, setConfirmState] = useState({ open: false, title: "", message: "", onConfirm: () => {} });
  const [toast, setToast] = useState<string | null>(null);

  function showToast(msg: string) { setToast(msg); setTimeout(() => setToast(null), 3000); }
  function openConfirm(title: string, message: string, onConfirm: () => void) { setConfirmState({ open: true, title, message, onConfirm }); }

  const fetchModels = useCallback(async () => {
    try { const r = await apiFetch("/api/ai-models"); if (r.ok) setModels(await r.json()); }
    finally { setLoading(false); }
  }, []);
  const checkHealth = useCallback(async () => {
    setHealth(h => ({ ...h, status: "loading" }));
    try {
      const res = await apiFetch("/api/ai/health");
      if (res.ok) { const d = await res.json(); setHealth(d); }
    } catch { setHealth({ status: "offline", provider: "", base_url: "", model: "" }); }
  }, []);
  const fetchFeatureDefaults = useCallback(async () => {
    try { const r = await apiFetch("/api/ai/feature-defaults"); if (r.ok) setFeatureDefaults(await r.json()); } catch {}
  }, []);
  const fetchProxies = useCallback(async () => {
    try { const r = await apiFetch("/api/ai-proxies"); if (r.ok) setProxies(await r.json()); } catch {}
  }, []);
  const fetchRouterModels = useCallback(async () => {
    try {
      const r = await apiFetch("/api/ai/router-models");
      if (r.ok) {
        const data = await r.json();
        setRouterModels(Array.isArray(data.models) ? data.models : []);
      }
    } catch {}
  }, []);

  useEffect(() => { fetchModels(); checkHealth(); fetchFeatureDefaults(); fetchProxies(); fetchRouterModels(); },
    [fetchModels, checkHealth, fetchFeatureDefaults, fetchProxies, fetchRouterModels]);

  async function saveFeatureDefaultsHandler() {
    setSavingDefaults(true);
    try {
      const res = await apiFetch("/api/ai/feature-defaults", { method: "POST", body: JSON.stringify(featureDefaults) });
      if (res.ok) { setFeatureDefaults(await res.json()); showToast("Default per fitur disimpan"); }
      else { const e = await res.json().catch(() => ({})); showToast(e.detail || "Gagal menyimpan"); }
    } finally { setSavingDefaults(false); }
  }

  async function deleteModel(id: string) {
    const res = await apiFetch(`/api/ai-models/${id}`, { method: "DELETE" });
    if (res.ok) { fetchModels(); showToast("Model dihapus"); }
  }

  function confirmDeleteModel(id: string, name: string) {
    openConfirm(`Hapus Model "${name}"?`, "Model override akan dihapus permanen. Provider default tetap aktif.", () => deleteModel(id));
  }

  async function deleteProxy(id: string) {
    const res = await apiFetch(`/api/ai-proxies/${id}`, { method: "DELETE" });
    if (res.ok) { fetchProxies(); showToast("Provider dihapus"); }
  }

  function confirmDeleteProxy(id: string, name: string) {
    openConfirm(`Hapus Provider "${name}"?`, "Provider ini akan dihapus permanen.", () => deleteProxy(id));
  }

  async function setDefault(id: string, capability: string) {
    const res = await apiFetch(`/api/ai-models/${id}/set-default?capability=${capability}`, { method: "POST" });
    if (res.ok) { fetchModels(); showToast(`Default ${capability} diset`); }
  }

  // Get active proxy as default provider
  const activeProxy = proxies.find(p => p.is_active);
  const activeProxyName = activeProxy?.name || "Belum ada";

  return (
    <div className="max-w-4xl space-y-6">
      {toast && (
        <div className="fixed top-5 right-5 z-[60] bg-emerald-600 text-white px-5 py-3 rounded-xl shadow-lg text-sm font-medium animate-slide-up">
          {toast}
        </div>
      )}

      {/* AI Provider Health */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">AI Provider Status</h2>
            <p className="text-xs text-neutral-500 mt-0.5">Status koneksi ke 9router aktif</p>
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
            {health.status === "not_configured" && (
              <span className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 text-gray-500 rounded-xl text-xs font-semibold">Belum dikonfigurasi</span>
            )}
            {health.status === "loading" && (
              <span className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 text-gray-500 rounded-xl text-xs font-semibold">Mengecek...</span>
            )}
            <button onClick={checkHealth} className="p-2 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors" title="Refresh"><RefreshCw size={14} /></button>
          </div>
        </div>
        {health.status === "connected" && (
          <div className="flex items-center gap-4 text-xs text-neutral-500">
            <span><span className="font-semibold">Provider:</span> {PROVIDER_OPTIONS.find(o => o.value === health.provider)?.label || health.provider || "—"}</span>
            <span><span className="font-semibold">Model:</span> {health.model || "—"}</span>
            <span className="truncate"><span className="font-semibold">URL:</span> {health.base_url || "—"}</span>
          </div>
        )}
      </div>

      {/* Active Provider Config */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 space-y-4">
        <div>
          <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Provider Default</h2>
          <p className="text-xs text-neutral-500 mt-1">Provider aktif untuk Artikel SEO dan Analisa Lead.</p>
        </div>
        {proxies.length === 0 ? (
          <div className="p-6 text-center">
            <p className="text-sm text-neutral-500 mb-3">Belum ada provider AI. Tambahkan base URL, API key, dan model di bawah.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {proxies.filter(p => p.is_active).map(p => (
              <div key={p.id} className="flex items-center gap-3 px-4 py-3 rounded-xl border-2 border-emerald-300 dark:border-emerald-700 bg-emerald-50/50 dark:bg-emerald-900/10">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{p.name}</span>
                    <span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-[10px] font-bold rounded">AKTIF</span>
                    {p.provider && <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-500">{PROVIDER_OPTIONS.find(o => o.value === p.provider)?.label || p.provider}</span>}
                  </div>
                  <p className="text-xs text-neutral-400 truncate mt-0.5">{p.base_url} • {p.model || "default"}</p>
                </div>
              </div>
            ))}
            {proxies.filter(p => !p.is_active).length > 0 && (
              <p className="text-xs text-neutral-400 mt-2">{proxies.filter(p => !p.is_active).length} provider lain tidak aktif. Aktifkan di section "AI Proxies".</p>
            )}
          </div>
        )}
      </div>

      {/* Model Override per Fitur */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 space-y-4">
        <div>
          <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Model per Fitur</h2>
          <p className="text-xs text-neutral-500 mt-1">Kosongkan jika semua fitur memakai provider aktif yang sama.</p>
        </div>
        <div className="space-y-3">
          {FEATURES.map(f => (
            <div key={f.key} className="flex items-center gap-4">
              <label className="text-sm text-neutral-700 dark:text-neutral-300 w-40 shrink-0">{f.label}</label>
              <select value={featureDefaults[f.key] || ""} onChange={e => setFeatureDefaults(prev => ({ ...prev, [f.key]: e.target.value }))}
                className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50 transition">
                <option value="">Default (provider aktif)</option>
                {proxies.map(p => <option key={p.id} value={p.id}>{p.name} {p.model ? `(${p.model})` : ""}</option>)}
              </select>
            </div>
          ))}
        </div>
        <button onClick={saveFeatureDefaultsHandler} disabled={savingDefaults}
          className="px-5 py-2.5 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors disabled:opacity-50">
          {savingDefaults ? "Menyimpan..." : "Simpan Default"}
        </button>
      </div>

      {/* Extracted sections */}
      <ModelRegistrySection
        models={models} routerModels={routerModels} loading={loading}
        onFetchModels={fetchModels} onDeleteModel={(id) => { const m = models.find(x => x.id === id); confirmDeleteModel(id, m?.name || "ini"); }}
        onSetDefault={setDefault}
        showToast={showToast}
      />
      <ProxiesSection proxies={proxies} routerModels={routerModels} onFetchProxies={fetchProxies} showToast={showToast} onConfirmDelete={confirmDeleteProxy} />

      <ConfirmModal
        open={confirmState.open} onClose={() => setConfirmState(s => ({ ...s, open: false }))}
        onConfirm={confirmState.onConfirm} title={confirmState.title} message={confirmState.message}
      />
    </div>
  );
}
