"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiFetch } from "../../../../lib/api";
import { formatRupiahInput, cleanRupiahInput } from "../../../../utils/formatter";
import { ArrowLeft, Plus, AlertTriangle, TrendingUp, CreditCard, Wallet, Eye, EyeOff, Copy, Key, FileText, ExternalLink, Trash2 } from "lucide-react";
import Toast from "../../../../components/Toast";
import Modal from "../../../../components/Modal";

interface Profile {
  id: number;
  business_name: string;
  owner_name: string | null;
  phone_number: string;
  purchased_product: string | null;
  notes: string | null;
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

interface ClientDetail {
  profile: Profile;
  ltv: number;
  active_billing: number;
  dana_talangan: number;
  projects: ProjectData[];
  notes: { id: string; category: string; content: string; actor: string; timestamp: string }[];
}

interface CredentialField {
  key: string;
  value: string;
  is_secret: boolean;
}

interface CredentialData {
  id: string;
  lead_id: number | null;
  category: string;
  title: string;
  fields: CredentialField[];
  created_at: string;
}

interface DocumentData {
  id: string;
  lead_id: number | null;
  title: string;
  cloud_url: string;
  created_at: string;
}

function formatRupiah(num: number): string {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0 }).format(num);
}

function daysLeft(dateStr: string | null): number | null {
  if (!dateStr) return null;
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
}

