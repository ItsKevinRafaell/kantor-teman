"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import { formatRupiahInput, cleanRupiahInput } from "../../../utils/formatter";
import { Plus, Trash2, ExternalLink, TrendingUp, Target, DollarSign } from "lucide-react";

interface Campaign {
  id: string;
  name: string;
  target_audience: string;
  budget: number;
  drive_link: string | null;
  leads_count: number;
  conversions_count: number;
  status: string;
  created_at: string;
  cac: number | null;
  cost_per_lead: number | null;
}

function formatRupiah(num: number): string {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0 }).format(num);
}

const STATUS_COLORS: Record<string, string> = {
  PLANNING: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  ACTIVE: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  COMPLETED: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400",
};

export default function AdsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ name: "", target_audience: "", budget: 0, drive_link: "", status: "PLANNING" });
  const [saving, setSaving] = useState(false);
  const [editingField, setEditingField] = useState<{ id: string; field: string } | null>(null);
  const [editValue, setEditValue] = useState("");

  const fetchCampaigns = useCallback(async () => {
    try {
      const res = await apiFetch("/api/ads/campaigns");
      if (res.ok) setCampaigns(await res.json());
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchCampaigns(); }, [fetchCampaigns]);

  async function createCampaign() {
    if (!form.name || !form.target_audience || !form.budget) return;
    setSaving(true);
    try {
      const res = await apiFetch("/api/ads/campaigns", {
        method: "POST",
        body: JSON.stringify(form),
      });
      if (res.ok) {
        setShowModal(false);
        setForm({ name: "", target_audience: "", budget: 0, drive_link: "", status: "PLANNING" });
        fetchCampaigns();
      }
    } finally { setSaving(false); }
  }

  async function updateCampaign(id: string, patch: Record<string, unknown>) {
    const res = await apiFetch(`/api/ads/campaigns/${id}`, {
      method: "PUT",
      body: JSON.stringify(patch),
    });
    if (res.ok) fetchCampaigns();
  }

  async function deleteCampaign(id: string) {
    const res = await apiFetch(`/api/ads/campaigns/${id}`, { method: "DELETE" });
    if (res.ok) setCampaigns(prev => prev.filter(c => c.id !== id));
  }

  function startEdit(id: string, field: string, currentValue: number) {
    setEditingField({ id, field });
    setEditValue(String(currentValue));
  }

  function commitEdit() {
    if (!editingField) return;
    const val = parseInt(editValue) || 0;
    updateCampaign(editingField.id, { [editingField.field]: val });
    setEditingField(null);
  }

  const totalBudget = campaigns.reduce((sum, c) => sum + c.budget, 0);
  const totalLeads = campaigns.reduce((sum, c) => sum + c.leads_count, 0);
  const totalConversions = campaigns.reduce((sum, c) => sum + c.conversions_count, 0);
  const avgCac = totalConversions > 0 ? totalBudget / totalConversions : null;

  if (loading) {
    return (
      <div className="max-w-6xl space-y-6">
        <div className="h-8 bg-neutral-100 dark:bg-neutral-800 rounded w-48 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-28 bg-neutral-100 dark:bg-neutral-800 rounded-2xl animate-pulse" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Ads Tracking Center</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">Rencanakan & lacak performa iklan</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-1.5 text-sm text-white">
          <Plus size={16} /> Buat Rencana Iklan
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
              <DollarSign size={18} className="text-blue-600 dark:text-blue-400" />
            </div>
            <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase">Total Budget</span>
          </div>
          <p className="text-xl font-bold text-neutral-900 dark:text-neutral-50">{formatRupiah(totalBudget)}</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-9 h-9 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center">
              <Target size={18} className="text-emerald-600 dark:text-emerald-400" />
            </div>
            <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase">Total Leads</span>
          </div>
          <p className="text-xl font-bold text-neutral-900 dark:text-neutral-50">{totalLeads}</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-9 h-9 rounded-xl bg-violet-50 dark:bg-violet-900/20 flex items-center justify-center">
              <TrendingUp size={18} className="text-violet-600 dark:text-violet-400" />
            </div>
            <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase">Konversi</span>
          </div>
          <p className="text-xl font-bold text-neutral-900 dark:text-neutral-50">{totalConversions}</p>
        </div>
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-9 h-9 rounded-xl bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center">
              <DollarSign size={18} className="text-amber-600 dark:text-amber-400" />
            </div>
            <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase">Avg. CAC</span>
          </div>
          <p className="text-xl font-bold text-neutral-900 dark:text-neutral-50">{avgCac ? formatRupiah(avgCac) : "—"}</p>
        </div>
      </div>

      {/* Campaigns Table */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-default)]">
          <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Daftar Campaign</h2>
        </div>

        {campaigns.length === 0 ? (
          <div className="text-center py-16 text-neutral-400 text-sm">Belum ada campaign. Buat rencana iklan pertama.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 dark:bg-neutral-800 border-b border-[var(--border-default)]">
                <tr>
                  {["Nama Campaign", "Target", "Budget", "Status", "Leads", "Konversi", "CAC", "Cost/Lead", "Aksi"].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {campaigns.map(c => (
                  <tr key={c.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-neutral-800 dark:text-neutral-200">{c.name}</div>
                      {c.drive_link && (
                        <a href={c.drive_link} target="_blank" rel="noopener noreferrer" className="text-[11px] text-blue-500 hover:underline flex items-center gap-0.5 mt-0.5">
                          Materi <ExternalLink size={10} />
                        </a>
                      )}
                    </td>
                    <td className="px-4 py-3 text-neutral-600 dark:text-neutral-400">{c.target_audience}</td>
                    <td className="px-4 py-3 font-semibold text-neutral-800 dark:text-neutral-200">{formatRupiah(c.budget)}</td>
                    <td className="px-4 py-3">
                      <select
                        value={c.status}
                        onChange={e => updateCampaign(c.id, { status: e.target.value })}
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border-0 cursor-pointer ${STATUS_COLORS[c.status] || STATUS_COLORS.PLANNING}`}
                      >
                        <option value="PLANNING">PLANNING</option>
                        <option value="ACTIVE">ACTIVE</option>
                        <option value="COMPLETED">COMPLETED</option>
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      {editingField?.id === c.id && editingField.field === "leads_count" ? (
                        <input
                          autoFocus
                          type="number"
                          value={editValue}
                          onChange={e => setEditValue(e.target.value)}
                          onBlur={commitEdit}
                          onKeyDown={e => { if (e.key === "Enter") commitEdit(); if (e.key === "Escape") setEditingField(null); }}
                          className="w-16 px-2 py-1 text-sm border border-brand-yellow rounded bg-transparent outline-none"
                        />
                      ) : (
                        <button onClick={() => startEdit(c.id, "leads_count", c.leads_count)}
                          className="px-2 py-1 text-sm font-semibold text-neutral-800 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded transition-colors">
                          {c.leads_count}
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {editingField?.id === c.id && editingField.field === "conversions_count" ? (
                        <input
                          autoFocus
                          type="number"
                          value={editValue}
                          onChange={e => setEditValue(e.target.value)}
                          onBlur={commitEdit}
                          onKeyDown={e => { if (e.key === "Enter") commitEdit(); if (e.key === "Escape") setEditingField(null); }}
                          className="w-16 px-2 py-1 text-sm border border-brand-yellow rounded bg-transparent outline-none"
                        />
                      ) : (
                        <button onClick={() => startEdit(c.id, "conversions_count", c.conversions_count)}
                          className="px-2 py-1 text-sm font-semibold text-neutral-800 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded transition-colors">
                          {c.conversions_count}
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm font-semibold text-neutral-800 dark:text-neutral-200">
                      {c.cac ? formatRupiah(c.cac) : "—"}
                    </td>
                    <td className="px-4 py-3 text-sm text-neutral-600 dark:text-neutral-400">
                      {c.cost_per_lead ? formatRupiah(c.cost_per_lead) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={() => deleteCampaign(c.id)} className="p-1.5 text-neutral-400 hover:text-red-500 rounded-lg transition-colors">
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Campaign Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-modal border border-[var(--border-default)] w-full max-w-md p-6 space-y-4 animate-slide-up">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Buat Rencana Iklan</h3>
              <button onClick={() => setShowModal(false)} className="p-1 text-neutral-400 hover:text-neutral-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Nama Campaign</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className="input-field" placeholder="Meta Ads - Jasa Web Design" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Target Audience</label>
                <input value={form.target_audience} onChange={e => setForm(f => ({ ...f, target_audience: e.target.value }))} className="input-field" placeholder="UMKM Surabaya, 25-45 tahun" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Budget (Rp)</label>
                <input
                  type="text"
                  value={form.budget ? formatRupiahInput(form.budget) : ""}
                  onChange={e => setForm(f => ({ ...f, budget: cleanRupiahInput(e.target.value) }))}
                  className="input-field"
                  placeholder="Rp 0"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Link Drive Materi (opsional)</label>
                <input value={form.drive_link} onChange={e => setForm(f => ({ ...f, drive_link: e.target.value }))} className="input-field" placeholder="https://drive.google.com/..." />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Status Awal</label>
                <select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))} className="input-field">
                  <option value="PLANNING">Planning (belum potong saldo)</option>
                  <option value="ACTIVE">Active (otomatis potong saldo)</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowModal(false)} className="btn-ghost">Batal</button>
              <button onClick={createCampaign} disabled={saving} className="btn-primary text-white">
                {saving ? "Menyimpan..." : "Simpan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
