"use client";
import { useState } from "react";
import { Plus, Edit2, Trash2, X } from "lucide-react";
import { inputCls } from "../../../lib/inputCls";

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

const PROVIDER_OPTIONS = [
  { value: "custom", label: "9router (OpenAI-compatible)" },
];

const PROXY_FEATURES = [
  { key: "", label: "Fallback (semua fitur)" },
  { key: "article", label: "Artikel SEO" },
  { key: "analysis", label: "Analisa Lead" },
];

interface ProxiesSectionProps {
  proxies: AIProxy[];
  routerModels: RouterModel[];
  onFetchProxies: () => void;
  showToast: (msg: string) => void;
  onConfirmDelete?: (id: string, name: string) => void;
}

export default function ProxiesSection({ proxies, routerModels, onFetchProxies, showToast, onConfirmDelete }: ProxiesSectionProps) {
  const [proxyModal, setProxyModal] = useState(false);
  const [editingProxy, setEditingProxy] = useState<AIProxy | null>(null);
  const [proxyForm, setProxyForm] = useState({ name: "", base_url: "http://9router.kantorteman.my.id/v1", api_key: "", model: "combo-genflow", feature: "", provider: "custom" });
  const [activatingProxy, setActivatingProxy] = useState<string | null>(null);
  const comboModels = routerModels.filter((model) => model.type === "combo" || model.id.startsWith("combo-"));
  const regularModels = routerModels.filter((model) => !comboModels.includes(model));

  function openProxyModal(p: AIProxy | null) {
    setEditingProxy(p);
    setProxyForm(p ? { name: p.name, base_url: p.base_url, api_key: "", model: p.model, feature: p.feature || "", provider: "custom" } : { name: "9router", base_url: "http://9router.kantorteman.my.id/v1", api_key: "", model: comboModels[0]?.id || "combo-genflow", feature: "", provider: "custom" });
    setProxyModal(true);
  }

  async function saveProxy() {
    const { apiFetch } = await import("../../../lib/api");
    if (!proxyForm.name || !proxyForm.base_url || !proxyForm.model) { showToast("Nama, Base URL, dan model wajib diisi"); return; }
    const payload: Record<string, unknown> = { name: proxyForm.name, base_url: proxyForm.base_url, model: proxyForm.model, feature: proxyForm.feature || null, provider: proxyForm.provider };
    if (proxyForm.api_key) payload.api_key = proxyForm.api_key;
    const res = editingProxy
      ? await apiFetch(`/api/ai-proxies/${editingProxy.id}`, { method: "PUT", body: JSON.stringify(payload) })
      : await apiFetch("/api/ai-proxies", { method: "POST", body: JSON.stringify(payload) });
    if (res.ok) { setProxyModal(false); onFetchProxies(); showToast(editingProxy ? "Proxy diupdate" : "Proxy ditambahkan"); }
    else showToast("Gagal simpan proxy");
  }

  async function handleDeleteProxy(id: string) {
    const p = proxies.find(x => x.id === id);
    if (onConfirmDelete) { onConfirmDelete(id, p?.name || "ini"); return; }
    // Fallback if no confirmation handler provided
    if (confirm(`Hapus proxy "${p?.name || id}"?`)) {
      const { apiFetch } = await import("../../../lib/api");
      const res = await apiFetch(`/api/ai-proxies/${id}`, { method: "DELETE" });
      if (res.ok) { onFetchProxies(); showToast("Proxy dihapus"); }
    }
  }

  async function activateProxy(id: string) {
    const { apiFetch } = await import("../../../lib/api");
    setActivatingProxy(id);
    try {
      const res = await apiFetch(`/api/ai-proxies/${id}/activate`, { method: "POST" });
      if (res.ok) { onFetchProxies(); showToast("Proxy diaktifkan"); }
    } finally { setActivatingProxy(null); }
  }

  function featureLabel(f: string | null) {
    return PROXY_FEATURES.find(x => x.key === (f || ""))?.label || f || "Fallback";
  }

  return (
    <>
      <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Provider AI ({proxies.length})</h2>
            <p className="text-xs text-neutral-500 mt-0.5">Semua AI KantorTeman diarahkan ke 9router OpenAI-compatible.</p>
          </div>
          <button onClick={() => openProxyModal(null)} className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs font-semibold rounded-xl transition-colors">
            <Plus size={14} /> Tambah
          </button>
        </div>

        {proxies.length === 0 ? (
          <p className="text-sm text-neutral-400 text-center py-4">Belum ada provider. Tambahkan koneksi 9router terlebih dulu.</p>
        ) : (
          <div className="space-y-2">
            {proxies.map(p => (
              <div key={p.id} className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-colors ${p.is_active ? "border-emerald-300 dark:border-emerald-700 bg-emerald-50/50 dark:bg-emerald-900/10" : "border-[var(--border-default)]"}`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{p.name}</span>
                    {p.is_active && <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">AKTIF</span>}
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-500">{featureLabel(p.feature)}</span>
                  </div>
                  <p className="text-xs text-neutral-400 truncate mt-0.5">{p.base_url} • {p.model || "default"}</p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {!p.is_active && (
                    <button onClick={() => activateProxy(p.id)} disabled={activatingProxy === p.id}
                      className="px-2.5 py-1.5 text-[11px] font-semibold bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 rounded-lg hover:bg-emerald-200 dark:hover:bg-emerald-900/50 transition-colors disabled:opacity-50">
                      {activatingProxy === p.id ? "..." : "Aktifkan"}
                    </button>
                  )}
                  <button onClick={() => openProxyModal(p)} className="p-1.5 text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 transition-colors"><Edit2 size={14} /></button>
                  <button onClick={() => handleDeleteProxy(p.id)} className="p-1.5 text-neutral-400 hover:text-red-500 transition-colors"><Trash2 size={14} /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Proxy Modal */}
      {proxyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setProxyModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-neutral-900 dark:text-neutral-50">{editingProxy ? "Edit Provider AI" : "Tambah Provider AI"}</h3>
              <button onClick={() => setProxyModal(false)} className="text-neutral-400 hover:text-neutral-700"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <input value={proxyForm.name} onChange={e => setProxyForm({...proxyForm, name: e.target.value})} placeholder="Nama provider" className={inputCls} />
              <select value={proxyForm.provider} onChange={e => setProxyForm({...proxyForm, provider: e.target.value})} className={inputCls}>
                {PROVIDER_OPTIONS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
              <input value={proxyForm.base_url} onChange={e => setProxyForm({...proxyForm, base_url: e.target.value})} placeholder="http://9router.kantorteman.my.id/v1" className={inputCls} />
              <input value={proxyForm.api_key} onChange={e => setProxyForm({...proxyForm, api_key: e.target.value})} placeholder={editingProxy ? "API Key 9router (kosongkan jika tidak berubah)" : "API Key 9router (opsional jika VPS lokal tidak butuh key)"} type="password" className={inputCls} />
              {routerModels.length > 0 ? (
                <select value={proxyForm.model} onChange={e => setProxyForm({...proxyForm, model: e.target.value})} className={inputCls}>
                  {comboModels.length > 0 && (
                    <optgroup label="Combos">
                      {comboModels.map(model => <option key={model.id} value={model.id}>{model.id}</option>)}
                    </optgroup>
                  )}
                  {regularModels.length > 0 && (
                    <optgroup label="Models">
                      {regularModels.map(model => <option key={model.id} value={model.id}>{model.id}</option>)}
                    </optgroup>
                  )}
                </select>
              ) : (
                <input value={proxyForm.model} onChange={e => setProxyForm({...proxyForm, model: e.target.value})} placeholder="combo-genflow" className={inputCls} />
              )}
              <select value={proxyForm.feature} onChange={e => setProxyForm({...proxyForm, feature: e.target.value})} className={inputCls}>
                {PROXY_FEATURES.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setProxyModal(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={saveProxy} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
