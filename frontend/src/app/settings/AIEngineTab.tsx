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
}

interface Combo { name: string; display_name: string; }
interface HealthState { status: "connected" | "offline" | "loading"; proxy_url: string; }

const COMBO_LABELS: Record<string, string> = {
  "combo-kiro": "Kiro (Claude)", "combo-mimo": "MiMo v2.5 Pro",
  "combo-deepseek": "DeepSeek", "combo-freemodel": "Free Model", "combo-test-mimo": "MiMo Test",
};

const FEATURES = [
  { key: "chat", label: "Chat & Agent" }, { key: "article", label: "Generate Artikel SEO" },
  { key: "image", label: "Generate Gambar" }, { key: "analysis", label: "Analisa Lead" },
  { key: "caption", label: "Generate Caption Sosmed" },
] as const;

export default function AIEngineTab() {
  const [models, setModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [combos, setCombos] = useState<Combo[]>([]);
  const [activeCombo, setActiveCombo] = useState<string>("");
  const [switching, setSwitching] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthState>({ status: "loading", proxy_url: "" });
  const [proxyUrlInput, setProxyUrlInput] = useState<string>("");
  const [savingUrl, setSavingUrl] = useState(false);
  const [featureDefaults, setFeatureDefaults] = useState<Record<string, string>>({});
  const [savingDefaults, setSavingDefaults] = useState(false);
  const [proxies, setProxies] = useState<AIProxy[]>([]);
  const [confirmState, setConfirmState] = useState({ open: false, title: "", message: "", onConfirm: () => {} });
  const [toast, setToast] = useState<string | null>(null);

  function showToast(msg: string) { setToast(msg); setTimeout(() => setToast(null), 3000); }
  function openConfirm(title: string, message: string, onConfirm: () => void) { setConfirmState({ open: true, title, message, onConfirm }); }

  const fetchModels = useCallback(async () => {
    try { const r = await apiFetch("/api/ai-models"); if (r.ok) setModels(await r.json()); }
    finally { setLoading(false); }
  }, []);
  const fetchCombos = useCallback(async () => {
    const [combosRes, activeRes] = await Promise.all([apiFetch("/api/ai/combos"), apiFetch("/api/ai/active-combo")]);
    if (combosRes.ok) setCombos(await combosRes.json());
    if (activeRes.ok) { const d = await activeRes.json(); setActiveCombo(d.combo); if (d.proxy_url) setProxyUrlInput(d.proxy_url); }
  }, []);
  const checkHealth = useCallback(async () => {
    setHealth(h => ({ ...h, status: "loading" }));
    try {
      const res = await apiFetch("/api/ai/health");
      if (res.ok) { const d = await res.json(); setHealth(d); if (d.proxy_url) setProxyUrlInput(d.proxy_url); }
    } catch { setHealth({ status: "offline", proxy_url: "" }); }
  }, []);
  const fetchFeatureDefaults = useCallback(async () => {
    try { const r = await apiFetch("/api/ai/feature-defaults"); if (r.ok) setFeatureDefaults(await r.json()); } catch {}
  }, []);
  const fetchProxies = useCallback(async () => {
    try { const r = await apiFetch("/api/ai-proxies"); if (r.ok) setProxies(await r.json()); } catch {}
  }, []);

  useEffect(() => { fetchModels(); fetchCombos(); checkHealth(); fetchFeatureDefaults(); fetchProxies(); },
    [fetchModels, fetchCombos, checkHealth, fetchFeatureDefaults, fetchProxies]);

  async function saveProxyUrl() {
    const url = proxyUrlInput.trim();
    if (!url || !/^https?:\/\//.test(url)) { showToast("URL harus diawali http:// atau https://"); return; }
    setSavingUrl(true);
    try {
      const res = await apiFetch("/api/ai/proxy-url", { method: "POST", body: JSON.stringify({ url }) });
      if (res.ok) { const d = await res.json(); setProxyUrlInput(d.proxy_url); showToast("Proxy URL disimpan"); checkHealth(); }
      else { const e = await res.json().catch(() => ({})); showToast(e.detail || "Gagal menyimpan URL"); }
    } finally { setSavingUrl(false); }
  }

  async function selectCombo(name: string) {
    if (name === activeCombo || switching) return;
    openConfirm("Ganti Combo", `Ganti combo aktif ke "${COMBO_LABELS[name] || name}"?`, async () => {
      setSwitching(name);
      try {
        const res = await apiFetch("/api/ai/active-combo", { method: "POST", body: JSON.stringify({ combo: name }) });
        if (res.ok) { setActiveCombo(name); showToast(`Combo diubah ke ${COMBO_LABELS[name] || name}`); }
        else { const e = await res.json().catch(() => ({})); showToast(e.detail || "Gagal mengubah combo"); }
      } finally { setSwitching(null); }
    });
  }

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

      {/* AI Model Endpoint */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">AI Model Endpoint</h2>
            <p className="text-xs text-neutral-500 mt-0.5">Endpoint OpenAI-compatible — bisa router multi-model atau direct API provider</p>
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
              <span className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 text-gray-500 rounded-xl text-xs font-semibold">Mengecek...</span>
            )}
            <button onClick={checkHealth} className="p-2 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors" title="Refresh"><RefreshCw size={14} /></button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input value={proxyUrlInput} onChange={e => setProxyUrlInput(e.target.value)} placeholder="http://localhost:20128/v1" className={inputCls} />
          <button onClick={saveProxyUrl} disabled={savingUrl} className="shrink-0 px-4 py-2.5 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors disabled:opacity-50">
            {savingUrl ? "..." : "Simpan"}
          </button>
        </div>
      </div>

      {/* Active Combo */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 space-y-4">
        <div>
          <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Combo Aktif (Default)</h2>
          <p className="text-xs text-neutral-500 mt-1">Klik combo untuk mengaktifkannya. Semua AI call CRM pakai combo ini kecuali ada override per fitur.</p>
        </div>
        {combos.length === 0 ? (
          <div className="p-6 text-center text-sm text-neutral-400">Memuat combo...</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {combos.map(c => {
              const isActive = c.name === activeCombo;
              const isSwitching = switching === c.name;
              return (
                <button key={c.name} onClick={() => selectCombo(c.name)} disabled={isSwitching || isActive}
                  className={`text-left p-4 rounded-xl border-2 transition-all ${isActive ? "border-[#f5a700] bg-amber-50/50 dark:bg-amber-900/10" : "border-[var(--border-subtle)] hover:border-amber-300 hover:bg-amber-50/30 dark:hover:bg-amber-900/5"} ${isSwitching ? "opacity-60" : ""}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{COMBO_LABELS[c.name] || c.name}</p>
                      <p className="text-[11px] text-neutral-400 font-mono mt-0.5">{c.name}</p>
                    </div>
                    {isActive && <span className="shrink-0 px-2 py-0.5 bg-brand-yellow text-white text-[10px] font-bold uppercase rounded">Aktif</span>}
                    {isSwitching && <span className="shrink-0 text-[10px] text-amber-600">Switching...</span>}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Default per Fitur */}
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 space-y-4">
        <div>
          <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Default Model per Fitur</h2>
          <p className="text-xs text-neutral-500 mt-1">Override combo per fitur. Kosong = pakai combo aktif di atas.</p>
        </div>
        <div className="space-y-3">
          {FEATURES.map(f => (
            <div key={f.key} className="flex items-center gap-4">
              <label className="text-sm text-neutral-700 dark:text-neutral-300 w-48 shrink-0">{f.label}</label>
              <select value={featureDefaults[f.key] || ""} onChange={e => setFeatureDefaults(prev => ({ ...prev, [f.key]: e.target.value }))}
                className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50 transition">
                <option value="">Default (combo aktif)</option>
                {combos.map(c => <option key={c.name} value={c.name}>{COMBO_LABELS[c.name] || c.name}</option>)}
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
        models={models} loading={loading}
        onFetchModels={fetchModels} onDeleteModel={deleteModel} onSetDefault={setDefault}
        showToast={showToast}
      />
      <ProxiesSection proxies={proxies} onFetchProxies={fetchProxies} showToast={showToast} />

      <ConfirmModal
        open={confirmState.open} onClose={() => setConfirmState(s => ({ ...s, open: false }))}
        onConfirm={confirmState.onConfirm} title={confirmState.title} message={confirmState.message}
      />
    </div>
  );
}
