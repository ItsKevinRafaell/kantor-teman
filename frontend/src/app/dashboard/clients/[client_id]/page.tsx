"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiFetch } from "../../../../lib/api";
import { formatRupiah } from "../../../../utils/formatter";
import { Plus, AlertTriangle, TrendingUp, CreditCard, Wallet } from "lucide-react";
import Toast from "../../../../components/Toast";
import Modal from "../../../../components/Modal";
import Breadcrumb from "../../../../components/Breadcrumb";
import ClientTabs from "./components/ClientTabs";
import ProjectModal, { DEFAULT_PROJECT_FORM } from "./components/ProjectModal";
import WASnippetDrawer, { WA_SNIPPETS } from "./components/WASnippetDrawer";

interface Profile {
  id: number;
  lead_id?: number | null;
  business_name: string;
  owner_name: string | null;
  phone_number: string;
  purchased_product: string | null;
  notes: string | null;
}

interface ProjectData {
  id: string;
  lead_id?: number | null;
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
  lead_id?: number | null;
  profile: Profile;
  ltv: number;
  active_billing: number;
  dana_talangan: number;
  projects: ProjectData[];
  notes: { id: string; category: string; content: string; actor: string; timestamp: string }[];
}

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

  // WA drawer
  const [waDrawerOpen, setWaDrawerOpen] = useState(false);

  // Project modal
  const [projectModal, setProjectModal] = useState(false);
  const [projectForm, setProjectForm] = useState(DEFAULT_PROJECT_FORM);
  const [editingProject, setEditingProject] = useState<ProjectData | null>(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; type: "project" | "note" | "credential" | "document" } | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [serviceTypes, setServiceTypes] = useState<ServiceType[]>([]);

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

  async function saveProject() {
    if (!projectForm.name) return;
    setSaving(true);
    try {
      const method = editingProject ? "PUT" : "POST";
      const url = editingProject ? `/api/projects/${editingProject.id}` : "/api/projects";
      const res = await apiFetch(url, {
        method,
        body: JSON.stringify({ ...projectForm, contact_id: Number(clientId) }),
      });
      if (res.ok) {
        setProjectModal(false);
        setEditingProject(null);
        setProjectForm(DEFAULT_PROJECT_FORM);
        fetchDetail();
      }
    } finally { setSaving(false); }
  }

  function openEditProject(p: ProjectData) {
    setEditingProject(p);
    setProjectForm({
      name: p.name,
      type: p.type,
      status: p.status,
      nominal: p.nominal,
      start_date: p.start_date || "",
      end_date: p.end_date || "",
      service_type: p.service_type || "",
      contract_months: p.contract_months || 1,
    });
    setProjectModal(true);
  }

  function openNewProject() {
    setEditingProject(null);
    setProjectForm({ ...DEFAULT_PROJECT_FORM, start_date: new Date().toISOString().slice(0, 10) });
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
  const clientLeadId = data.lead_id ?? profile.lead_id ?? null;
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
        <div>
          <Breadcrumb items={[{ label: "Buku Klien", href: "/clients" }, { label: profile.business_name }]} showBack backHref="/clients" />
          <div className="flex items-center gap-3 mt-1">
            <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-50">{profile.business_name}</h1>
            {isVIP && <span className="px-2.5 py-0.5 bg-brand-yellow/10 text-brand-yellow text-[10px] font-bold uppercase rounded-full">VIP Client</span>}
          </div>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
            {profile.owner_name || "—"} · +{profile.phone_number} · {profile.purchased_product || "—"}
          </p>
        </div>
      </div>

      {/* Blok A: Financial Snapshot */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

      {/* Blok C: Tabs */}
      <ClientTabs leadId={clientLeadId} initialNotes={data.notes} />

      {/* Project Modal */}
      <ProjectModal
        open={projectModal}
        onClose={() => { setProjectModal(false); setEditingProject(null); setProjectForm(DEFAULT_PROJECT_FORM); }}
        editingProject={editingProject}
        products={products}
        serviceTypes={serviceTypes}
        form={projectForm}
        setForm={setProjectForm}
        onSave={saveProject}
        saving={saving}
      />

      {/* WA Floating Button */}
      <button
        onClick={() => setWaDrawerOpen(true)}
        className="fixed bottom-6 right-6 z-40 bg-green-500 hover:bg-green-600 text-white rounded-full p-4 shadow-lg transition-colors"
        title="Laci Balasan Cepat WA"
      >
        <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
        </svg>
      </button>

      {/* WA Snippet Drawer */}
      <WASnippetDrawer
        open={waDrawerOpen}
        onClose={() => setWaDrawerOpen(false)}
        businessName={profile.business_name}
        purchasedProduct={profile.purchased_product || undefined}
        snippets={WA_SNIPPETS(profile.business_name, profile.purchased_product || undefined)}
      />
    </div>
  );
}
