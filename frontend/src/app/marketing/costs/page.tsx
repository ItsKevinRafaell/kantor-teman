"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import { formatRupiahInput, cleanRupiahInput } from "../../../utils/formatter";
import { Zap, Brain, MessageSquare, TrendingUp, Plus } from "lucide-react";

interface ProviderData {
  id: string;
  provider_name: string;
  remaining_quota: number;
  price_per_unit_idr: number;
  price_input_token_usd: number;
  price_output_token_usd: number;
  estimated_balance_idr: number;
}

interface CampaignCost {
  id: string;
  name: string;
  created_at: string;
  sent_count: number;
  total_operational_cost_idr: number;
  converted_clients_count: number;
  cpa: number | null;
  roi: number | null;
  status: string;
}

function formatRupiah(num: number): string {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0 }).format(num);
}

function getProviderIcon(id: string) {
  if (id === "FONNTE") return <MessageSquare size={18} className="text-emerald-600 dark:text-emerald-400" />;
  return <Brain size={18} className="text-violet-600 dark:text-violet-400" />;
}

function getProviderColor(id: string) {
  if (id === "FONNTE") return "bg-emerald-50 dark:bg-emerald-900/20";
  return "bg-violet-50 dark:bg-violet-900/20";
}

export default function CostsPage() {
  const [providers, setProviders] = useState<ProviderData[]>([]);
  const [campaigns, setCampaigns] = useState<CampaignCost[]>([]);
  const [loading, setLoading] = useState(true);
  const [topUpModal, setTopUpModal] = useState<{ open: boolean; provider: ProviderData | null }>({ open: false, provider: null });
  const [topUpValue, setTopUpValue] = useState("");
  const [topUpPackage, setTopUpPackage] = useState("10000");
  const [topUpConfirmed, setTopUpConfirmed] = useState(false);
  const [resetModal, setResetModal] = useState<{ open: boolean; provider: ProviderData | null }>({ open: false, provider: null });
  const [resetConfirmed, setResetConfirmed] = useState(false);
  const [editingConversion, setEditingConversion] = useState<{ id: string } | null>(null);
  const [conversionValue, setConversionValue] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const res = await apiFetch("/api/finance/outreach-costs");
      if (res.ok) {
        const data = await res.json();
        setProviders(data.providers);
        setCampaigns(data.campaigns);
      }
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  async function submitTopUp() {
    if (!topUpModal.provider || !topUpValue) return;
    const newQuota = parseFloat(topUpValue);
    if (isNaN(newQuota)) return;

    if (topUpModal.provider.id === "FONNTE") {
      const packagePrices: Record<string, number> = { "1000": 25, "10000": 6.6, "25000": 4.4 };
      const pricePerUnit = packagePrices[topUpPackage] || 6.6;
      await apiFetch(`/api/provider-configs/${topUpModal.provider.id}`, {
        method: "PUT",
        body: JSON.stringify({ remaining_quota: newQuota, price_per_unit_idr: pricePerUnit }),
      });
    } else {
      await apiFetch(`/api/provider-configs/${topUpModal.provider.id}`, {
        method: "PUT",
        body: JSON.stringify({ remaining_quota: newQuota }),
      });
    }

    setTopUpModal({ open: false, provider: null });
    setTopUpValue("");
    setTopUpConfirmed(false);
    fetchData();
  }

  async function submitReset() {
    if (!resetModal.provider) return;
    await apiFetch(`/api/provider-configs/${resetModal.provider.id}`, {
      method: "PUT",
      body: JSON.stringify({ remaining_quota: 0 }),
    });
    setResetModal({ open: false, provider: null });
    setResetConfirmed(false);
    fetchData();
  }

  async function submitConversion() {
    if (!editingConversion || !conversionValue) return;
    await apiFetch(`/api/blast-campaigns/${editingConversion.id}/conversions`, {
      method: "PUT",
      body: JSON.stringify({ converted_clients_count: parseInt(conversionValue) || 0 }),
    });
    setEditingConversion(null);
    setConversionValue("");
    fetchData();
  }

  if (loading) {
    return (
      <div className="max-w-6xl space-y-6">
        <div className="h-8 bg-neutral-100 dark:bg-neutral-800 rounded w-48 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-36 bg-neutral-100 dark:bg-neutral-800 rounded-2xl animate-pulse" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Pusat Biaya & Kuota</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">Pantau sisa kuota provider dan biaya operasional per kampanye</p>
      </div>

      {/* Blok Atas: Provider Quota Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {providers.filter(p => p.id === "FONNTE").map(p => {
          const isFonnte = p.id === "FONNTE";
          const isAI = !isFonnte;

          return (
            <div key={p.id} className="card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${getProviderColor(p.id)}`}>
                    {getProviderIcon(p.id)}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase">{p.provider_name}</p>
                  </div>
                </div>
                {isFonnte && (
                  <div className="flex items-center gap-1">
                    <button onClick={() => { setTopUpModal({ open: true, provider: p }); setTopUpPackage("10000"); setTopUpValue(String(p.remaining_quota)); setTopUpConfirmed(false); }}
                      className="p-1.5 text-neutral-400 hover:text-brand-yellow rounded-lg transition-colors" title="Update Kuota">
                      <Plus size={14} />
                    </button>
                    <button onClick={() => { setResetModal({ open: true, provider: p }); setResetConfirmed(false); }}
                      className="p-1.5 text-neutral-400 hover:text-red-500 rounded-lg transition-colors" title="Reset Kuota">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                    </button>
                  </div>
                )}
                {isAI && (
                  <div className="flex items-center gap-1">
                    <button onClick={() => { setTopUpModal({ open: true, provider: p }); setTopUpValue(String(p.remaining_quota)); setTopUpConfirmed(false); }}
                      className="p-1.5 text-neutral-400 hover:text-brand-yellow rounded-lg transition-colors" title="Edit Biaya">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                    </button>
                    <button onClick={() => { setResetModal({ open: true, provider: p }); setResetConfirmed(false); }}
                      className="p-1.5 text-neutral-400 hover:text-red-500 rounded-lg transition-colors" title="Reset Biaya">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                    </button>
                  </div>
                )}
              </div>

              {isFonnte ? (
                <div>
                  <p className="text-lg font-bold text-neutral-900 dark:text-neutral-50">
                    {p.remaining_quota.toLocaleString("id-ID")} pesan
                  </p>
                  <p className="text-xs text-neutral-400 mt-0.5">
                    Tarif: {formatRupiah(p.price_per_unit_idr)}/pesan
                  </p>
                  {/* Progress bar */}
                  <div className="w-full h-2 bg-neutral-100 dark:bg-neutral-800 rounded-full overflow-hidden mt-2">
                    <div
                      className={`h-full rounded-full transition-all ${p.remaining_quota < 2000 ? "bg-red-500" : "bg-emerald-500"}`}
                      style={{ width: `${Math.min(100, (p.remaining_quota / 10000) * 100)}%` }}
                    />
                  </div>
                  <p className={`text-[10px] font-semibold mt-1 ${p.remaining_quota < 2000 ? "text-red-500" : "text-neutral-400"}`}>
                    {p.remaining_quota < 2000 ? "Kuota hampir habis!" : `${((p.remaining_quota / 10000) * 100).toFixed(0)}% tersisa`}
                  </p>
                </div>
              ) : (
                <div>
                  <p className="text-lg font-bold text-neutral-900 dark:text-neutral-50">
                    {formatRupiah(p.remaining_quota)}
                  </p>
                  <p className="text-xs text-neutral-400 mt-0.5">
                    Estimasi total biaya terpakai
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Blok Bawah: Campaign Cost Log */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Log Biaya Per Kampanye</h2>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">Rincian biaya operasional, CPA, dan ROI per blast</p>
          </div>
        </div>

        {campaigns.length === 0 ? (
          <div className="text-center py-16 text-neutral-400 text-sm">Belum ada data kampanye.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 dark:bg-neutral-800 border-b border-[var(--border-default)]">
                <tr>
                  {["Nama Kampanye", "Tanggal", "Pesan Terkirim", "Total Biaya", "Closing", "CPA", "ROI", "Status"].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {campaigns.map(c => (
                  <tr key={c.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                    <td className="px-4 py-3 font-semibold text-neutral-800 dark:text-neutral-200">{c.name}</td>
                    <td className="px-4 py-3 text-neutral-500 text-xs">
                      {new Date(c.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}
                    </td>
                    <td className="px-4 py-3 text-neutral-800 dark:text-neutral-200">{c.sent_count}</td>
                    <td className="px-4 py-3 font-semibold text-neutral-800 dark:text-neutral-200">{formatRupiah(c.total_operational_cost_idr)}</td>
                    <td className="px-4 py-3">
                      {editingConversion?.id === c.id ? (
                        <input
                          autoFocus
                          type="number"
                          value={conversionValue}
                          onChange={e => setConversionValue(e.target.value)}
                          onBlur={submitConversion}
                          onKeyDown={e => { if (e.key === "Enter") submitConversion(); if (e.key === "Escape") setEditingConversion(null); }}
                          className="w-16 px-2 py-1 text-sm border border-brand-yellow rounded bg-transparent outline-none"
                        />
                      ) : (
                        <button onClick={() => { setEditingConversion({ id: c.id }); setConversionValue(String(c.converted_clients_count)); }}
                          className="px-2 py-1 text-sm font-semibold text-neutral-800 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded transition-colors">
                          {c.converted_clients_count}
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3 text-neutral-800 dark:text-neutral-200">
                      {c.cpa ? formatRupiah(c.cpa) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      {c.roi !== null ? (
                        <span className={`font-bold ${c.roi > 100 ? "text-emerald-600 dark:text-emerald-400" : c.roi > 0 ? "text-emerald-500" : "text-red-500"}`}>
                          {c.roi.toFixed(1)}%
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${c.status === "SUCCESS" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : c.status === "PROCESSING" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" : c.status === "FAILED" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"}`}>
                        {c.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Top Up Modal */}
      {topUpModal.open && topUpModal.provider && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setTopUpModal({ open: false, provider: null })} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-modal border border-[var(--border-default)] w-full max-w-sm p-6 space-y-4 animate-slide-up">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">
                {topUpModal.provider.id === "FONNTE" ? "Update Kuota Fonnte" : `Edit Biaya ${topUpModal.provider.provider_name}`}
              </h3>
              <button onClick={() => setTopUpModal({ open: false, provider: null })} className="p-1 text-neutral-400 hover:text-neutral-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>

            {topUpModal.provider.id === "FONNTE" ? (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Pilih Paket</label>
                  <select value={topUpPackage} onChange={e => { setTopUpPackage(e.target.value); setTopUpValue(e.target.value); }}
                    className="input-field">
                    <option value="1000">1.000 pesan — Rp 25.000 (Rp 25/pesan)</option>
                    <option value="10000">10.000 pesan — Rp 66.000 (Rp 6,6/pesan)</option>
                    <option value="25000">25.000 pesan — Rp 110.000 (Rp 4,4/pesan)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Jumlah Kuota (pesan)</label>
                  <input type="number" value={topUpValue} onChange={e => setTopUpValue(e.target.value)} className="input-field" placeholder="Masukkan jumlah kuota..." />
                  <p className="text-[11px] text-neutral-400 mt-1">
                    Tarif otomatis: Rp {topUpPackage === "1000" ? "25" : topUpPackage === "10000" ? "6,6" : "4,4"}/pesan
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Estimasi Biaya Terpakai (Rp)</label>
                  <input type="number" value={topUpValue} onChange={e => setTopUpValue(e.target.value)} className="input-field" placeholder="0" />
                  <p className="text-[11px] text-neutral-400 mt-1">Set ke 0 untuk reset hitungan.</p>
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <label className="flex items-center gap-2 mr-auto cursor-pointer">
                <input type="checkbox" checked={topUpConfirmed} onChange={e => setTopUpConfirmed(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-amber-500 focus:ring-amber-400" />
                <span className="text-xs text-neutral-500 dark:text-neutral-400">Saya yakin ingin mengubah data ini</span>
              </label>
              <button onClick={() => setTopUpModal({ open: false, provider: null })} className="btn-ghost">Batal</button>
              <button onClick={submitTopUp} disabled={!topUpConfirmed} className="btn-primary disabled:opacity-50">Simpan</button>
            </div>
          </div>
        </div>
      )}

      {/* Reset Confirmation Modal */}
      {resetModal.open && resetModal.provider && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setResetModal({ open: false, provider: null })} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-modal border border-[var(--border-default)] w-full max-w-sm p-6 space-y-4 animate-slide-up">
            <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Reset {resetModal.provider.provider_name}</h3>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Apakah Anda yakin ingin mereset {resetModal.provider.id === "FONNTE" ? "kuota" : "estimasi biaya"} <strong>{resetModal.provider.provider_name}</strong> ke 0? Tindakan ini tidak bisa dibatalkan.
            </p>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={resetConfirmed} onChange={e => setResetConfirmed(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-red-500 focus:ring-red-400" />
              <span className="text-xs text-neutral-500 dark:text-neutral-400">Saya yakin ingin mereset data ini</span>
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setResetModal({ open: false, provider: null })} className="btn-ghost">Batal</button>
              <button onClick={submitReset} disabled={!resetConfirmed} className="btn-danger disabled:opacity-50">Reset</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
