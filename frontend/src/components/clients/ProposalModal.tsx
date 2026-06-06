"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "../../lib/api";
import { formatRupiah, formatRupiahInput, cleanRupiahInput } from "../../utils/formatter";
import { inputClsLarge } from "../../lib/inputCls";
import { Search, X } from "lucide-react";
import type { Contact, ProductItem, ServiceItem, TimelinePhase, TimelineTemplate } from "../../types";

interface SelectedService { id: string; name: string; price: number; features: string; }

interface ProposalModalProps {
  contact: Contact | null;
  open: boolean;
  onClose: () => void;
  onSuccess: (url: string) => void;
  setToast: (toast: { message: string; type: "success" | "error" | "info" } | null) => void;
  /** When true, shows client search step before the proposal form */
  searchMode?: boolean;
  /** Contacts list for search mode */
  contacts?: Contact[];
}

export default function ProposalModal({ contact: initialContact, open, onClose, onSuccess, setToast, searchMode, contacts = [] }: ProposalModalProps) {
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [selectedServices, setSelectedServices] = useState<SelectedService[]>([]);
  const [additionalOptions, setAdditionalOptions] = useState("");
  const [timelinePhases, setTimelinePhases] = useState<TimelinePhase[]>([]);
  const [timelineTemplates, setTimelineTemplates] = useState<TimelineTemplate[]>([]);
  const [timelineDropdownOpen, setTimelineDropdownOpen] = useState(false);
  const [roiEnabled, setRoiEnabled] = useState(true);
  const [retainerPeriod, setRetainerPeriod] = useState(0);
  const [saving, setSaving] = useState(false);
  const [unbilledTotal, setUnbilledTotal] = useState(0);

  // Search mode state
  const [step, setStep] = useState<"search" | "form">("form");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);

  // Effective contact (from search or prop)
  const contact = searchMode && !initialContact ? selectedContact : initialContact;

  useEffect(() => {
    if (!open) return;
    Promise.all([
      apiFetch("/api/settings/services").then(r => r.ok ? r.json() : []),
      apiFetch("/api/products?active_only=true").then(r => r.ok ? r.json() : []),
      apiFetch("/api/timeline-templates").then(r => r.ok ? r.json() : []),
    ]).then(([s, p, t]) => {
      setServices(s);
      setProducts(p);
      setTimelineTemplates(t);
    }).catch(() => {});
  }, [open]);

  useEffect(() => {
    if (!open) return;
    if (contact) {
      apiFetch(`/api/finance/client/${contact.id}/unbilled`)
        .then(r => r.ok ? r.json() : { unbilled_total: 0, count: 0 })
        .then(d => setUnbilledTotal(d.unbilled_total))
        .catch(() => setUnbilledTotal(0));
    }
  }, [open, contact]);

  // Reset when modal opens
  useEffect(() => {
    if (open) {
      setStep(searchMode && !initialContact ? "search" : "form");
      setSelectedContact(null);
      setSearchQuery("");
      setSelectedServices([]);
      setAdditionalOptions("");
      setTimelinePhases([]);
      setRoiEnabled(true);
      setRetainerPeriod(0);
      setUnbilledTotal(0);
    }
  }, [open, searchMode, initialContact]);

  function toggleService(serviceId: string) {
    const existing = selectedServices.find(s => s.id === serviceId);
    if (existing) {
      setSelectedServices(prev => prev.filter(s => s.id !== serviceId));
    } else {
      const svc = services.find(s => s.id === serviceId);
      if (svc) setSelectedServices(prev => [...prev, { id: svc.id, name: svc.name, price: svc.default_price, features: svc.default_features.join("\n") }]);
    }
  }

  function toggleProduct(productId: string) {
    const existing = selectedServices.find(s => s.id === productId);
    if (existing) {
      setSelectedServices(prev => prev.filter(s => s.id !== productId));
    } else {
      const prod = products.find(p => p.id === productId);
      if (prod) setSelectedServices(prev => [...prev, { id: prod.id, name: prod.name, price: prod.base_price, features: prod.features.join("\n") }]);
    }
  }

  function updateSelectedService(id: string, field: "price" | "features", value: string) {
    setSelectedServices(prev => prev.map(s => s.id === id ? { ...s, [field]: field === "price" ? Number(value) || 0 : value } : s));
  }

  const grandTotal = selectedServices.reduce((sum, s) => sum + (typeof s.price === "number" ? s.price : 0), 0);

  async function handleSubmit() {
    if (!contact || selectedServices.length === 0) return;
    setSaving(true);
    try {
      const servicesPayload = selectedServices.map(s => ({
        name: s.name,
        price: s.price,
        features: s.features.split(/[\n,]+/).map((f: string) => f.trim()).filter(Boolean),
      }));
      const res = await apiFetch("/api/proposals", {
        method: "POST",
        body: JSON.stringify({
          lead_id: contact.id,
          source: "contact",
          services: servicesPayload,
          additional_options: additionalOptions || null,
          timeline_data: timelinePhases.length > 0 ? timelinePhases : null,
          roi_data: { enabled: roiEnabled, retainer_period: retainerPeriod },
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const url = `${window.location.origin}/proposal/${data.id}`;
      setSelectedServices([]);
      setAdditionalOptions("");
      setTimelinePhases([]);
      onSuccess(url);
      onClose();
    } catch {
      setToast({ message: "Gagal membuat proposal.", type: "error" });
    } finally {
      setSaving(false);
    }
  }

  if (!open) return null;

  // ─── Search step (search mode only) ─────────────────────────────────────────
  if (searchMode && step === "search") {
    const filtered = contacts.filter(c =>
      !searchQuery ||
      c.business_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.owner_name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.phone_number.includes(searchQuery)
    );

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
        <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md max-h-[80vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border-default)]">
            <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Pilih Klien</h3>
            <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600">
              <X size={18} />
            </button>
          </div>

          {/* Search */}
          <div className="px-5 py-3 border-b border-[var(--border-default)]">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Cari nama bisnis, owner, atau WA..."
                autoFocus
                className="w-full pl-9 pr-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50 transition"
              />
            </div>
          </div>

          {/* Client list */}
          <div className="flex-1 overflow-y-auto divide-y divide-[var(--border-subtle)]">
            {filtered.length === 0 ? (
              <div className="text-center py-12 text-sm text-neutral-400">
                {searchQuery ? "Tidak ada klien yang cocok." : "Belum ada klien."}
              </div>
            ) : (
              filtered.slice(0, 20).map(c => (
                <button
                  key={c.id}
                  onClick={() => {
                    setSelectedContact(c);
                    setStep("form");
                  }}
                  className="w-full text-left px-5 py-3.5 hover:bg-[var(--bg-surface-hover)] transition-colors"
                >
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{c.business_name}</p>
                  <p className="text-xs text-neutral-500 mt-0.5">
                    {[c.owner_name, `+${c.phone_number}`].filter(Boolean).join(" · ")}
                  </p>
                </button>
              ))
            )}
          </div>

          <div className="px-5 py-3 border-t border-[var(--border-default)] text-center">
            <button onClick={onClose} className="text-xs text-neutral-400 hover:text-neutral-600">Batal</button>
          </div>
        </div>
      </div>
    );
  }

  if (!contact) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-2xl p-6 space-y-4 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">
            {searchMode ? `Proposal — ${contact.business_name}` : "Buat Proposal"}
          </h3>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>

        {searchMode && (
          <button onClick={() => { setStep("search"); setSelectedServices([]); }}
            className="text-xs text-neutral-400 hover:text-amber-600 flex items-center gap-1">
            ← Ganti klien
          </button>
        )}

        <p className="text-xs text-neutral-500 dark:text-neutral-400">Proposal untuk: <span className="font-semibold text-gray-700 dark:text-neutral-50">{contact.business_name}</span></p>

        {unbilledTotal > 0 && (
          <div className="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-xl">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-600 dark:text-amber-400 mt-0.5 shrink-0"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
            <div>
              <p className="text-xs font-semibold text-amber-800 dark:text-amber-300">Peringatan: Ada dana talangan {formatRupiah(unbilledTotal)} yang belum ditagihkan!</p>
            </div>
          </div>
        )}

        {/* Service selection */}
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Pilih Layanan (Multi-Select)</label>
          <div className="border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-[var(--bg-surface)] p-2 space-y-1 max-h-44 overflow-y-auto">
            {products.length > 0 && <p className="text-[10px] text-gray-400 uppercase tracking-wide px-2 pt-1 font-semibold">Katalog Produk</p>}
            {products.map((prod) => {
              const isSelected = selectedServices.some(s => s.id === prod.id);
              return (
                <label key={prod.id} className={`flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors ${isSelected ? "bg-brand-yellow/10" : "hover:bg-gray-100 dark:hover:bg-gray-800"}`}>
                  <input type="checkbox" checked={isSelected} onChange={() => toggleProduct(prod.id)} className="w-3.5 h-3.5 rounded border-gray-300 text-brand-yellow" />
                  <span className="text-xs text-gray-700 dark:text-gray-300 flex-1">{prod.name}</span>
                  <span className="text-xs text-brand-yellow font-medium">{formatRupiah(prod.base_price)}</span>
                </label>
              );
            })}
            {services.length > 0 && <p className="text-[10px] text-gray-400 uppercase tracking-wide px-2 pt-2 font-semibold">Jasa Lama</p>}
            {services.map((svc) => {
              const isSelected = selectedServices.some(s => s.id === svc.id);
              return (
                <label key={svc.id} className={`flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors ${isSelected ? "bg-brand-yellow/10" : "hover:bg-gray-100 dark:hover:bg-gray-800"}`}>
                  <input type="checkbox" checked={isSelected} onChange={() => toggleService(svc.id)} className="w-3.5 h-3.5 rounded border-gray-300 text-brand-yellow" />
                  <span className="text-xs text-gray-700 dark:text-gray-300 flex-1">{svc.name}</span>
                  <span className="text-xs text-brand-yellow font-medium">{formatRupiah(svc.default_price)}</span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Selected services detail */}
        {selectedServices.length > 0 && (
          <div className="space-y-3">
            <p className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">Detail Layanan Terpilih</p>
            {selectedServices.map((svc) => (
              <div key={svc.id} className="border border-gray-200 dark:border-gray-700 rounded-xl p-3 space-y-2 bg-white dark:bg-[var(--bg-surface)]">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-800 dark:text-neutral-50">{svc.name}</span>
                  <button type="button" onClick={() => setSelectedServices(prev => prev.filter(s => s.id !== svc.id))} className="text-xs text-red-400 hover:text-red-600">Hapus</button>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-400 uppercase mb-0.5">Harga (Rp)</label>
                  <input type="text" value={formatRupiahInput(svc.price)} onChange={(e) => updateSelectedService(svc.id, "price", String(cleanRupiahInput(e.target.value)))} className={inputClsLarge} />
                </div>
                <div>
                  <label className="block text-[10px] text-gray-400 uppercase mb-0.5">Fitur</label>
                  <textarea value={svc.features} onChange={(e) => updateSelectedService(svc.id, "features", e.target.value)} rows={2} className={inputClsLarge} />
                </div>
              </div>
            ))}
            <div className="flex items-center justify-between px-1 pt-1 border-t border-[var(--border-default)]">
              <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase">Grand Total</span>
              <span className="text-lg font-bold text-brand-yellow">{formatRupiah(grandTotal)}</span>
            </div>
          </div>
        )}

        {/* Timeline configurator */}
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Konfigurasi Timeline</label>
          <div className="border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-[var(--bg-surface)] p-3 space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <button type="button" onClick={() => setTimelinePhases(prev => [...prev, { sequence: prev.length + 1, title: "", description: "" }])}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold rounded-lg transition-colors">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                Tambah Fase
              </button>
              <div className="relative">
                <button type="button" onClick={() => setTimelineDropdownOpen(!timelineDropdownOpen)}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 text-xs font-semibold rounded-lg transition-colors">
                  Muat dari Template <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                </button>
                {timelineDropdownOpen && (
                  <div className="absolute top-full left-0 mt-1 w-56 bg-white dark:bg-zinc-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-50 py-1">
                    {timelineTemplates.length === 0 && <p className="text-xs text-gray-400 px-3 py-2">Tidak ada template.</p>}
                    {timelineTemplates.map((tmpl) => (
                      <button key={tmpl.id} type="button" onClick={() => { setTimelinePhases(tmpl.timeline_data); setTimelineDropdownOpen(false); }}
                        className="block w-full text-left px-3 py-2 text-xs text-gray-700 dark:text-gray-200 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors">
                        {tmpl.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
            {timelinePhases.length === 0 && <p className="text-[11px] text-gray-400 italic">Klik &quot;Tambah Fase&quot; atau muat dari template.</p>}
            {timelinePhases.map((phase, idx) => (
              <div key={idx} className="border border-gray-200 dark:border-gray-600 rounded-lg p-2.5 bg-white dark:bg-[#1e1e1d] space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-amber-500 text-white text-xs font-bold flex items-center justify-center shrink-0">{phase.sequence}</span>
                  <input type="text" placeholder="Judul Fase" value={phase.title}
                    onChange={(e) => setTimelinePhases(prev => prev.map((p, i) => i === idx ? { ...p, title: e.target.value } : p))}
                    className="flex-1 text-xs bg-transparent border-b border-gray-200 dark:border-gray-600 focus:border-amber-500 outline-none py-1 text-gray-800 dark:text-gray-100" />
                  <button type="button" onClick={() => setTimelinePhases(prev => prev.filter((_, i) => i !== idx).map((p, i) => ({ ...p, sequence: i + 1 })))}
                    className="text-red-400 hover:text-red-600 text-xs">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14H6L5 6" /></svg>
                  </button>
                </div>
                <textarea placeholder="Deskripsi..." value={phase.description}
                  onChange={(e) => setTimelinePhases(prev => prev.map((p, i) => i === idx ? { ...p, description: e.target.value } : p))}
                  rows={2} className="w-full text-xs bg-transparent border border-gray-200 dark:border-gray-600 focus:border-amber-500 rounded-md outline-none p-2 text-gray-700 dark:text-gray-200 resize-none" />
              </div>
            ))}
          </div>
        </div>

        {/* ROI toggle */}
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">Tampilkan ROI & Perbandingan</label>
            <button type="button" onClick={() => setRoiEnabled(!roiEnabled)}
              className={`relative w-10 h-5 rounded-full transition-colors ${roiEnabled ? "bg-amber-500" : "bg-gray-300 dark:bg-gray-600"}`}>
              <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${roiEnabled ? "translate-x-5" : "translate-x-0.5"}`} />
            </button>
          </div>
        </div>

        {/* Additional options */}
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Penyesuaian Tambahan <span className="normal-case font-normal">(Opsional)</span></label>
          <textarea value={additionalOptions} onChange={(e) => setAdditionalOptions(e.target.value)} rows={2} placeholder="Catatan khusus, diskon, bonus..." className={inputClsLarge} />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
          <button onClick={handleSubmit} disabled={saving || selectedServices.length === 0}
            className="px-4 py-2.5 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors disabled:opacity-50">
            {saving ? "Menyimpan..." : "Buat Proposal"}
          </button>
        </div>
      </div>
    </div>
  );
}