"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "../../lib/api";
import { FileText, Copy, CheckCircle, Eye, ExternalLink, Download, Plus, Trash2 } from "lucide-react";
import { formatRupiahInput, cleanRupiahInput } from "../../utils/formatter";
import Modal from "../../components/Modal";
import Toast from "../../components/Toast";

interface Contact {
  id: number;
  business_name: string;
  owner_name: string | null;
  phone_number: string;
  purchased_product: string | null;
  notes: string | null;
}

interface ProjectData {
  id: string;
  lead_id: number;
  name: string;
  type: string;
  status: string;
  nominal: number;
  start_date: string | null;
  end_date: string | null;
}

interface ServiceItem {
  id: string;
  name: string;
  default_price: number;
  default_features: string[];
}

interface ProductItem {
  id: string;
  name: string;
  base_price: number;
  features: string[];
  category: string | null;
  is_active: boolean;
}

interface ProposalRecord {
  id: string;
  lead_id: number;
  services_detail: { name: string; price: number; features: string[] }[];
  total_price: number;
  additional_options: string | null;
  status: string;
  created_at: string | null;
  business_name: string | null;
  phone_number: string | null;
  slug: string | null;
}

function formatRupiah(num: number): string {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0 }).format(num);
}

export default function ClientsPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [projects, setProjects] = useState<ProjectData[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; id: number | null; name: string }>({ open: false, id: null, name: "" });
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  const [search, setSearch] = useState("");
  const [sortField, setSortField] = useState<"business_name" | "id">("id");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  // Edit client modal
  const [editClientModal, setEditClientModal] = useState<{ open: boolean; contact: Contact | null }>({ open: false, contact: null });
  const [editForm, setEditForm] = useState({ business_name: "", phone_number: "", owner_name: "", purchased_product: "", notes: "" });

  // Services list
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [products, setProducts] = useState<ProductItem[]>([]);

  // Proposal modal (multi-select)
  interface SelectedService { id: string; name: string; price: number; features: string; }
  const [proposalModal, setProposalModal] = useState<{ open: boolean; contact: Contact | null }>({ open: false, contact: null });
  const [selectedServices, setSelectedServices] = useState<SelectedService[]>([]);
  const [additionalOptions, setAdditionalOptions] = useState("");
  const [proposalSaving, setProposalSaving] = useState(false);
  const [proposalSuccess, setProposalSuccess] = useState<{ open: boolean; url: string }>({ open: false, url: "" });
  const [copied, setCopied] = useState(false);

  // Timeline configurator state
  interface TimelinePhase { sequence: number; title: string; description: string; }
  const [timelinePhases, setTimelinePhases] = useState<TimelinePhase[]>([]);
  const [timelineTemplates, setTimelineTemplates] = useState<{ id: string; name: string; timeline_data: TimelinePhase[] }[]>([]);
  const [timelineDropdownOpen, setTimelineDropdownOpen] = useState(false);

  // ROI configurator state
  const [roiEnabled, setRoiEnabled] = useState(true);
  const [retainerPeriod, setRetainerPeriod] = useState(0);

  useEffect(() => {
    async function fetchTimelineTemplates() {
      try {
        const res = await apiFetch("/api/timeline-templates");
        if (res.ok) setTimelineTemplates(await res.json());
      } catch {}
    }
    fetchTimelineTemplates();
  }, []);

  // Detail modal
  const [detailModal, setDetailModal] = useState<{ open: boolean; contact: Contact | null }>({ open: false, contact: null });
  const [detailTab, setDetailTab] = useState<"profil" | "aktivitas" | "proposal">("profil");
  const [clientProposals, setClientProposals] = useState<ProposalRecord[]>([]);
  const [loadingProposals, setLoadingProposals] = useState(false);

  // Unbilled dana talangan warning
  const [unbilledTotal, setUnbilledTotal] = useState(0);
  const [unbilledCount, setUnbilledCount] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Add Client modal
  const [addClientModal, setAddClientModal] = useState(false);
  const [clientForm, setClientForm] = useState({ business_name: "", phone_number: "", owner_name: "", purchased_product: "" });

  // Project modal
  const [projectModal, setProjectModal] = useState<{ open: boolean; contactId: number | null }>({ open: false, contactId: null });
  const [projectForm, setProjectForm] = useState({ name: "", type: "RETAINER", status: "ACTIVE", nominal: 0, start_date: "", end_date: "", service_type: "", contract_months: 1 });
  const [editingProject, setEditingProject] = useState<ProjectData | null>(null);
  const [serviceTypes, setServiceTypes] = useState<{ value: string; label: string; default_months: number }[]>([]);

  // Notes modal (per-column/category)
  const [notesModal, setNotesModal] = useState<{ open: boolean; contact: Contact | null }>({ open: false, contact: null });
  const [clientNotes, setClientNotes] = useState<{ id: string; category: string; content: string; actor: string; timestamp: string }[]>([]);
  const [noteForm, setNoteForm] = useState({ category: "BISNIS", content: "" });

  const fetchContacts = useCallback(async () => {
    try {
      const [cRes, pRes] = await Promise.all([
        apiFetch("/api/contacts"),
        apiFetch("/api/projects"),
      ]);
      if (cRes.ok) setContacts(await cRes.json());
      if (pRes.ok) setProjects(await pRes.json());
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    apiFetch("/api/workspace/service-types")
      .then(r => r.ok ? r.json() : [])
      .then(setServiceTypes)
      .catch(() => {});
  }, []);

  const fetchServices = useCallback(async () => {
    try {
      const [sRes, pRes] = await Promise.all([
        apiFetch("/api/settings/services"),
        apiFetch("/api/products?active_only=true"),
      ]);
      if (sRes.ok) setServices(await sRes.json());
      if (pRes.ok) setProducts(await pRes.json());
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchContacts();
    fetchServices();
    intervalRef.current = setInterval(() => { fetchContacts(); fetchServices(); }, 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchContacts, fetchServices]);

  async function exportLeadsCSV() {
    const res = await apiFetch("/api/export/leads");
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "leads_export.csv";
      a.click();
      URL.revokeObjectURL(url);
    }
  }

  function openEditClient(c: Contact) {
    setEditClientModal({ open: true, contact: c });
    setEditForm({ business_name: c.business_name, phone_number: c.phone_number, owner_name: c.owner_name || "", purchased_product: c.purchased_product || "", notes: c.notes || "" });
  }

  async function saveEditClient() {
    if (!editClientModal.contact) return;
    const res = await apiFetch(`/api/contacts/${editClientModal.contact.id}`, {
      method: "PATCH", body: JSON.stringify(editForm),
    });
    if (res.ok) {
      setEditClientModal({ open: false, contact: null });
      setToast({ message: "Klien berhasil diperbarui.", type: "success" });
      fetchContacts();
    }
  }

  async function confirmDelete() {
    const id = deleteModal.id;
    if (!id) return;
    setDeleteModal({ open: false, id: null, name: "" });
    const res = await apiFetch(`/api/contacts/${id}`, { method: "DELETE" });
    if (res.ok) {
      setContacts((prev) => prev.filter((c) => c.id !== id));
      setToast({ message: "Klien berhasil dihapus.", type: "success" });
    }
  }

  function toggleService(serviceId: string) {
    const existing = selectedServices.find((s) => s.id === serviceId);
    if (existing) {
      setSelectedServices((prev) => prev.filter((s) => s.id !== serviceId));
    } else {
      const svc = services.find((s) => s.id === serviceId);
      if (svc) {
        setSelectedServices((prev) => [...prev, { id: svc.id, name: svc.name, price: svc.default_price, features: svc.default_features.join("\n") }]);
      }
    }
  }

  function toggleProduct(productId: string) {
    const existing = selectedServices.find((s) => s.id === productId);
    if (existing) {
      setSelectedServices((prev) => prev.filter((s) => s.id !== productId));
    } else {
      const prod = products.find((p) => p.id === productId);
      if (prod) {
        setSelectedServices((prev) => [...prev, { id: prod.id, name: prod.name, price: prod.base_price, features: prod.features.join("\n") }]);
      }
    }
  }

  function updateSelectedService(id: string, field: "price" | "features", value: string) {
    setSelectedServices((prev) => prev.map((s) => s.id === id ? { ...s, [field]: field === "price" ? Number(value) || 0 : value } : s));
  }

  const grandTotal = selectedServices.reduce((sum, s) => sum + (typeof s.price === "number" ? s.price : 0), 0);

  async function submitProposal() {
    const contact = proposalModal.contact;
    if (!contact || selectedServices.length === 0) return;
    setProposalSaving(true);
    try {
      const servicesPayload = selectedServices.map((s) => ({
        name: s.name,
        price: s.price,
        features: s.features.split(/[\n,]+/).map((f) => f.trim()).filter(Boolean),
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
      setProposalModal({ open: false, contact: null });
      setSelectedServices([]);
      setAdditionalOptions("");
      setTimelinePhases([]);
      setProposalSuccess({ open: true, url });
    } catch (err: unknown) {
      setToast({ message: err instanceof Error ? err.message : "Gagal membuat proposal.", type: "error" });
    } finally {
      setProposalSaving(false);
    }
  }

  function copyLink() {
    navigator.clipboard.writeText(proposalSuccess.url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function openDetail(contact: Contact) {
    setDetailModal({ open: true, contact });
    setDetailTab("profil");
    setLoadingProposals(true);
    try {
      const res = await apiFetch(`/api/proposals/client/${contact.id}?source=contact`);
      if (res.ok) setClientProposals(await res.json());
      else setClientProposals([]);
    } catch { setClientProposals([]); }
    finally { setLoadingProposals(false); }
  }

  function copyProposalLink(id: string, slug?: string | null) {
    const link = `${window.location.origin}/proposal/${id}`;
    navigator.clipboard.writeText(link);
    setToast({ message: "Link proposal tersalin!", type: "info" });
  }

  async function fetchUnbilled(contactId: number) {
    try {
      const res = await apiFetch(`/api/finance/client/${contactId}/unbilled`);
      if (res.ok) {
        const data = await res.json();
        setUnbilledTotal(data.unbilled_total);
        setUnbilledCount(data.count);
      } else {
        setUnbilledTotal(0);
        setUnbilledCount(0);
      }
    } catch {
      setUnbilledTotal(0);
      setUnbilledCount(0);
    }
  }

  // Add Client
  async function saveClient() {
    if (!clientForm.business_name || !clientForm.phone_number) return;
    const res = await apiFetch("/api/contacts", { method: "POST", body: JSON.stringify(clientForm) });
    if (res.ok) {
      setAddClientModal(false);
      setClientForm({ business_name: "", phone_number: "", owner_name: "", purchased_product: "" });
      setToast({ message: "Klien berhasil ditambahkan!", type: "success" });
      fetchContacts();
    } else {
      const d = await res.json().catch(() => ({}));
      setToast({ message: d.detail || "Gagal menambah klien.", type: "error" });
    }
  }

  // Project CRUD
  function openProjectModal(contactId: number, project?: ProjectData) {
    setProjectModal({ open: true, contactId });
    if (project) {
      setEditingProject(project);
      setProjectForm({ name: project.name, type: project.type, status: project.status, nominal: project.nominal, start_date: project.start_date || "", end_date: project.end_date || "", service_type: "", contract_months: 1 });
    } else {
      setEditingProject(null);
      setProjectForm({ name: "", type: "RETAINER", status: "ACTIVE", nominal: 0, start_date: new Date().toISOString().slice(0, 10), end_date: "", service_type: "", contract_months: 1 });
    }
  }

  async function saveProject() {
    if (!projectForm.name || !projectModal.contactId) return;
    const payload = { ...projectForm, lead_id: projectModal.contactId };
    const method = editingProject ? "PUT" : "POST";
    const url = editingProject ? `/api/projects/${editingProject.id}` : "/api/projects";
    const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
    if (res.ok) {
      setProjectModal({ open: false, contactId: null });
      setEditingProject(null);
      setToast({ message: editingProject ? "Project diperbarui." : "Project ditambahkan!", type: "success" });
      fetchContacts();
    }
  }

  async function deleteProject(id: string) {
    const res = await apiFetch(`/api/projects/${id}`, { method: "DELETE" });
    if (res.ok) { fetchContacts(); setToast({ message: "Project dihapus.", type: "success" }); }
  }

  // Notes
  async function openNotesModal(contact: Contact) {
    setNotesModal({ open: true, contact });
    setNoteForm({ category: "BISNIS", content: "" });
    try {
      const res = await apiFetch(`/api/client-notes?lead_id=${contact.id}`);
      if (res.ok) setClientNotes(await res.json());
      else setClientNotes([]);
    } catch { setClientNotes([]); }
  }

  async function saveNote() {
    if (!noteForm.content || !notesModal.contact) return;
    const res = await apiFetch("/api/client-notes", { method: "POST", body: JSON.stringify({ lead_id: notesModal.contact.id, category: noteForm.category, content: noteForm.content }) });
    if (res.ok) {
      setNoteForm({ category: "BISNIS", content: "" });
      const r = await apiFetch(`/api/client-notes?lead_id=${notesModal.contact.id}`);
      if (r.ok) setClientNotes(await r.json());
    }
  }

  async function deleteNote(noteId: string) {
    if (!notesModal.contact) return;
    await apiFetch(`/api/client-notes/${noteId}`, { method: "DELETE" });
    const r = await apiFetch(`/api/client-notes?lead_id=${notesModal.contact.id}`);
    if (r.ok) setClientNotes(await r.json());
  }

  const inputCls = "w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50 transition";

  return (
    <div className="max-w-6xl space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
      <Modal open={deleteModal.open} title="Hapus Klien"
        message={`Hapus "${deleteModal.name}" dari buku klien?`}
        confirmLabel="Hapus" confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={confirmDelete} onCancel={() => setDeleteModal({ open: false, id: null, name: "" })} />

      {/* Proposal Form Modal */}
      <Modal open={proposalModal.open} title="Buat Proposal"
        confirmLabel={proposalSaving ? "Menyimpan..." : "Buat Proposal"}
        confirmClass="bg-brand-yellow hover:bg-amber-600 text-white"
        onConfirm={submitProposal}
        onCancel={() => { setProposalModal({ open: false, contact: null }); setSelectedServices([]); setAdditionalOptions(""); setTimelinePhases([]); setTimelineDropdownOpen(false); }}>
        <div className="space-y-3 max-h-[60vh] overflow-y-auto">
          <p className="text-xs text-neutral-500 dark:text-neutral-400">Proposal untuk: <span className="font-semibold text-gray-700 dark:text-[#fcfaf7]">{proposalModal.contact?.business_name}</span></p>
          {unbilledTotal > 0 && (
            <div className="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-xl">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-600 dark:text-amber-400 mt-0.5 shrink-0"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
              <div>
                <p className="text-xs font-semibold text-amber-800 dark:text-amber-300">Peringatan: Ada dana talangan {formatRupiah(unbilledTotal)} untuk klien ini yang belum ditagihkan!</p>
                <p className="text-[11px] text-amber-600 dark:text-amber-400 mt-0.5">{unbilledCount} transaksi belum di-billing.</p>
              </div>
            </div>
          )}
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Pilih Layanan (Multi-Select)</label>
            <div className="border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-[#2a2a29] p-2 space-y-1 max-h-44 overflow-y-auto">
              {products.length === 0 && services.length === 0 && <p className="text-xs text-gray-400 px-2 py-1">Belum ada produk. Tambahkan di <a href="/master/products" className="underline text-brand-yellow">Katalog Produk</a>.</p>}
              {products.length > 0 && <p className="text-[10px] text-gray-400 uppercase tracking-wide px-2 pt-1 font-semibold">Katalog Produk</p>}
              {products.map((prod) => {
                const isSelected = selectedServices.some((s) => s.id === prod.id);
                return (
                  <label key={prod.id} className={`flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors ${isSelected ? "bg-brand-yellow/10" : "hover:bg-gray-100 dark:hover:bg-gray-800"}`}>
                    <input type="checkbox" checked={isSelected} onChange={() => toggleProduct(prod.id)}
                      className="w-3.5 h-3.5 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
                    <span className="text-xs text-gray-700 dark:text-gray-300 flex-1">{prod.name}</span>
                    <span className="text-xs text-brand-yellow font-medium">{formatRupiah(prod.base_price)}</span>
                  </label>
                );
              })}
              {services.length > 0 && <p className="text-[10px] text-gray-400 uppercase tracking-wide px-2 pt-2 font-semibold">Jasa Lama</p>}
              {services.map((svc) => {
                const isSelected = selectedServices.some((s) => s.id === svc.id);
                return (
                  <label key={svc.id} className={`flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors ${isSelected ? "bg-brand-yellow/10" : "hover:bg-gray-100 dark:hover:bg-gray-800"}`}>
                    <input type="checkbox" checked={isSelected} onChange={() => toggleService(svc.id)}
                      className="w-3.5 h-3.5 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
                    <span className="text-xs text-gray-700 dark:text-gray-300 flex-1">{svc.name}</span>
                    <span className="text-xs text-brand-yellow font-medium">{formatRupiah(svc.default_price)}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {selectedServices.length > 0 && (
            <div className="space-y-3">
              <p className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">Detail Layanan Terpilih</p>
              {selectedServices.map((svc) => (
                <div key={svc.id} className="border border-gray-200 dark:border-gray-700 rounded-xl p-3 space-y-2 bg-white dark:bg-[#2a2a29]">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-gray-800 dark:text-[#fcfaf7]">{svc.name}</span>
                    <button type="button" onClick={() => setSelectedServices((prev) => prev.filter((s) => s.id !== svc.id))}
                      className="text-xs text-red-400 hover:text-red-600">Hapus</button>
                  </div>
                  <div>
                    <label className="block text-[10px] text-gray-400 uppercase mb-0.5">Harga (Rp)</label>
                    <input type="text" value={formatRupiahInput(svc.price)} onChange={(e) => updateSelectedService(svc.id, "price", String(cleanRupiahInput(e.target.value)))}
                      className={inputCls} />
                  </div>
                  <div>
                    <label className="block text-[10px] text-gray-400 uppercase mb-0.5">Fitur</label>
                    <textarea value={svc.features} onChange={(e) => updateSelectedService(svc.id, "features", e.target.value)}
                      rows={2} className={inputCls + " resize-none"} />
                  </div>
                </div>
              ))}
              <div className="flex items-center justify-between px-1 pt-1 border-t border-[var(--border-default)]">
                <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase">Grand Total</span>
                <span className="text-lg font-bold text-brand-yellow">{formatRupiah(grandTotal)}</span>
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Konfigurasi Timeline Proyeksi Masa Depan</label>
            <div className="border border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50 dark:bg-[#2a2a29] p-3 space-y-2">
              <div className="flex items-center gap-2 mb-2">
                <button type="button" onClick={() => setTimelinePhases((prev) => [...prev, { sequence: prev.length + 1, title: "", description: "" }])}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold rounded-lg transition-colors">
                  <Plus size={12} /> Tambah Fase
                </button>
                <div className="relative">
                  <button type="button" onClick={() => setTimelineDropdownOpen(!timelineDropdownOpen)}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 text-xs font-semibold rounded-lg transition-colors">
                    Muat dari Template
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                  </button>
                  {timelineDropdownOpen && (
                    <div className="absolute top-full left-0 mt-1 w-56 bg-white dark:bg-zinc-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-50 py-1">
                      {timelineTemplates.length === 0 && <p className="text-xs text-gray-400 px-3 py-2">Tidak ada template.</p>}
                      {timelineTemplates.map((tmpl) => (
                        <button key={tmpl.id} type="button"
                          onClick={() => { setTimelinePhases(tmpl.timeline_data); setTimelineDropdownOpen(false); }}
                          className="block w-full text-left px-3 py-2 text-xs text-gray-700 dark:text-gray-200 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors">
                          {tmpl.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              {timelinePhases.length === 0 && <p className="text-[11px] text-gray-400 italic">Belum ada fase timeline. Klik &quot;Tambah Fase&quot; atau muat dari template.</p>}
              {timelinePhases.map((phase, idx) => (
                <div key={idx} className="border border-gray-200 dark:border-gray-600 rounded-lg p-2.5 bg-white dark:bg-[#1e1e1d] space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-amber-500 text-white text-xs font-bold flex items-center justify-center shrink-0">{phase.sequence}</span>
                    <input type="text" placeholder="Judul Fase" value={phase.title}
                      onChange={(e) => setTimelinePhases((prev) => prev.map((p, i) => i === idx ? { ...p, title: e.target.value } : p))}
                      className="flex-1 text-xs bg-transparent border-b border-gray-200 dark:border-gray-600 focus:border-amber-500 outline-none py-1 text-gray-800 dark:text-gray-100 placeholder-gray-400" />
                    <button type="button" onClick={() => setTimelinePhases((prev) => prev.filter((_, i) => i !== idx).map((p, i) => ({ ...p, sequence: i + 1 })))}
                      className="text-red-400 hover:text-red-600 text-xs">
                      <Trash2 size={12} />
                    </button>
                  </div>
                  <textarea placeholder="Deskripsi detail fase ini..." value={phase.description}
                    onChange={(e) => setTimelinePhases((prev) => prev.map((p, i) => i === idx ? { ...p, description: e.target.value } : p))}
                    rows={2} className="w-full text-xs bg-transparent border border-gray-200 dark:border-gray-600 focus:border-amber-500 rounded-md outline-none p-2 text-gray-700 dark:text-gray-200 placeholder-gray-400 resize-none" />
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5">Penyesuaian Tambahan <span className="normal-case font-normal">(Opsional)</span></label>
            <textarea value={additionalOptions} onChange={(e) => setAdditionalOptions(e.target.value)}
              rows={2} placeholder="Catatan khusus, diskon, bonus, dll."
              className={inputCls + " resize-none"} />
          </div>

          {/* ROI & Comparison Toggle */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">Tampilkan ROI & Perbandingan</label>
              <button type="button" onClick={() => setRoiEnabled(!roiEnabled)}
                className={`relative w-10 h-5 rounded-full transition-colors ${roiEnabled ? "bg-amber-500" : "bg-gray-300 dark:bg-gray-600"}`}>
                <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${roiEnabled ? "translate-x-5" : "translate-x-0.5"}`}></div>
              </button>
            </div>
            {roiEnabled && (
              <div className="mt-3 space-y-2">
                <div>
                  <label className="block text-[10px] text-zinc-500 font-semibold mb-1">Periode Retainer (jika ada layanan bulanan)</label>
                  <select value={retainerPeriod} onChange={(e) => setRetainerPeriod(Number(e.target.value))}
                    className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-[#2a2a29] dark:text-[#fcfaf7] outline-none focus:ring-1 focus:ring-amber-300">
                    <option value={0}>Tidak ada retainer (sekali bayar)</option>
                    <option value={3}>3 Bulan</option>
                    <option value={6}>6 Bulan</option>
                    <option value={12}>12 Bulan</option>
                  </select>
                </div>
                <p className="text-[10px] text-zinc-400 italic">ROI & perbandingan otomatis dikalkulasi dari produk yang dipilih dan periode retainer.</p>
              </div>
            )}
          </div>
        </div>
      </Modal>

      {/* Proposal Success Modal */}
      <Modal open={proposalSuccess.open} title="Proposal Berhasil Dibuat!"
        confirmLabel="Tutup" confirmClass="bg-gray-200 hover:bg-gray-300 text-gray-700"
        onConfirm={() => setProposalSuccess({ open: false, url: "" })}
        onCancel={() => setProposalSuccess({ open: false, url: "" })}>
        <div className="space-y-3 text-center">
          <div className="flex justify-center">
            <CheckCircle size={48} className="text-green-500" />
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-300">Kirim link ini ke klien:</p>
          <div className="flex items-center gap-2 bg-neutral-50 dark:bg-neutral-800 border border-gray-200 dark:border-gray-700 rounded-xl px-3 py-2.5">
            <input type="text" readOnly value={proposalSuccess.url}
              className="flex-1 text-xs bg-transparent text-gray-700 dark:text-gray-200 outline-none truncate" />
            <button onClick={copyLink}
              className="flex items-center gap-1 px-3 py-1.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs font-semibold rounded-lg transition-colors">
              <Copy size={12} />
              {copied ? "Tersalin!" : "Copy"}
            </button>
          </div>
        </div>
      </Modal>

      {/* Detail Klien Modal */}
      {detailModal.open && detailModal.contact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setDetailModal({ open: false, contact: null })} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-2xl max-h-[80vh] flex flex-col outline-none">
            <div className="px-6 py-4 border-b border-[var(--border-default)]">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Detail Klien — {detailModal.contact.business_name}</h3>
            </div>
            {/* Tabs */}
            <div className="flex border-b border-[var(--border-default)] px-6">
              {(["profil", "aktivitas", "proposal"] as const).map((tab) => (
                <button key={tab} onClick={() => setDetailTab(tab)}
                  className={`px-4 py-2.5 text-xs font-semibold uppercase tracking-wide border-b-2 transition-colors ${detailTab === tab ? "border-brand-yellow text-brand-yellow" : "border-transparent text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"}`}>
                  {tab === "profil" ? "Profil Klien" : tab === "aktivitas" ? "Riwayat Aktivitas" : "Riwayat Proposal"}
                </button>
              ))}
            </div>
            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {detailTab === "profil" && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-4">
                    <div><p className="text-xs text-gray-400 uppercase tracking-wide">Nama Bisnis</p><p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{detailModal.contact.business_name}</p></div>
                    <div><p className="text-xs text-gray-400 uppercase tracking-wide">Owner</p><p className="text-sm text-gray-700 dark:text-gray-300">{detailModal.contact.owner_name || "—"}</p></div>
                    <div><p className="text-xs text-gray-400 uppercase tracking-wide">Nomor WA</p><p className="text-sm font-mono text-gray-700 dark:text-gray-300">+{detailModal.contact.phone_number}</p></div>
                    <div><p className="text-xs text-gray-400 uppercase tracking-wide">Produk</p><p className="text-sm text-gray-700 dark:text-gray-300">{detailModal.contact.purchased_product || "—"}</p></div>
                  </div>
                  {detailModal.contact.notes && (
                    <div><p className="text-xs text-gray-400 uppercase tracking-wide">Catatan</p><p className="text-sm text-gray-600 dark:text-neutral-500 dark:text-neutral-400 mt-1">{detailModal.contact.notes}</p></div>
                  )}
                </div>
              )}
              {detailTab === "aktivitas" && (
                <div className="text-center py-8 text-gray-400 text-sm">
                  Fitur riwayat aktivitas akan segera hadir.
                </div>
              )}
              {detailTab === "proposal" && (
                <div>
                  {loadingProposals ? (
                    <div className="text-center py-8 text-gray-400 text-sm animate-pulse">Memuat proposal...</div>
                  ) : clientProposals.length === 0 ? (
                    <div className="text-center py-8 text-gray-400 text-sm">Belum ada proposal untuk klien ini.</div>
                  ) : (
                    <div className="overflow-x-auto rounded-xl border border-[var(--border-default)]">
                      <table className="w-full text-sm">
                        <thead className="bg-neutral-50 dark:bg-neutral-800">
                          <tr>
                            {["Tanggal", "Layanan", "Harga", "Status", "Aksi"].map((h) => (
                              <th key={h} className="text-left px-3 py-2 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[var(--border-subtle)]">
                          {clientProposals.map((p) => (
                            <tr key={p.id} className="hover:bg-[var(--bg-surface-hover)]">
                              <td className="px-3 py-2 text-xs text-gray-500">{p.created_at ? new Date(p.created_at).toLocaleDateString("id-ID") : "—"}</td>
                              <td className="px-3 py-2 text-xs font-medium text-neutral-800 dark:text-neutral-200">{p.services_detail.map((s) => s.name).join(", ")}</td>
                              <td className="px-3 py-2 text-xs text-gray-600 dark:text-gray-400">{formatRupiah(p.total_price)}</td>
                              <td className="px-3 py-2"><span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${p.status === "Accepted" ? "bg-green-100 text-green-700" : p.status === "Rejected" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>{p.status}</span></td>
                              <td className="px-3 py-2">
                                <button onClick={() => copyProposalLink(p.id, p.slug)} className="inline-flex items-center gap-1 text-xs text-brand-yellow hover:underline">
                                  <ExternalLink size={11} /> Lihat Link
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="px-6 py-3 border-t border-[var(--border-default)] flex justify-end">
              <button onClick={() => setDetailModal({ open: false, contact: null })}
                className="px-4 py-2 text-sm font-semibold text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Buku Klien</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Daftar klien aktif yang sudah dikonversi dari leads.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={exportLeadsCSV} className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs sm:text-sm font-semibold rounded-xl transition-colors">
            <Download size={14} /> Export CSV
          </button>
          <button onClick={() => setAddClientModal(true)} className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-4 sm:py-2.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs sm:text-sm font-semibold rounded-xl transition-colors">
            + Tambah Klien
          </button>
        </div>
      </div>

      {/* Search & Sort */}
      <div className="flex items-center gap-3 flex-wrap">
        <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Cari nama bisnis atau owner..."
          className="flex-1 max-w-sm px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50 transition" />
        <select value={sortField} onChange={e => setSortField(e.target.value as "business_name" | "id")}
          className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-xs bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50">
          <option value="id">Urut: Terbaru</option>
          <option value="business_name">Urut: Nama</option>
        </select>
        <button onClick={() => setSortDir(d => d === "asc" ? "desc" : "asc")}
          className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-xs font-semibold bg-neutral-50 dark:bg-neutral-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
          {sortDir === "asc" ? "↑ A-Z" : "↓ Z-A"}
        </button>
      </div>

      {loading && (
        <div className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] shadow-card overflow-hidden">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="flex gap-4 px-6 py-4 border-b border-[var(--border-subtle)] last:border-0 animate-pulse">
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/4" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/4" />
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/3 ml-auto" />
            </div>
          ))}
        </div>
      )}

      {!loading && contacts.length === 0 && (
        <div className="text-center py-16 bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] text-gray-400 text-sm">
          Belum ada klien. Konversi lead dari halaman <span className="font-semibold text-gray-600 dark:text-gray-300">Semua Leads</span>.
        </div>
      )}

      {!loading && contacts.length > 0 && (
        <div className="overflow-x-auto rounded-2xl shadow-sm border border-[var(--border-default)]">
          <table className="w-full bg-[var(--bg-surface)] text-sm">
            <thead className="bg-neutral-50 dark:bg-neutral-800 border-b border-[var(--border-default)]">
              <tr>{["#", "Nama Bisnis", "Nama Owner", "Nomor WA", "Proyek Aktif", "Nilai Kontrak", "Timeline", "Aksi"].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide whitespace-nowrap">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {contacts
                .filter(c => {
                  if (!search) return true;
                  const q = search.toLowerCase();
                  return c.business_name.toLowerCase().includes(q) || (c.owner_name || "").toLowerCase().includes(q);
                })
                .sort((a, b) => {
                  const valA = sortField === "business_name" ? a.business_name.toLowerCase() : String(a.id);
                  const valB = sortField === "business_name" ? b.business_name.toLowerCase() : String(b.id);
                  return sortDir === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
                })
                .map((c, i) => {
                const clientProjects = projects.filter(p => p.lead_id === c.id);
                const activeProjects = clientProjects.filter(p => p.status === "ACTIVE");
                const totalValue = activeProjects.reduce((sum, p) => sum + p.nominal, 0);
                const nearestEnd = activeProjects.filter(p => p.end_date).sort((a, b) => (a.end_date || "").localeCompare(b.end_date || ""))[0];
                const daysLeft = nearestEnd?.end_date ? Math.ceil((new Date(nearestEnd.end_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24)) : null;
                const totalDays = nearestEnd?.start_date && nearestEnd?.end_date ? Math.ceil((new Date(nearestEnd.end_date).getTime() - new Date(nearestEnd.start_date).getTime()) / (1000 * 60 * 60 * 24)) : null;
                const progress = totalDays && daysLeft !== null ? Math.max(0, Math.min(100, ((totalDays - daysLeft) / totalDays) * 100)) : 0;

                return (
                <tr key={c.id} className="hover:bg-[var(--bg-surface-hover)] transition-colors">
                  <td className="px-4 py-3 text-gray-400 text-xs">{i + 1}</td>
                  <td className="px-4 py-3 font-semibold text-neutral-800 dark:text-neutral-200">
                    <a href={`/dashboard/clients/${c.id}`} className="hover:text-brand-yellow transition-colors">{c.business_name}</a>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-gray-700 dark:text-gray-300">{c.owner_name || <span className="text-gray-300 dark:text-gray-600 italic">—</span>}</span>
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-600 dark:text-gray-400 text-xs whitespace-nowrap">
                    <a href={`https://wa.me/${c.phone_number}`} target="_blank" rel="noopener noreferrer" className="text-green-600 hover:underline">+{c.phone_number}</a>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {activeProjects.length > 0 ? activeProjects.map(p => (
                        <span key={p.id} className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${p.type === "RETAINER" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"}`}>
                          {p.type === "RETAINER" ? "Retainer" : "Fixed"}: {p.name}
                        </span>
                      )) : (
                        <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500">Idle</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {activeProjects.length > 0 ? (
                      <div>
                        <span className="text-xs font-bold text-neutral-800 dark:text-neutral-200">{formatRupiah(totalValue)}</span>
                        <p className="text-[10px] text-gray-400">{activeProjects[0]?.type === "RETAINER" ? "/bulan (MRR)" : "Total (TCV)"}</p>
                      </div>
                    ) : <span className="text-gray-300 dark:text-gray-600 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3 min-w-[120px]">
                    {daysLeft !== null ? (
                      <div>
                        <div className="w-full h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden mb-1">
                          <div className={`h-full rounded-full transition-all ${daysLeft <= 7 ? "bg-red-500" : daysLeft <= 14 ? "bg-amber-500" : "bg-emerald-500"}`} style={{ width: `${progress}%` }} />
                        </div>
                        <span className={`text-[10px] font-semibold ${daysLeft <= 7 ? "text-red-600 dark:text-red-400" : daysLeft <= 14 ? "text-amber-600 dark:text-amber-400" : "text-neutral-500 dark:text-neutral-400"}`}>
                          {daysLeft <= 0 ? "Expired" : daysLeft <= 7 ? `${daysLeft}d — Need Renewal` : `${daysLeft} hari lagi`}
                        </span>
                      </div>
                    ) : <span className="text-gray-300 dark:text-gray-600 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                          <a href={`/dashboard/clients/${c.id}`}
                            className="inline-flex items-center gap-1 px-2 py-1.5 text-gray-500 hover:text-brand-yellow hover:bg-brand-yellow/10 text-xs font-medium rounded-lg transition-colors whitespace-nowrap">
                            <Eye size={12} /> Detail
                          </a>
                          <button onClick={() => openNotesModal(c)}
                            className="inline-flex items-center gap-1 px-2 py-1.5 text-gray-500 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 text-xs font-medium rounded-lg transition-colors whitespace-nowrap">
                            <FileText size={12} /> Notes
                          </button>
                          <button onClick={() => openProjectModal(c.id)}
                            className="inline-flex items-center gap-1 px-2 py-1.5 text-gray-500 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 text-xs font-medium rounded-lg transition-colors whitespace-nowrap">
                            + Project
                          </button>
                          <button onClick={() => { setSelectedServices([]); setAdditionalOptions(""); setTimelinePhases([]); setRoiEnabled(true); setProposalModal({ open: true, contact: c }); fetchUnbilled(c.id); }}
                            className="inline-flex items-center gap-1 px-2 py-1.5 bg-brand-yellow/10 hover:bg-brand-yellow/20 text-brand-yellow text-xs font-semibold rounded-lg transition-colors whitespace-nowrap">
                            <FileText size={12} /> Proposal
                          </button>
                          <button onClick={() => openEditClient(c)}
                            className="p-1.5 text-gray-400 hover:text-brand-yellow hover:bg-brand-yellow/10 rounded-lg transition-colors">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                          </button>
                          <button onClick={() => setDeleteModal({ open: true, id: c.id, name: c.business_name })}
                            className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14H6L5 6" /><path d="M10 11v6" /><path d="M14 11v6" /><path d="M9 6V4h6v2" /></svg>
                          </button>
                    </div>
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
          <div className="px-4 py-2 bg-neutral-50 dark:bg-neutral-800 border-t border-[var(--border-default)] text-xs text-gray-400">{contacts.length} klien aktif</div>
        </div>
      )}

      {/* Add Client Modal */}
      {addClientModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setAddClientModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Tambah Klien Baru</h3>
              <button onClick={() => setAddClientModal(false)} className="p-1 text-gray-400 hover:text-gray-600"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Bisnis *</label>
                <input value={clientForm.business_name} onChange={e => setClientForm(f => ({ ...f, business_name: e.target.value }))} className={inputCls} placeholder="Contoh: PT Maju Jaya" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nomor WhatsApp *</label>
                <input value={clientForm.phone_number} onChange={e => setClientForm(f => ({ ...f, phone_number: e.target.value }))} className={inputCls} placeholder="628123456789" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Owner</label>
                <input value={clientForm.owner_name} onChange={e => setClientForm(f => ({ ...f, owner_name: e.target.value }))} className={inputCls} placeholder="Opsional" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Produk/Layanan</label>
                <input value={clientForm.purchased_product} onChange={e => setClientForm(f => ({ ...f, purchased_product: e.target.value }))} className={inputCls} placeholder="Opsional" />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setAddClientModal(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={saveClient} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Client Modal */}
      {editClientModal.open && editClientModal.contact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setEditClientModal({ open: false, contact: null })} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Edit Klien</h3>
              <button onClick={() => setEditClientModal({ open: false, contact: null })} className="p-1 text-gray-400 hover:text-gray-600"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Bisnis</label>
                <input value={editForm.business_name} onChange={e => setEditForm(f => ({ ...f, business_name: e.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nomor WhatsApp</label>
                <input value={editForm.phone_number} onChange={e => setEditForm(f => ({ ...f, phone_number: e.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Owner</label>
                <input value={editForm.owner_name} onChange={e => setEditForm(f => ({ ...f, owner_name: e.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Produk/Layanan</label>
                <input value={editForm.purchased_product} onChange={e => setEditForm(f => ({ ...f, purchased_product: e.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Catatan</label>
                <textarea value={editForm.notes} onChange={e => setEditForm(f => ({ ...f, notes: e.target.value }))} rows={3} className={inputCls + " resize-none"} />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setEditClientModal({ open: false, contact: null })} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={saveEditClient} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
            </div>
          </div>
        </div>
      )}

      {/* Project Modal */}
      {projectModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setProjectModal({ open: false, contactId: null })} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editingProject ? "Edit Project" : "Tambah Project"}</h3>
              <button onClick={() => setProjectModal({ open: false, contactId: null })} className="p-1 text-gray-400 hover:text-gray-600"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Project</label>
                <input value={projectForm.name} onChange={e => setProjectForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Contoh: SEO Bulanan, Landing Page" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Tipe</label>
                  <select value={projectForm.type} onChange={e => setProjectForm(f => ({ ...f, type: e.target.value }))} className={inputCls}>
                    <option value="RETAINER">Retainer (Bulanan)</option>
                    <option value="FIXED">Fixed (Sekali)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Status</label>
                  <select value={projectForm.status} onChange={e => setProjectForm(f => ({ ...f, status: e.target.value }))} className={inputCls}>
                    <option value="ACTIVE">Active</option>
                    <option value="COMPLETED">Completed</option>
                    <option value="HOLD">Hold</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">{projectForm.type === "RETAINER" ? "Bayaran / Bulan (Rp)" : "Nominal Total (Rp)"}</label>
                <input type="text" value={projectForm.nominal ? formatRupiahInput(projectForm.nominal) : ""} onChange={e => setProjectForm(f => ({ ...f, nominal: cleanRupiahInput(e.target.value) }))} className={inputCls} placeholder="Rp 0" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Mulai</label>
                  <input type="date" value={projectForm.start_date} onChange={e => setProjectForm(f => ({ ...f, start_date: e.target.value }))} className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Berakhir</label>
                  <input type="date" value={projectForm.end_date} onChange={e => setProjectForm(f => ({ ...f, end_date: e.target.value }))} className={inputCls} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Jenis Layanan (Workspace)</label>
                  <select value={projectForm.service_type} onChange={e => {
                    const svc = e.target.value;
                    const match = serviceTypes.find(s => s.value === svc);
                    setProjectForm(f => ({ ...f, service_type: svc, contract_months: match?.default_months || 1 }));
                  }} className={inputCls}>
                    <option value="">— Pilih (opsional) —</option>
                    {serviceTypes.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Durasi (Bulan)</label>
                  <input type="number" min={1} max={24} value={projectForm.contract_months} onChange={e => setProjectForm(f => ({ ...f, contract_months: Number(e.target.value) }))} className={inputCls} disabled={!projectForm.service_type} />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setProjectModal({ open: false, contactId: null })} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={saveProject} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
            </div>

            {/* Existing projects for this client */}
            {projectModal.contactId && projects.filter(p => p.lead_id === projectModal.contactId).length > 0 && (
              <div className="border-t border-[var(--border-default)] pt-3">
                <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Project Existing</p>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {projects.filter(p => p.lead_id === projectModal.contactId).map(p => (
                    <div key={p.id} className="flex items-center justify-between bg-neutral-50 dark:bg-neutral-800 rounded-lg px-3 py-2">
                      <div>
                        <span className={`text-xs font-semibold ${p.status === "ACTIVE" ? "text-emerald-600" : p.status === "HOLD" ? "text-amber-600" : "text-gray-500"}`}>{p.name}</span>
                        <span className="text-[10px] text-gray-400 ml-2">{p.type} · {formatRupiah(p.nominal)}</span>
                      </div>
                      <div className="flex gap-1">
                        <button onClick={() => openProjectModal(projectModal.contactId!, p)} className="text-[10px] text-brand-yellow hover:underline">Edit</button>
                        <button onClick={() => deleteProject(p.id)} className="text-[10px] text-red-400 hover:underline">Hapus</button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Notes Modal - Per Column */}
      {notesModal.open && notesModal.contact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setNotesModal({ open: false, contact: null })} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-3xl p-6 space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Catatan — {notesModal.contact.business_name}</h3>
              <button onClick={() => setNotesModal({ open: false, contact: null })} className="p-1 text-gray-400 hover:text-gray-600"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg></button>
            </div>

            {/* Add note form */}
            <div className="flex gap-2">
              <select value={noteForm.category} onChange={e => setNoteForm(f => ({ ...f, category: e.target.value }))} className="px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-xs bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50">
                <option value="BISNIS">Bisnis</option>
                <option value="TEKNIS">Teknis</option>
                <option value="PENTING">Penting</option>
              </select>
              <input value={noteForm.content} onChange={e => setNoteForm(f => ({ ...f, content: e.target.value }))} onKeyDown={e => { if (e.key === "Enter") saveNote(); }}
                className="flex-1 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-neutral-50 dark:bg-neutral-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-yellow/50" placeholder="Tulis catatan baru..." />
              <button onClick={saveNote} className="px-4 py-2 bg-brand-yellow hover:bg-amber-600 text-white text-xs font-semibold rounded-xl transition-colors">Tambah</button>
            </div>

            {/* Notes columns */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {(["BISNIS", "TEKNIS", "PENTING"] as const).map(cat => {
                const catNotes = clientNotes.filter(n => n.category === cat);
                const colors = { BISNIS: "border-blue-200 dark:border-blue-800", TEKNIS: "border-purple-200 dark:border-purple-800", PENTING: "border-red-200 dark:border-red-800" };
                const headerColors = { BISNIS: "text-blue-600 dark:text-blue-400", TEKNIS: "text-purple-600 dark:text-purple-400", PENTING: "text-red-600 dark:text-red-400" };
                return (
                  <div key={cat} className={`border ${colors[cat]} rounded-xl p-3`}>
                    <p className={`text-xs font-bold uppercase tracking-wide mb-2 ${headerColors[cat]}`}>{cat}</p>
                    {catNotes.length === 0 ? (
                      <p className="text-xs text-gray-400 italic">Belum ada catatan.</p>
                    ) : (
                      <div className="space-y-2">
                        {catNotes.map(n => (
                          <div key={n.id} className="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-2 group">
                            <p className="text-xs text-gray-700 dark:text-gray-300">{n.content}</p>
                            <div className="flex items-center justify-between mt-1">
                              <span className="text-[10px] text-gray-400">{n.actor} · {new Date(n.timestamp).toLocaleDateString("id-ID", { day: "2-digit", month: "short" })}</span>
                              <button onClick={() => deleteNote(n.id)} className="text-[10px] text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity">Hapus</button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