export default function ClientDetailPage() {
  const params = useParams();
  const router = useRouter();
  const clientId = params.client_id as string;
  const [data, setData] = useState<ClientDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // WA Smart-Snippet Drawer
  const [waDrawerOpen, setWaDrawerOpen] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  // Project modal
  const [projectModal, setProjectModal] = useState(false);
  const [projectForm, setProjectForm] = useState({ name: "", type: "RETAINER", status: "ACTIVE", nominal: 0, start_date: "", end_date: "", service_type: "", contract_months: 1 });
  const [editingProject, setEditingProject] = useState<ProjectData | null>(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; type: "project" | "note" | "credential" | "document" } | null>(null);
  const [products, setProducts] = useState<{ id: string; name: string; base_price: number; is_retainer: boolean; category_name?: string | null }[]>([]);
  const [serviceTypes, setServiceTypes] = useState<{ value: string; label: string; default_months: number }[]>([]);

  const fetchDetail = useCallback(async () => {
    try {
      const res = await apiFetch(`/api/clients/detail/${clientId}`);
      if (res.ok) setData(await res.json());
    } finally { setLoading(false); }
  }, [clientId]);

  useEffect(() => {
    fetchDetail();
    intervalRef.current = setInterval(fetchDetail, 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchDetail]);

  // Fetch products for project form selector
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

  function applyProductToProjectForm(productId: string) {
    if (!productId) return;
    const p = products.find(x => x.id === productId);
    if (!p) return;
    const cat = (p.category_name || "").toLowerCase();
    let svcType = "";
    if (cat.includes("web")) svcType = cat.includes("bulanan") ? "web_dev_bulanan" : "web_dev";
    else if (cat.includes("seo") || cat.includes("google")) svcType = "seo_gmaps";
    else if (cat.includes("sosial") || cat.includes("sosmed") || cat.includes("kelola")) svcType = "sosmed";
    else if (cat.includes("maintenance")) svcType = "maintenance";
    else if (cat.includes("logo") || cat.includes("branding") || cat.includes("desain")) svcType = "branding";
    // Fallback: try product name
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
    setProjectForm(f => ({
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

  async function saveProject() {
    if (!projectForm.name) return;
    setSaving(true);
    try {
      const method = editingProject ? "PUT" : "POST";
      const url = editingProject ? `/api/projects/${editingProject.id}` : "/api/projects";
      const res = await apiFetch(url, {
        method,
        body: JSON.stringify({ ...projectForm, lead_id: Number(clientId) }),
      });
      if (res.ok) {
        setProjectModal(false);
        setEditingProject(null);
        setProjectForm({ name: "", type: "RETAINER", status: "ACTIVE", nominal: 0, start_date: "", end_date: "", service_type: "", contract_months: 1 });
        fetchDetail();
      }
    } finally { setSaving(false); }
  }

  function openEditProject(p: ProjectData) {
    setEditingProject(p);
    setProjectForm({ name: p.name, type: p.type, status: p.status, nominal: p.nominal, start_date: p.start_date || "", end_date: p.end_date || "", service_type: p.service_type || "", contract_months: p.contract_months || 1 });
    setProjectModal(true);
  }

  function openNewProject() {
    setEditingProject(null);
    setProjectForm({ name: "", type: "RETAINER", status: "ACTIVE", nominal: 0, start_date: new Date().toISOString().slice(0, 10), end_date: "", service_type: "", contract_months: 1 });
    setProjectModal(true);
  }

  async function deleteProject(projectId: string) {
    const res = await apiFetch(`/api/projects/${projectId}`, { method: "DELETE" });
    if (res.ok) {
      setToast({ message: "Project dihapus.", type: "success" });
      fetchDetail();
    } else {
      setToast({ message: "Gagal hapus project.", type: "error" });
    }
    setDeleteTarget(null);
  }

  const inputCls = "input-field";

  if (loading) {
    return (
      <div className="max-w-5xl space-y-6">
        <div className="h-8 bg-neutral-100 dark:bg-neutral-800 rounded w-48 animate-pulse" />
        <div className="grid grid-cols-3 gap-4">{[1, 2, 3].map(i => <div key={i} className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-2xl animate-pulse" />)}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-5xl text-center py-20">
        <p className="text-neutral-500">Klien tidak ditemukan.</p>
        <button onClick={() => router.push("/clients")} className="btn-secondary mt-4">Kembali</button>
      </div>
    );
  }

  const { profile, ltv, active_billing, dana_talangan, projects } = data;
  const isVIP = ltv >= 10000000;

  return (
    <div className="max-w-5xl space-y-6">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
      <Modal
        open={deleteTarget?.type === "project"}
        title="Hapus Project?"
        message="Project yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteTarget && deleteProject(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
      />
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => router.push("/clients")} className="p-2 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-xl transition-all">
          <ArrowLeft size={20} />
        </button>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">{profile.business_name}</h1>
            {isVIP && <span className="px-2.5 py-0.5 bg-brand-yellow/10 text-brand-yellow text-[10px] font-bold uppercase rounded-full">VIP Client</span>}
          </div>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
            {profile.owner_name || "—"} · +{profile.phone_number} · {profile.purchased_product || "—"}
          </p>
        </div>
      </div>

      {/* Blok A: Financial Snapshot */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* LTV Card */}
        <div className={`card p-5 ${isVIP ? "ring-2 ring-brand-yellow/30" : ""}`}>
          <div className="flex items-center gap-2 mb-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${isVIP ? "bg-brand-yellow/10" : "bg-emerald-50 dark:bg-emerald-900/20"}`}>
              <TrendingUp size={18} className={isVIP ? "text-brand-yellow" : "text-emerald-600 dark:text-emerald-400"} />
            </div>
            <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">Lifetime Value</span>
          </div>
          <p className={`text-2xl font-bold ${isVIP ? "text-brand-yellow" : "text-neutral-900 dark:text-neutral-50"}`}>{formatRupiah(ltv)}</p>
          <p className="text-[11px] text-neutral-400 dark:text-neutral-500 mt-1">Total dari semua proyek aktif & selesai</p>
        </div>

        {/* Active Billing Card */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
              <CreditCard size={18} className="text-blue-600 dark:text-blue-400" />
            </div>
            <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">Billing Aktif</span>
          </div>
          <p className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">{formatRupiah(active_billing)}</p>
          <p className="text-[11px] text-neutral-400 dark:text-neutral-500 mt-1">Proyek berstatus ACTIVE saat ini</p>
        </div>

        {/* Dana Talangan Card */}
        <div className={`card p-5 ${dana_talangan > 0 ? "ring-2 ring-red-300/50 dark:ring-red-700/50" : ""}`}>
          <div className="flex items-center gap-2 mb-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${dana_talangan > 0 ? "bg-red-50 dark:bg-red-900/20" : "bg-neutral-50 dark:bg-neutral-800"}`}>
              <Wallet size={18} className={dana_talangan > 0 ? "text-red-600 dark:text-red-400" : "text-neutral-400"} />
            </div>
            <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">Dana Talangan</span>
          </div>
          <p className={`text-2xl font-bold ${dana_talangan > 0 ? "text-red-600 dark:text-red-400" : "text-neutral-900 dark:text-neutral-50"}`}>{formatRupiah(dana_talangan)}</p>
          {dana_talangan > 0 && (
            <div className="flex items-center gap-1 mt-2">
              <AlertTriangle size={12} className="text-red-500" />
              <span className="text-[11px] text-red-600 dark:text-red-400 font-medium">Belum ditagihkan ke klien!</span>
            </div>
          )}
          {dana_talangan === 0 && <p className="text-[11px] text-neutral-400 dark:text-neutral-500 mt-1">Tidak ada dana talangan</p>}
        </div>
      </div>

      {/* Blok B: Project Management */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
          <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Proyek Klien</h2>
          <button onClick={openNewProject} className="btn-primary flex items-center gap-1.5 text-xs">
            <Plus size={14} /> Tambah Proyek Baru
          </button>
        </div>

        {projects.length === 0 ? (
          <div className="text-center py-12 text-neutral-400 text-sm">Belum ada proyek untuk klien ini.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 dark:bg-neutral-800 border-b border-[var(--border-default)]">
                <tr>
                  {["Nama Proyek", "Tipe", "Status", "Nominal", "Mulai", "Berakhir", "Sisa", "Aksi"].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {projects.map(p => {
                  const remaining = daysLeft(p.end_date);
                  return (
                    <tr key={p.id} className="table-row-hover">
                      <td className="px-4 py-3 font-semibold text-neutral-800 dark:text-neutral-200">{p.name}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${p.type === "RETAINER" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"}`}>
                          {p.type}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${p.status === "ACTIVE" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : p.status === "HOLD" ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" : "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"}`}>
                          {p.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-semibold text-neutral-800 dark:text-neutral-200">
                        {formatRupiah(p.nominal)}
                        <span className="text-[10px] text-neutral-400 ml-1">{p.type === "RETAINER" ? "/bln" : ""}</span>
                      </td>
                      <td className="px-4 py-3 text-xs text-neutral-500">{p.start_date || "—"}</td>
                      <td className="px-4 py-3 text-xs text-neutral-500">{p.end_date || "—"}</td>
                      <td className="px-4 py-3">
                        {remaining !== null ? (
                          <span className={`text-xs font-semibold ${remaining <= 7 ? "text-red-600 dark:text-red-400" : remaining <= 14 ? "text-amber-600 dark:text-amber-400" : "text-neutral-500"}`}>
                            {remaining <= 0 ? "Expired" : `${remaining} hari`}
                          </span>
                        ) : <span className="text-xs text-neutral-400">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <button onClick={() => openEditProject(p)} className="p-1.5 text-neutral-400 hover:text-brand-yellow rounded-lg transition-colors">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                          </button>
                          <button onClick={() => setDeleteTarget({ id: p.id, type: "project" })} className="p-1.5 text-neutral-400 hover:text-red-500 rounded-lg transition-colors">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14H6L5 6" /><path d="M10 11v6" /><path d="M14 11v6" /><path d="M9 6V4h6v2" /></svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Blok C: Tabs - Notes / Credentials / Documents */}
      <ClientTabs clientId={Number(clientId)} initialNotes={data.notes} />

      {/* Project Modal */}
      {projectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setProjectModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-modal border border-[var(--border-default)] w-full max-w-md p-6 space-y-4 animate-slide-up">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editingProject ? "Edit Proyek" : "Tambah Proyek Baru"}</h3>
              <button onClick={() => setProjectModal(false)} className="p-1 text-neutral-400 hover:text-neutral-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>
            <div className="space-y-3">
              {!editingProject && products.length > 0 && (
                <div>
                  <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Pilih dari Paket</label>
                  <select onChange={e => applyProductToProjectForm(e.target.value)} className={inputCls} defaultValue="">
                    <option value="">— Custom (isi manual) —</option>
                    {products.map(p => <option key={p.id} value={p.id}>{p.name} — {new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0 }).format(p.base_price)}{p.is_retainer ? "/bln" : ""}</option>)}
                  </select>
                </div>
              )}
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Nama Proyek</label>
                <input value={projectForm.name} onChange={e => setProjectForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Contoh: SEO Bulanan, Landing Page" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Tipe</label>
                  <select value={projectForm.type} onChange={e => setProjectForm(f => ({ ...f, type: e.target.value }))} className={inputCls}>
                    <option value="RETAINER">Retainer (Bulanan)</option>
                    <option value="FIXED">Fixed (Sekali)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Status</label>
                  <select value={projectForm.status} onChange={e => setProjectForm(f => ({ ...f, status: e.target.value }))} className={inputCls}>
                    <option value="ACTIVE">Active</option>
                    <option value="COMPLETED">Completed</option>
                    <option value="HOLD">Hold</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">{projectForm.type === "RETAINER" ? "Bayaran / Bulan (Rp)" : "Nominal Total (Rp)"}</label>
                <input type="text" value={projectForm.nominal ? formatRupiahInput(projectForm.nominal) : ""} onChange={e => setProjectForm(f => ({ ...f, nominal: cleanRupiahInput(e.target.value) }))} className={inputCls} placeholder="Rp 0" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Mulai</label>
                  <input type="date" value={projectForm.start_date} onChange={e => setProjectForm(f => ({ ...f, start_date: e.target.value }))} className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Berakhir</label>
                  <input type="date" value={projectForm.end_date} onChange={e => setProjectForm(f => ({ ...f, end_date: e.target.value }))} className={inputCls} />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setProjectModal(false)} className="btn-ghost">Batal</button>
              <button onClick={saveProject} disabled={saving} className="btn-primary">
                {saving ? "Menyimpan..." : "Simpan Proyek"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* WA Smart-Snippet Keyboard Trigger Button */}
      <button
        onClick={() => setWaDrawerOpen(true)}
        className="fixed bottom-6 right-6 z-40 bg-green-500 hover:bg-green-600 text-white rounded-full p-4 shadow-lg transition-colors"
        title="Laci Balasan Cepat WA"
      >
        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
        </svg>
      </button>

      {/* WA Smart-Snippet Drawer */}
      {waDrawerOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setWaDrawerOpen(false)} />
          <div className="relative w-full max-w-sm bg-[var(--bg-surface)] border-l border-[var(--border-default)] shadow-xl h-full overflow-y-auto">
            <div className="p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Laci Balasan Cepat WA</h3>
                <button onClick={() => setWaDrawerOpen(false)} className="p-1 text-neutral-400 hover:text-neutral-600">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                </button>
              </div>
              <p className="text-xs text-neutral-500">Klik tombol untuk menyalin teks balasan ke clipboard, lalu paste ke WhatsApp.</p>

              <div className="space-y-3">
                {[
                  {
                    label: "Objection: Kemahalan",
                    getText: () => `Pak, saya paham pertimbangannya. Tapi coba kita hitung bersama: setiap bulan ada ratusan calon pelanggan di kota Bapak yang mencari jasa ${data?.profile?.purchased_product || "seperti bisnis Bapak"} di Google. Tanpa website yang teroptimasi, semua calon pelanggan itu lari ke kompetitor. Investasi perbaikan web ini jauh lebih kecil dibanding potensi omzet ratusan juta yang hilang setiap bulannya ke kompetitor. Ini bukan biaya, tapi investasi yang ROI-nya bisa dihitung langsung di kalkulator laporan audit kemarin.`,
                  },
                  {
                    label: "Objection: Mau Diskusi Dulu",
                    getText: () => `Silakan Pak, justru laporan itu sengaja saya desain rapi agar bisa Bapak share ke partner bisnis menggunakan tombol khusus di samping tombol WA utama halaman kemarin. Silakan ditinjau bersama kalkulator proyeksinya, besok siang saya kabari lagi ya Pak untuk slot wilayahnya.`,
                  },
                  {
                    label: "Follow-Up: Belum Buka Link",
                    getText: () => `Halo Pak, saya notice laporan audit digital untuk ${data?.profile?.business_name || "bisnis Bapak"} belum dibuka. Laporan ini ada timer 24 jam untuk harga spesial. Mau saya kirim ulang linknya sekarang?`,
                  },
                  {
                    label: "Closing: Konfirmasi Deal",
                    getText: () => `Baik Pak, terima kasih atas kepercayaannya. Saya akan segera proses onboarding untuk ${data?.profile?.business_name || "bisnis Bapak"}. Tim teknis kami akan mulai audit mendalam dalam 1x24 jam. Ada yang perlu ditanyakan sebelum kita mulai?`,
                  },
                ].map((snippet, idx) => (
                  <button
                    key={idx}
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(snippet.getText());
                        setCopiedIdx(idx);
                        setTimeout(() => setCopiedIdx(null), 2000);
                      } catch {}
                    }}
                    className="w-full text-left p-3 rounded-lg border border-[var(--border-default)] hover:bg-green-50 dark:hover:bg-green-900/10 transition-colors group"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{snippet.label}</span>
                      {copiedIdx === idx ? (
                        <span className="text-xs text-green-600 font-medium">Disalin!</span>
                      ) : (
                        <Copy className="w-3.5 h-3.5 text-neutral-400 group-hover:text-green-500" />
                      )}
                    </div>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2">{snippet.getText()}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Client Tabs Component (Notes / Credentials / Documents)
// ---------------------------------------------------------------------------

function ClientTabs({ clientId, initialNotes }: { clientId: number; initialNotes: NoteData[] }) {
  const [activeTab, setActiveTab] = useState<"notes" | "credentials" | "documents">("notes");

  const tabs = [
    { key: "notes" as const, label: "Timeline Notes", icon: <FileText size={14} /> },
    { key: "credentials" as const, label: "Kredensial & Akses", icon: <Key size={14} /> },
    { key: "documents" as const, label: "Dokumen & Media", icon: <ExternalLink size={14} /> },
  ];

  return (
    <div className="card overflow-hidden">
      {/* Tab Headers */}
      <div className="px-5 py-3 border-b border-[var(--border-default)] flex items-center gap-1 bg-neutral-50/50 dark:bg-neutral-800/30">
        {tabs.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 ${activeTab === tab.key ? "bg-brand-yellow/10 text-brand-yellow shadow-sm" : "text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-700 dark:hover:text-neutral-200"}`}>
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "notes" && <NotesTimeline clientId={clientId} initialNotes={initialNotes} />}
      {activeTab === "credentials" && <CredentialsTab clientId={clientId} />}
      {activeTab === "documents" && <DocumentsTab clientId={clientId} />}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Notes Timeline Component
// ---------------------------------------------------------------------------

interface NoteData {
  id: string;
  category: string;
  content: string;
  actor: string;
  timestamp: string;
}

const CATEGORY_BADGE: Record<string, string> = {
  BISNIS: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  TEKNIS: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  PENTING: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

function NotesTimeline({ clientId, initialNotes }: { clientId: number; initialNotes: NoteData[] }) {
  const [notes, setNotes] = useState<NoteData[]>(initialNotes);
  const [filter, setFilter] = useState<"ALL" | "BISNIS" | "TEKNIS" | "PENTING">("ALL");
  const [form, setForm] = useState({ category: "BISNIS", content: "" });
  const [submitting, setSubmitting] = useState(false);
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
  const [noteToast, setNoteToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  useEffect(() => { setNotes(initialNotes); }, [initialNotes]);

  async function submitNote() {
    if (!form.content.trim()) return;
    setSubmitting(true);
    try {
      const res = await apiFetch("/api/clients/notes", {
        method: "POST",
        body: JSON.stringify({ lead_id: clientId, category: form.category, content: form.content }),
      });
      if (res.ok) {
        const newNote = await res.json();
        setNotes(prev => [newNote, ...prev]);
        setForm(f => ({ ...f, content: "" }));
      }
    } finally { setSubmitting(false); }
  }

  async function deleteNote(noteId: string) {
    const res = await apiFetch(`/api/client-notes/${noteId}`, { method: "DELETE" });
    if (res.ok) {
      setNoteToast({ message: "Catatan dihapus.", type: "success" });
      setNotes(prev => prev.filter(n => n.id !== noteId));
    } else {
      setNoteToast({ message: "Gagal hapus catatan.", type: "error" });
    }
    setDeleteNoteId(null);
  }

  const filtered = filter === "ALL" ? notes : notes.filter(n => n.category === filter);

  return (
    <div>
      <Toast message={noteToast?.message ?? null} type={noteToast?.type} onClose={() => setNoteToast(null)} />
      <Modal
        open={!!deleteNoteId}
        title="Hapus Catatan?"
        message="Catatan yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteNoteId && deleteNote(deleteNoteId)}
        onCancel={() => setDeleteNoteId(null)}
      />
      <div className="px-5 py-4 border-b border-[var(--border-default)]">
        <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Catatan & Timeline</h2>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">Riwayat catatan kronologis untuk klien ini.</p>
      </div>

      {/* Input Form */}
      <div className="px-5 py-4 border-b border-[var(--border-subtle)] bg-neutral-50/50 dark:bg-neutral-800/30">
        <div className="flex gap-3">
          <div className="flex-1">
            <textarea
              value={form.content}
              onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submitNote(); } }}
              rows={2}
              placeholder="Tulis catatan baru... (Enter untuk kirim, Shift+Enter untuk baris baru)"
              className="input-field resize-none"
            />
          </div>
          <div className="flex flex-col gap-2 shrink-0">
            <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
              className="px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-xl text-xs bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 focus:outline-none focus:ring-2 focus:ring-amber-300">
              <option value="BISNIS">Bisnis</option>
              <option value="TEKNIS">Teknis</option>
              <option value="PENTING">Penting</option>
            </select>
            <button onClick={submitNote} disabled={submitting || !form.content.trim()} className="btn-primary text-xs px-3 py-2 disabled:opacity-50">
              {submitting ? "..." : "Kirim"}
            </button>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="px-5 py-3 border-b border-[var(--border-subtle)] flex items-center gap-2">
        {(["ALL", "BISNIS", "TEKNIS", "PENTING"] as const).map(cat => (
          <button key={cat} onClick={() => setFilter(cat)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${filter === cat ? "bg-brand-yellow/10 text-brand-yellow" : "text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}>
            {cat === "ALL" ? "Semua" : cat.charAt(0) + cat.slice(1).toLowerCase()}
          </button>
        ))}
        <span className="ml-auto text-[11px] text-neutral-400">{filtered.length} catatan</span>
      </div>

      {/* Notes Feed */}
      <div className="divide-y divide-[var(--border-subtle)] max-h-[400px] overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="text-center py-10 text-neutral-400 text-sm">Belum ada catatan.</div>
        ) : (
          filtered.map(note => (
            <div key={note.id} className="px-5 py-4 hover:bg-[var(--bg-surface-hover)] transition-colors group">
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <div className={`w-2.5 h-2.5 rounded-full ${note.category === "BISNIS" ? "bg-emerald-500" : note.category === "TEKNIS" ? "bg-blue-500" : "bg-red-500"}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${CATEGORY_BADGE[note.category] || CATEGORY_BADGE.BISNIS}`}>
                      {note.category}
                    </span>
                    <span className="text-[11px] text-neutral-400">{note.actor}</span>
                  </div>
                  <p className="text-sm text-neutral-800 dark:text-neutral-200 leading-relaxed whitespace-pre-wrap">{note.content}</p>
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <span className="text-[10px] text-neutral-400">
                    {new Date(note.timestamp).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}
                  </span>
                  <span className="text-[10px] text-neutral-400">
                    {new Date(note.timestamp).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}
                  </span>
                  <button onClick={() => setDeleteNoteId(note.id)} className="text-[10px] text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity mt-1">
                    Hapus
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// Credentials Tab Component
// ---------------------------------------------------------------------------

function CredentialsTab({ clientId }: { clientId: number }) {
  const [credentials, setCredentials] = useState<CredentialData[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [visibleFields, setVisibleFields] = useState<Set<string>>(new Set());
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [formCategory, setFormCategory] = useState("");
  const [formTitle, setFormTitle] = useState("");
  const [formFields, setFormFields] = useState<CredentialField[]>([{ key: "", value: "", is_secret: false }]);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [catDropdownOpen, setCatDropdownOpen] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [editingCat, setEditingCat] = useState<string | null>(null);
  const [editingCatValue, setEditingCatValue] = useState("");
  const [deleteCredId, setDeleteCredId] = useState<string | null>(null);
  const [credToast, setCredToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await apiFetch("/api/credential-categories");
      if (res.ok) setCategories(await res.json());
    } catch { /* non-critical */ }
  }, []);

  async function deleteCategory(cat: string) {
    const updated = categories.filter(c => c !== cat);
    setCategories(updated);
    await apiFetch("/api/credential-categories", { method: "PUT", body: JSON.stringify(updated) });
  }

  async function renameCategory(oldName: string, newName: string) {
    if (!newName.trim() || newName.trim() === oldName) { setEditingCat(null); return; }
    const updated = categories.map(c => c === oldName ? newName.trim() : c);
    setCategories(updated);
    setEditingCat(null);
    await apiFetch("/api/credential-categories", { method: "PUT", body: JSON.stringify(updated) });
  }

  const fetchCredentials = useCallback(async () => {
    try {
      const res = await apiFetch(`/api/credentials?lead_id=${clientId}`);
      if (res.ok) setCredentials(await res.json());
    } finally { setLoading(false); }
  }, [clientId]);

  useEffect(() => { fetchCredentials(); fetchCategories(); }, [fetchCredentials, fetchCategories]);

  function toggleFieldVisibility(fieldKey: string) {
    setVisibleFields(prev => {
      const next = new Set(prev);
      if (next.has(fieldKey)) next.delete(fieldKey); else next.add(fieldKey);
      return next;
    });
  }

  async function copyToClipboard(text: string, id: string) {
    await navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  function openNew() {
    setEditingId(null);
    setFormCategory("");
    setFormTitle("");
    setFormFields([{ key: "Username", value: "", is_secret: false }, { key: "Password", value: "", is_secret: true }]);
    setShowModal(true);
  }

  function openEdit(cred: CredentialData) {
    setEditingId(cred.id);
    setFormCategory(cred.category);
    setFormTitle(cred.title);
    setFormFields(cred.fields.length > 0 ? cred.fields.map(f => ({ ...f })) : [{ key: "", value: "", is_secret: false }]);
    setShowModal(true);
  }

  function addField() {
    setFormFields(prev => [...prev, { key: "", value: "", is_secret: false }]);
  }

  function removeField(idx: number) {
    setFormFields(prev => prev.filter((_, i) => i !== idx));
  }

  function updateField(idx: number, patch: Partial<CredentialField>) {
    setFormFields(prev => prev.map((f, i) => i === idx ? { ...f, ...patch } : f));
  }

  async function saveCredential() {
    if (!formTitle || !formCategory || formFields.length === 0) return;
    const validFields = formFields.filter(f => f.key.trim() && f.value.trim());
    if (validFields.length === 0) return;
    setSaving(true);
    try {
      const method = editingId ? "PUT" : "POST";
      const url = editingId ? `/api/credentials/${editingId}` : "/api/credentials";
      const payload = { category: formCategory, title: formTitle, fields: validFields, lead_id: clientId };
      const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
      if (res.ok) {
        setShowModal(false);
        fetchCredentials();
      }
    } finally { setSaving(false); }
  }

  async function deleteCredential(id: string) {
    const res = await apiFetch(`/api/credentials/${id}`, { method: "DELETE" });
    if (res.ok) {
      setCredToast({ message: "Kredensial dihapus.", type: "success" });
      setCredentials(prev => prev.filter(c => c.id !== id));
    } else {
      setCredToast({ message: "Gagal hapus kredensial.", type: "error" });
    }
    setDeleteCredId(null);
  }

  if (loading) {
    return <div className="p-6"><div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl animate-pulse" /></div>;
  }

  return (
    <div>
      <Toast message={credToast?.message ?? null} type={credToast?.type} onClose={() => setCredToast(null)} />
      <Modal
        open={!!deleteCredId}
        title="Hapus Kredensial?"
        message="Kredensial yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteCredId && deleteCredential(deleteCredId)}
        onCancel={() => setDeleteCredId(null)}
      />
      <div className="px-5 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Kredensial & Akses</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">Akun login milik klien ini (terenkripsi).</p>
        </div>
        <button onClick={openNew} className="btn-primary flex items-center gap-1.5 text-xs">
          <Plus size={14} /> Tambah
        </button>
      </div>

      {credentials.length === 0 ? (
        <div className="text-center py-12 text-neutral-400 text-sm">Belum ada kredensial tersimpan.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-5">
          {credentials.map(cred => (
            <div key={cred.id} className="card p-4 space-y-3 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                    {cred.category}
                  </span>
                  <h3 className="text-sm font-bold text-neutral-900 dark:text-neutral-50 mt-1.5">{cred.title}</h3>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(cred)} className="p-1.5 text-neutral-400 hover:text-brand-yellow rounded-lg transition-colors">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                  </button>
                  <button onClick={() => setDeleteCredId(cred.id)} className="p-1.5 text-neutral-400 hover:text-red-500 rounded-lg transition-colors">
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                {cred.fields.map((field, idx) => (
                  <div key={idx}>
                    <span className="text-[10px] text-neutral-400 uppercase font-semibold">{field.key}</span>
                    <div className="flex items-center gap-2">
                      <p className="text-sm text-neutral-800 dark:text-neutral-200 font-mono break-all">
                        {field.is_secret && !visibleFields.has(`${cred.id}-${idx}`) ? "••••••••" : field.value}
                      </p>
                      {field.is_secret && (
                        <button onClick={() => toggleFieldVisibility(`${cred.id}-${idx}`)} className="p-1 text-neutral-400 hover:text-brand-yellow transition-colors">
                          {visibleFields.has(`${cred.id}-${idx}`) ? <EyeOff size={12} /> : <Eye size={12} />}
                        </button>
                      )}
                      <button onClick={() => copyToClipboard(field.value, `${cred.id}-${idx}`)} className="p-1 text-neutral-400 hover:text-brand-yellow transition-colors">
                        <Copy size={12} />
                      </button>
                      {copiedId === `${cred.id}-${idx}` && <span className="text-[10px] text-emerald-500">Copied!</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Credential Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-modal border border-[var(--border-default)] w-full max-w-lg p-6 space-y-4 animate-slide-up max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editingId ? "Edit Kredensial" : "Tambah Kredensial"}</h3>
              <button onClick={() => setShowModal(false)} className="p-1 text-neutral-400 hover:text-neutral-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Kategori</label>
                <div className="relative">
                  <input
                    value={formCategory}
                    onChange={e => { setFormCategory(e.target.value); setCatDropdownOpen(true); }}
                    onFocus={() => setCatDropdownOpen(true)}
                    onBlur={() => { if (!editingCat) setTimeout(() => setCatDropdownOpen(false), 150); }}
                    className="input-field"
                    placeholder="Ketik atau pilih kategori..."
                  />
                  {catDropdownOpen && (() => {
                    const filtered = categories.filter(c => c.toLowerCase().includes(formCategory.toLowerCase()));
                    const showAddNew = formCategory.trim() && !categories.some(c => c.toLowerCase() === formCategory.trim().toLowerCase());
                    if (filtered.length === 0 && !showAddNew) return null;
                    return (
                      <div className="absolute z-10 top-full left-0 right-0 mt-1 bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl shadow-lg max-h-40 overflow-y-auto">
                        {filtered.map(cat => (
                          <div key={cat} className="flex items-center justify-between px-3 py-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
                            {editingCat === cat ? (
                              <input
                                autoFocus
                                value={editingCatValue}
                                onChange={e => setEditingCatValue(e.target.value)}
                                onBlur={() => renameCategory(cat, editingCatValue)}
                                onKeyDown={e => { if (e.key === "Enter") renameCategory(cat, editingCatValue); if (e.key === "Escape") setEditingCat(null); }}
                                onMouseDown={e => e.stopPropagation()}
                                className="flex-1 text-sm px-1 py-0.5 border border-brand-yellow rounded bg-transparent text-neutral-800 dark:text-neutral-200 outline-none"
                              />
                            ) : (
                              <button type="button" onMouseDown={() => { setFormCategory(cat); setCatDropdownOpen(false); }}
                                className="flex-1 text-left text-sm text-neutral-700 dark:text-neutral-300">
                                {cat}
                              </button>
                            )}
                            <div className="flex items-center gap-0.5 shrink-0 ml-1">
                              <button type="button" onMouseDown={e => { e.preventDefault(); e.stopPropagation(); setEditingCat(cat); setEditingCatValue(cat); }}
                                className="p-1 text-neutral-300 hover:text-brand-yellow transition-colors">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                              </button>
                              <button type="button" onMouseDown={e => { e.preventDefault(); e.stopPropagation(); deleteCategory(cat); }}
                                className="p-1 text-neutral-300 hover:text-red-500 transition-colors">
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </div>
                        ))}
                        {showAddNew && (
                          <button type="button" onMouseDown={() => { const updated = [...categories, formCategory.trim()]; setCategories(updated); apiFetch("/api/credential-categories", { method: "PUT", body: JSON.stringify(updated) }); setCatDropdownOpen(false); }}
                            className="w-full text-left px-3 py-2 text-sm text-brand-yellow font-semibold hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors">
                            + Tambah &quot;{formCategory.trim()}&quot;
                          </button>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Judul / Label</label>
                <input value={formTitle} onChange={e => setFormTitle(e.target.value)} className="input-field" placeholder="cPanel Hosting Utama" />
              </div>

              {/* Dynamic Key-Value Fields */}
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-2">Fields</label>
                <div className="space-y-2">
                  {formFields.map((field, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <input
                        value={field.key}
                        onChange={e => updateField(idx, { key: e.target.value })}
                        className="input-field flex-1"
                        placeholder="Key (Username, Password, API Key...)"
                      />
                      <input
                        type={field.is_secret ? "password" : "text"}
                        value={field.value}
                        onChange={e => updateField(idx, { value: e.target.value })}
                        className="input-field flex-[2]"
                        placeholder="Value"
                      />
                      <button
                        type="button"
                        onClick={() => updateField(idx, { is_secret: !field.is_secret })}
                        className={`p-2 rounded-lg border transition-colors shrink-0 ${field.is_secret ? "border-amber-300 bg-amber-50 dark:bg-amber-900/20 text-amber-600" : "border-neutral-200 dark:border-neutral-700 text-neutral-400 hover:text-neutral-600"}`}
                        title={field.is_secret ? "Sensitif (terenkripsi)" : "Biasa (tidak terenkripsi)"}
                      >
                        {field.is_secret ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                      {formFields.length > 1 && (
                        <button type="button" onClick={() => removeField(idx)} className="p-2 text-neutral-400 hover:text-red-500 transition-colors shrink-0">
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                <button type="button" onClick={addField} className="mt-2 text-xs text-brand-yellow hover:text-amber-600 font-semibold flex items-center gap-1">
                  <Plus size={12} /> Tambah Field
                </button>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowModal(false)} className="btn-ghost">Batal</button>
              <button onClick={saveCredential} disabled={saving} className="btn-primary">
                {saving ? "Menyimpan..." : "Simpan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Documents Tab Component
// ---------------------------------------------------------------------------

function DocumentsTab({ clientId }: { clientId: number }) {
  const [documents, setDocuments] = useState<DocumentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ title: "", cloud_url: "" });
  const [saving, setSaving] = useState(false);
  const [deleteDocId, setDeleteDocId] = useState<string | null>(null);
  const [docToast, setDocToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await apiFetch(`/api/documents?lead_id=${clientId}`);
      if (res.ok) setDocuments(await res.json());
    } finally { setLoading(false); }
  }, [clientId]);

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

  async function saveDocument() {
    if (!form.title || !form.cloud_url) return;
    setSaving(true);
    try {
      const res = await apiFetch("/api/documents", {
        method: "POST",
        body: JSON.stringify({ ...form, lead_id: clientId }),
      });
      if (res.ok) {
        setShowModal(false);
        setForm({ title: "", cloud_url: "" });
        fetchDocuments();
      }
    } finally { setSaving(false); }
  }

  async function deleteDocument(id: string) {
    const res = await apiFetch(`/api/documents/${id}`, { method: "DELETE" });
    if (res.ok) {
      setDocToast({ message: "Dokumen dihapus.", type: "success" });
      setDocuments(prev => prev.filter(d => d.id !== id));
    } else {
      setDocToast({ message: "Gagal hapus dokumen.", type: "error" });
    }
    setDeleteDocId(null);
  }

  if (loading) {
    return <div className="p-6"><div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl animate-pulse" /></div>;
  }

  return (
    <div>
      <Toast message={docToast?.message ?? null} type={docToast?.type} onClose={() => setDocToast(null)} />
      <Modal
        open={!!deleteDocId}
        title="Hapus Dokumen?"
        message="Dokumen yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteDocId && deleteDocument(deleteDocId)}
        onCancel={() => setDeleteDocId(null)}
      />
      <div className="px-5 py-4 border-b border-[var(--border-default)] flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Dokumen & Media</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">Link dokumen cloud milik klien ini.</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-1.5 text-xs">
          <Plus size={14} /> Tambah
        </button>
      </div>

      {documents.length === 0 ? (
        <div className="text-center py-12 text-neutral-400 text-sm">Belum ada dokumen tersimpan.</div>
      ) : (
        <div className="divide-y divide-[var(--border-subtle)]">
          {documents.map(doc => (
            <div key={doc.id} className="px-5 py-4 flex items-center justify-between hover:bg-[var(--bg-surface-hover)] transition-colors group">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center shrink-0">
                  <FileText size={16} className="text-blue-600 dark:text-blue-400" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{doc.title}</p>
                  <a href={doc.cloud_url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 dark:text-blue-400 hover:underline truncate block">
                    {doc.cloud_url}
                  </a>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[10px] text-neutral-400">
                  {new Date(doc.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}
                </span>
                <button onClick={() => setDeleteDocId(doc.id)} className="p-1.5 text-neutral-400 hover:text-red-500 rounded-lg transition-colors opacity-0 group-hover:opacity-100">
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Document Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setShowModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-modal border border-[var(--border-default)] w-full max-w-md p-6 space-y-4 animate-slide-up">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Tambah Dokumen</h3>
              <button onClick={() => setShowModal(false)} className="p-1 text-neutral-400 hover:text-neutral-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Judul Dokumen</label>
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} className="input-field" placeholder="Desain Logo Final" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Cloud URL</label>
                <input value={form.cloud_url} onChange={e => setForm(f => ({ ...f, cloud_url: e.target.value }))} className="input-field" placeholder="https://drive.google.com/..." />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowModal(false)} className="btn-ghost">Batal</button>
              <button onClick={saveDocument} disabled={saving} className="btn-primary">
                {saving ? "Menyimpan..." : "Simpan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
