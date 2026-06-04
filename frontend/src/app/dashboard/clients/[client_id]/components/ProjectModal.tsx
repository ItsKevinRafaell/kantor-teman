"use client";

import { useState, type Dispatch, type SetStateAction } from "react";
import { Plus } from "lucide-react";
import { formatRupiahInput, cleanRupiahInput } from "../../../../../utils/formatter";

interface Product {
  id: string;
  name: string;
  base_price: number;
  is_retainer: boolean;
  category_name?: string | null;
}

interface ServiceType {
  value: string;
  label: string;
  default_months: number;
}

interface ProjectForm {
  name: string;
  type: string;
  status: string;
  nominal: number;
  start_date: string;
  end_date: string;
  service_type: string;
  contract_months: number;
}

interface ProjectData {
  id: string;
  name: string;
  type: string;
  status: string;
  nominal: number;
  start_date: string | null;
  end_date: string | null;
  service_type?: string | null;
  contract_months?: number | null;
}

interface ProjectModalProps {
  open: boolean;
  onClose: () => void;
  editingProject: ProjectData | null;
  products: Product[];
  serviceTypes: ServiceType[];
  form: ProjectForm;
  setForm: Dispatch<SetStateAction<ProjectForm>>;
  onSave: () => Promise<void>;
  saving: boolean;
}

const inputCls = "input-field";

export default function ProjectModal({
  open,
  onClose,
  editingProject,
  products,
  serviceTypes,
  form,
  setForm,
  onSave,
  saving,
}: ProjectModalProps) {
  if (!open) return null;

  function applyProduct(productId: string) {
    const p = products.find(x => x.id === productId);
    if (!p) return;
    const cat = (p.category_name || "").toLowerCase();
    let svcType = "";
    if (cat.includes("web")) svcType = cat.includes("bulanan") ? "web_dev_bulanan" : "web_dev";
    else if (cat.includes("seo") || cat.includes("google")) svcType = "seo_gmaps";
    else if (cat.includes("sosial") || cat.includes("sosmed") || cat.includes("kelola")) svcType = "sosmed";
    else if (cat.includes("maintenance")) svcType = "maintenance";
    else if (cat.includes("logo") || cat.includes("branding") || cat.includes("desain")) svcType = "branding";
    if (!svcType) {
      const nameL = p.name.toLowerCase();
      if (nameL.includes("seo") || nameL.includes("google")) svcType = "seo_gmaps";
      else if (nameL.includes("sosial") || nameL.includes("sosmed")) svcType = "sosmed";
      else if (nameL.includes("maintenance")) svcType = "maintenance";
      else if (nameL.includes("logo") || nameL.includes("branding")) svcType = "branding";
      else if (nameL.includes("web")) svcType = nameL.includes("bulanan") ? "web_dev_bulanan" : "web_dev";
    }
    const match = serviceTypes.find(s => s.value === svcType);
    const months = match?.default_months || 1;
    const startDate = new Date().toISOString().slice(0, 10);
    const endD = new Date();
    endD.setMonth(endD.getMonth() + months);
    const endDate = endD.toISOString().slice(0, 10);
    setForm(() => ({
      name: p.name,
      type: p.is_retainer ? "RETAINER" : "FIXED",
      status: "ACTIVE",
      nominal: p.base_price,
      service_type: svcType,
      contract_months: months,
      start_date: startDate,
      end_date: endDate,
    }));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-modal border border-[var(--border-default)] w-full max-w-md p-6 space-y-4 animate-slide-up">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">
            {editingProject ? "Edit Proyek" : "Tambah Proyek Baru"}
          </h3>
          <button onClick={onClose} className="p-1 text-neutral-400 hover:text-neutral-600">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
        <div className="space-y-3">
          {!editingProject && products.length > 0 && (
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Pilih dari Paket</label>
              <select onChange={e => applyProduct(e.target.value)} className={inputCls} defaultValue="">
                <option value="">— Custom (isi manual) —</option>
                {products.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0 }).format(p.base_price)}{p.is_retainer ? "/bln" : ""}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Nama Proyek</label>
            <input value={form.name} onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))} className={inputCls} placeholder="Contoh: SEO Bulanan, Landing Page" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Tipe</label>
              <select value={form.type} onChange={e => setForm(prev => ({ ...prev, type: e.target.value }))} className={inputCls}>
                <option value="RETAINER">Retainer (Bulanan)</option>
                <option value="FIXED">Fixed (Sekali)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Status</label>
              <select value={form.status} onChange={e => setForm(prev => ({ ...prev, status: e.target.value }))} className={inputCls}>
                <option value="ACTIVE">Active</option>
                <option value="COMPLETED">Completed</option>
                <option value="HOLD">Hold</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">
              {form.type === "RETAINER" ? "Bayaran / Bulan (Rp)" : "Nominal Total (Rp)"}
            </label>
            <input
              type="text"
              value={form.nominal ? formatRupiahInput(form.nominal) : ""}
              onChange={e => setForm(prev => ({ ...prev, nominal: cleanRupiahInput(e.target.value) }))}
              className={inputCls}
              placeholder="Rp 0"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Mulai</label>
              <input type="date" value={form.start_date} onChange={e => setForm(prev => ({ ...prev, start_date: e.target.value }))} className={inputCls} />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Berakhir</label>
              <input type="date" value={form.end_date} onChange={e => setForm(prev => ({ ...prev, end_date: e.target.value }))} className={inputCls} />
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="btn-ghost">Batal</button>
          <button onClick={onSave} disabled={saving} className="btn-primary">
            {saving ? "Menyimpan..." : "Simpan Proyek"}
          </button>
        </div>
      </div>
    </div>
  );
}

export const DEFAULT_PROJECT_FORM: ProjectForm = {
  name: "",
  type: "RETAINER",
  status: "ACTIVE",
  nominal: 0,
  start_date: "",
  end_date: "",
  service_type: "",
  contract_months: 1,
};