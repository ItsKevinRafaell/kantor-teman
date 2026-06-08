"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "../../lib/api";
import { formatRupiahInput, cleanRupiahInput } from "../../utils/formatter";
import { inputCls } from "../../lib/inputCls";
import type { ProductItem, ProjectData, ServiceTypeOption } from "../../types";

interface ProjectModalProps {
  contactId: number | null;
  contactLeadId?: number | null;
  editingProject: ProjectData | null;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  setToast: (toast: { message: string; type: "success" | "error" | "info" } | null) => void;
}

export default function ProjectModal({ contactId, contactLeadId, editingProject, open, onClose, onSuccess, setToast }: ProjectModalProps) {
  const [form, setForm] = useState({ name: "", type: "RETAINER", status: "ACTIVE", nominal: 0, start_date: "", end_date: "", service_type: "", contract_months: 1 });
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [serviceTypes, setServiceTypes] = useState<ServiceTypeOption[]>([]);
  const [existingProjects, setExistingProjects] = useState<ProjectData[]>([]);

  useEffect(() => {
    if (editingProject) {
      setForm({
        name: editingProject.name,
        type: editingProject.type,
        status: editingProject.status,
        nominal: editingProject.nominal,
        start_date: editingProject.start_date || "",
        end_date: editingProject.end_date || "",
        service_type: editingProject.service_type || "",
        contract_months: editingProject.contract_months || 1,
      });
    } else {
      const startDate = new Date().toISOString().slice(0, 10);
      setForm({ name: "", type: "RETAINER", status: "ACTIVE", nominal: 0, start_date: startDate, end_date: "", service_type: "", contract_months: 1 });
    }
  }, [editingProject]);

  useEffect(() => {
    apiFetch("/api/products?active_only=true")
      .then(r => r.ok ? r.json() : [])
      .then(setProducts)
      .catch(() => {});

    apiFetch("/api/workspace/service-types")
      .then(r => r.ok ? r.json() : [])
      .then(setServiceTypes)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!open) {
      setExistingProjects([]);
      return;
    }
    if (!contactLeadId) {
      setExistingProjects([]);
      return;
    }
    apiFetch("/api/projects")
      .then(r => r.ok ? r.json() : [])
      .then((projects: ProjectData[]) => setExistingProjects(projects.filter(p => p.lead_id === contactLeadId)))
      .catch(() => {});
  }, [open, contactLeadId]);

  function applyProductToForm(productId: string) {
    if (!productId) return;
    const p = products.find(x => x.id === productId);
    if (!p) return;
    const cat = (p.category_name || "").toLowerCase();
    let svcType = "";
    if (cat.includes("web")) svcType = cat.includes("bulanan") ? "web_dev_bulanan" : "web_dev";
    else if (cat.includes("seo") || cat.includes("google")) svcType = "seo_gmaps";
    else if (cat.includes("sosmed") || cat.includes("kelola")) svcType = "sosmed";
    else if (cat.includes("maintenance")) svcType = "maintenance";
    else if (cat.includes("logo") || cat.includes("branding") || cat.includes("desain")) svcType = "branding";
    const match = serviceTypes.find(s => s.value === svcType);
    const months = match?.default_months || 1;
    const startDate = new Date().toISOString().slice(0, 10);
    const endD = new Date();
    endD.setMonth(endD.getMonth() + months);
    const endDate = endD.toISOString().slice(0, 10);
    setForm(f => ({
      ...f,
      name: p.name,
      type: p.is_retainer ? "RETAINER" : "FIXED",
      nominal: p.base_price,
      service_type: svcType,
      contract_months: months,
      start_date: startDate,
      end_date: endDate,
    }));
  }

  async function handleSave() {
    if (!form.name || !contactId) return;
    const payload = { ...form, contact_id: contactId };
    const method = editingProject ? "PUT" : "POST";
    const url = editingProject ? `/api/projects/${editingProject.id}` : "/api/projects";
    const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
    if (res.ok) {
      setToast({ message: editingProject ? "Project diperbarui." : "Project ditambahkan!", type: "success" });
      onSuccess();
      onClose();
    } else {
      const err = await res.json().catch(() => ({}));
      setToast({ message: err.detail || "Gagal menyimpan project.", type: "error" });
    }
  }

  async function handleDelete(projectId: string) {
    const res = await apiFetch(`/api/projects/${projectId}`, { method: "DELETE" });
    if (res.ok) {
      setExistingProjects(prev => prev.filter(p => p.id !== projectId));
      setToast({ message: "Project dihapus.", type: "success" });
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editingProject ? "Edit Project" : "Tambah Project"}</h3>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Pilih dari Paket</label>
            <select onChange={e => applyProductToForm(e.target.value)} className={inputCls} defaultValue="">
              <option value="">— Custom (isi manual) —</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.name} — Rp {p.base_price.toLocaleString("id-ID")}{p.is_retainer ? "/bln" : ""}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Project</label>
            <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Contoh: SEO Bulanan" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Tipe</label>
              <select value={form.type} onChange={e => setForm(f => ({ ...f, type: e.target.value }))} className={inputCls}>
                <option value="RETAINER">Retainer (Bulanan)</option>
                <option value="FIXED">Fixed (Sekali)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Status</label>
              <select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))} className={inputCls}>
                <option value="ACTIVE">Active</option>
                <option value="COMPLETED">Completed</option>
                <option value="HOLD">Hold</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">{form.type === "RETAINER" ? "Bayaran / Bulan (Rp)" : "Nominal Total (Rp)"}</label>
            <input type="text" value={form.nominal ? formatRupiahInput(form.nominal) : ""} onChange={e => setForm(f => ({ ...f, nominal: cleanRupiahInput(e.target.value) }))} className={inputCls} placeholder="Rp 0" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Mulai</label>
              <input type="date" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} className={inputCls} />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Berakhir</label>
              <input type="date" value={form.end_date} onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))} className={inputCls} />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
          <button onClick={handleSave} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
        </div>

        {/* Existing projects */}
        {contactId && existingProjects.length > 0 && (
          <div className="border-t border-[var(--border-default)] pt-3">
            <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Project Existing</p>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {existingProjects.map(p => (
                <div key={p.id} className="flex items-center justify-between bg-neutral-50 dark:bg-neutral-800 rounded-lg px-3 py-2">
                  <div>
                    <span className={`text-xs font-semibold ${p.status === "ACTIVE" ? "text-emerald-600" : p.status === "HOLD" ? "text-amber-600" : "text-gray-500"}`}>{p.name}</span>
                    <span className="text-[10px] text-gray-400 ml-2">{p.type} · {formatRupiahInput(p.nominal)}</span>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => handleDelete(p.id)} className="text-[10px] text-red-400 hover:underline">Hapus</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}