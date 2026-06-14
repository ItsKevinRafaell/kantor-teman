"use client";
import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../lib/api";
import { RefreshCw, CheckCircle2, XCircle } from "lucide-react";
import ConfirmModal from "../../components/ConfirmModal";
import ModelRegistrySection from "./ai/ModelRegistrySection";
import ProxiesSection from "./ai/ProxiesSection";

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

interface HealthState {
  status: "connected" | "offline" | "not_configured" | "loading";
  provider: string;
  base_url: string;
  model: string;
  models_count?: number;
  stored_base_url?: string;
  base_url_repaired?: boolean;
}

const FEATURES = [
  { key: "article", label: "Generate Artikel SEO" },
  { key: "analysis", label: "Analisa Lead" },
] as const;

function displayProxyName(proxy?: AIProxy | null): string {
  if (!proxy) return "Belum ada";
  const name = (proxy.name || "").trim();
  if (!name || /aimurah|openai|custom/i.test(name)) return "9router";
  return name;
}

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
    openConfirm(`Hapus Model "${name}"?`, "Model override akan dihapus permanen. Endpoint 9router default tetap aktif.", () => deleteModel(id));
  }

  async function deleteProxy(id: string) {
    const res = await apiFetch(`/api/ai-proxies/${id}`, { method: "DELETE" });
    if (res.ok) { fetchProxies(); showToast("Provider dihapus"); }
  }

  function confirmDeleteProxy(id: string, name: string) {
    openConfirm(`Hapus Endpoint "${name}"?`, "Endpoint 9router ini akan dihapus permanen.", () => deleteProxy(id));
  }

  async function setDefault(id: string, capability: string) {
    const res = await apiFetch(`/api/ai-models/${id}/set-default?capability=${capability}`, { method: "POST" });
    if (res.ok) { fetchModels(); showToast(`Default ${capability} diset`); }
  }

  return (
    <div className="max-w-4xl space-y-6">
      {toast && (
        <div className="fixed top-5 right-5 z-[60] bg-emerald-600 text-white px-5 py-3 rounded-xl shadow-lg text-sm font-medium animate-slide-up">
          {toast}
        </div>
      )}

      {/* 9router Health */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Status 9router</h2>
            <p className="text-xs text-neutral-500 mt-0.5">Model dan combo dibaca realtime dari 9router VPS.</p>
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
          <div className="flex flex-wrap items-center gap-4 text-xs text-neutral-500">
            <span><span className="font-semibold">Router:</span> 9router</span>
            <span><span className="font-semibold">Model:</span> {health.model || "—"}</span>
            {health.models_count != null && <span><span className="font-semibold">Registry:</span> {health.models_count} model/combo</span>}
            <span className="truncate"><span className="font-semibold">URL:</span> {health.base_url || "—"}</span>
          </div>
        )}
        {health.base_url_repaired && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
            Config lama di database mengarah ke endpoint non-9router dan sedang diabaikan. Runtime memakai {health.base_url || "endpoint 9router default"}.
          </div>
        )}
      </div>

      {/* Active 9router Config */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 space-y-4">
        <div>
          <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Endpoint Default</h2>
          <p className="text-xs text-neutral-500 mt-1">Endpoint 9router aktif untuk Artikel SEO dan Analisa Lead.</p>
        </div>
        {proxies.length === 0 ? (
          <div className="p-6 text-center">
            <p className="text-sm text-neutral-500 mb-3">Belum ada endpoint 9router. Tambahkan base URL, API key, dan combo/model di bawah.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {proxies.filter(p => p.is_active).map(p => (
              <div key={p.id} className="flex items-center gap-3 px-4 py-3 rounded-xl border-2 border-emerald-300 dark:border-emerald-700 bg-emerald-50/50 dark:bg-emerald-900/10">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{displayProxyName(p)}</span>
                    <span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-[10px] font-bold rounded">AKTIF</span>
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-500">9router</span>
                  </div>
                  <p className="text-xs text-neutral-400 truncate mt-0.5">{p.base_url} • {p.model || "default"}</p>
                </div>
              </div>
            ))}
            {proxies.filter(p => !p.is_active).length > 0 && (
              <p className="text-xs text-neutral-400 mt-2">{proxies.filter(p => !p.is_active).length} endpoint lain tidak aktif. Aktifkan di section "Endpoint 9router".</p>
            )}
          </div>
        )}
      </div>

      {/* Model Override per Fitur */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 space-y-4">
        <div>
          <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Model per Fitur</h2>
          <p className="text-xs text-neutral-500 mt-1">Kosongkan jika semua fitur memakai endpoint aktif yang sama.</p>
        </div>
        <div className="space-y-3">
          {FEATURES.map(f => (
            <div key={f.key} className="flex items-center gap-4">
              <label className="text-sm text-neutral-700 dark:text-neutral-300 w-40 shrink-0">{f.label}</label>
              <select value={featureDefaults[f.key] || ""} onChange={e => setFeatureDefaults(prev => ({ ...prev, [f.key]: e.target.value }))}
                className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50 transition">
                <option value="">Default (endpoint aktif)</option>
                {proxies.map(p => <option key={p.id} value={p.id}>{displayProxyName(p)} {p.model ? `(${p.model})` : ""}</option>)}
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
