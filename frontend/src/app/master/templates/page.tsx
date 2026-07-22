"use client";
import NativeSelect from "../../../components/ui/NativeSelect";
import { inputCls } from "../../../lib/inputCls";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "../../../lib/api";
import { Plus, Edit2, Trash2, X, FileText, Search } from "lucide-react";
import Breadcrumb from "../../../components/Breadcrumb";
import Pagination from "../../../components/Pagination";
import Modal from "../../../components/Modal";
import Toast from "../../../components/Toast";

interface DynTemplate {
  id: string;
  name: string;
  type: string;
  content: string;
  is_active: boolean;
  category_id: string | null;
  category_name: string | null;
}

interface TemplateStats {
  sent: number;
  delivered: number;
  read: number;
  replied: number;
  closed: number;
  reply_rate: number;
  conversion_rate: number;
}

interface CategoryOption {
  id: string;
  name: string;
}

const TEMPLATE_TYPES = [
  { value: "WA_BLAST", label: "WA Blast", hint: "Dipakai saat blast WA ke leads" },
  { value: "PROPOSAL_TEXT", label: "Proposal Text", hint: "Isi teks proposal yang dikirim" },
  { value: "PROPOSAL_INTRO", label: "Leader / Intro", hint: "Pembuka di halaman proposal" },
  { value: "PROPOSAL_OUTRO", label: "Outro", hint: "Penutup di halaman proposal" },
  { value: "FOLLOW_UP", label: "Follow Up", hint: "Pesan follow-up otomatis" },
  { value: "GENERAL", label: "General", hint: "Template umum" },
];

const TYPE_COLORS: Record<string, string> = {
  WA_BLAST: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  PROPOSAL_TEXT: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
  PROPOSAL_INTRO: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  PROPOSAL_OUTRO: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  FOLLOW_UP: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  GENERAL: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
};

export default function DynamicTemplatesPage() {
  const [templates, setTemplates] = useState<DynTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<DynTemplate | null>(null);
  const [form, setForm] = useState({ name: "", type: "WA_BLAST", content: "", is_active: true, category_id: "" });
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [stats, setStats] = useState<Record<string, TemplateStats>>({});
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const [page, setPage] = useState(1);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const PAGE_SIZE = 15;

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await apiFetch("/api/dynamic-templates");
      if (res.ok) setTemplates(await res.json());
    } finally { setLoading(false); }
  }, []);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await apiFetch("/api/categories");
      if (res.ok) setCategories(await res.json());
    } catch { /* silent */ }
  }, []);

  const fetchStats = useCallback(async (waBlastIds: string[]) => {
    const results: Record<string, TemplateStats> = {};
    await Promise.all(waBlastIds.map(async (id) => {
      try {
        const res = await apiFetch(`/api/templates/${id}/stats?days=30`);
        if (res.ok) results[id] = await res.json();
      } catch { /* silent */ }
    }));
    setStats(results);
  }, []);

  useEffect(() => {
    const waIds = templates.filter(t => t.type === "WA_BLAST").map(t => t.id);
    if (waIds.length > 0) fetchStats(waIds);
  }, [templates, fetchStats]);

  useEffect(() => {
    fetchTemplates();
    fetchCategories();
    intervalRef.current = setInterval(fetchTemplates, 30000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchTemplates, fetchCategories]);

  useEffect(() => {
    setPage(1);
  }, [typeFilter, statusFilter, categoryFilter, searchQuery]);

  function openNew() {
    setEditing(null);
    setForm({ name: "", type: "WA_BLAST", content: "", is_active: true, category_id: "" });
    setModal(true);
  }

  function openEdit(t: DynTemplate) {
    setEditing(t);
    setForm({ name: t.name, type: t.type, content: t.content, is_active: t.is_active, category_id: t.category_id || "" });
    setModal(true);
  }

  async function save() {
    if (!form.name.trim()) { setToast({ message: "Nama template wajib diisi.", type: "error" }); return; }
    if (!form.content.trim()) { setToast({ message: "Konten template wajib diisi.", type: "error" }); return; }
    const payload = { ...form, category_id: form.category_id || null };
    const method = editing ? "PUT" : "POST";
    const url = editing ? `/api/dynamic-templates/${editing.id}` : "/api/dynamic-templates";
    const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
    if (res.ok) { setToast({ message: "Template berhasil disimpan.", type: "success" }); setModal(false); fetchTemplates(); }
  }

  async function deleteTemplate(id: string) {
    const res = await apiFetch(`/api/dynamic-templates/${id}`, { method: "DELETE" });
    if (res.ok) { setToast({ message: "Berhasil dihapus.", type: "success" }); fetchTemplates(); }
    else { setToast({ message: "Gagal hapus.", type: "error" }); }
    setDeleteId(null);
  }

  if (loading) {
    return (
      <div className="max-w-6xl space-y-6">
        <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
        <Modal
          open={!!deleteId}
          title="Hapus Template?"
          message="Item yang dihapus tidak bisa dikembalikan."
          confirmLabel="Hapus"
          confirmClass="bg-red-600 hover:bg-red-700"
          onConfirm={() => deleteId !== null && deleteTemplate(deleteId!)}
          onCancel={() => setDeleteId(null)}
        />
        <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded w-48 animate-pulse" />
        <div className="space-y-3">{[1, 2, 3].map(i => <div key={i} className="h-20 bg-gray-100 dark:bg-gray-800 rounded-2xl animate-pulse" />)}</div>
      </div>
    );
  }

  const normalizedSearch = searchQuery.trim().toLowerCase();
  const filtered = templates.filter(t => {
    if (typeFilter !== "all" && t.type !== typeFilter) return false;
    if (statusFilter === "active" && !t.is_active) return false;
    if (statusFilter === "inactive" && t.is_active) return false;
    if (categoryFilter !== "all" && (t.category_id || "") !== categoryFilter) return false;
    if (!normalizedSearch) return true;
    return [t.name, t.content, t.category_name || "", TEMPLATE_TYPES.find(tt => tt.value === t.type)?.label || t.type]
      .some(v => v.toLowerCase().includes(normalizedSearch));
  });
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="max-w-6xl space-y-6">
      <Breadcrumb items={[{ label: "Master" }, { label: "Template" }]} showBack backHref="/master" />
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />
      <Modal
        open={!!deleteId}
        title="Hapus Template?"
        message="Item yang dihapus tidak bisa dikembalikan."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteId !== null && deleteTemplate(deleteId!)}
        onCancel={() => setDeleteId(null)}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Template Teks</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Master template dinamis untuk WA Blast, Proposal, dan lainnya.</p>
        </div>
        <button onClick={openNew} className="flex items-center gap-1.5 px-4 py-2.5 bg-brand-yellow hover:bg-amber-600 text-white text-sm font-semibold rounded-xl transition-colors">
          <Plus size={16} /> Tambah Template
        </button>
      </div>

      <div className="grid grid-cols-1 gap-3 rounded-2xl border border-amber-100 bg-white p-3 shadow-sm sm:grid-cols-2 lg:grid-cols-4 dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
        <label className="relative sm:col-span-2">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="Cari nama, isi template, atau kategori..."
            className="w-full rounded-xl border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-gray-700 dark:bg-neutral-800/70 dark:text-neutral-100" />
        </label>
        <NativeSelect value={typeFilter} onChange={setTypeFilter} placeholder="Semua tipe" options={[{value:"",label:"Semua tipe"},{value:"WA_BLAST",label:"WA Blast"},{value:"FOLLOW_UP",label:"Follow Up"},{value:"EMAIL",label:"Email"}]} />
        <NativeSelect value={statusFilter} onChange={v => setStatusFilter((v || "all") as any)} clearable={false} options={[{value:"all",label:"Semua"},{value:"active",label:"Aktif"},{value:"inactive",label:"Nonaktif"}]} />
        <NativeSelect value={categoryFilter} onChange={setCategoryFilter} placeholder="Semua kategori" options={categories.map((c: any) => ({ value: String(c.id), label: c.name }))} />
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-12 bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] text-gray-400 text-sm">
          {typeFilter === "all" ? "Belum ada template. Tambahkan template pertamamu." : "Tidak ada template untuk filter ini."}
        </div>
      ) : (
        <div className="space-y-3">
          {paged.map(t => (
            <div key={t.id} className="bg-[var(--bg-surface)] rounded-2xl border border-[var(--border-default)] shadow-sm p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-brand-yellow/10 flex items-center justify-center shrink-0 mt-0.5"><FileText size={15} className="text-brand-yellow" /></div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{t.name}</p>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${TYPE_COLORS[t.type] || TYPE_COLORS.GENERAL}`}>{TEMPLATE_TYPES.find(tt => tt.value === t.type)?.label || t.type}</span>
                      {!t.is_active && <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-200 dark:bg-gray-700 text-gray-500">Nonaktif</span>}
                    </div>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2 font-mono whitespace-pre-wrap">{t.content}</p>
                    {t.type === "WA_BLAST" && stats[t.id] && (
                      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 text-[10px] font-semibold">
                        <span className="text-gray-500">Sent: {stats[t.id].sent}</span>
                        <span className="text-blue-600">Delivered: {stats[t.id].delivered}</span>
                        <span className="text-purple-600">Read: {stats[t.id].read}</span>
                        <span className="text-amber-600">Replied: {stats[t.id].replied} ({stats[t.id].reply_rate}%)</span>
                        <span className="text-green-600">Closed: {stats[t.id].closed} ({stats[t.id].conversion_rate}%)</span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0 ml-3">
                  <button onClick={() => openEdit(t)} className="p-1.5 text-gray-400 hover:text-brand-yellow rounded-lg transition-colors"><Edit2 size={14} /></button>
                  <button onClick={() => setDeleteId(t.id)} className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg transition-colors"><Trash2 size={14} /></button>
                </div>
              </div>
            </div>
          ))}
          <Pagination page={page} pageSize={PAGE_SIZE} total={filtered.length} onPageChange={setPage} itemLabel="template" />
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setModal(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-lg p-6 space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">{editing ? "Edit Template" : "Tambah Template"}</h3>
              <button onClick={() => setModal(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nama Template</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className={inputCls} placeholder="Contoh: Blast SEO Promo" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Tipe</label>
                <NativeSelect value={form.type} onChange={v => setForm(f => ({ ...f, type: v }))} clearable={false} options={[{value:"WA_BLAST",label:"WA Blast"},{value:"FOLLOW_UP",label:"Follow Up"},{value:"EMAIL",label:"Email"}]} />
                <p className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1">{TEMPLATE_TYPES.find(t => t.value === form.type)?.hint}</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Kategori Produk</label>
                <NativeSelect value={form.category_id} onChange={v => setForm(f => ({ ...f, category_id: v }))} placeholder="Kategori" options={categories.map((c: any) => ({ value: String(c.id), label: c.name }))} />
                <p className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1">Untuk WA Blast: template akan difilter berdasarkan kategori saat eksekusi.</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Isi Konten</label>
                <textarea value={form.content} onChange={e => setForm(f => ({ ...f, content: e.target.value }))} rows={6}
                  className={inputCls + " resize-none font-mono"} placeholder="Halo {{client_name}}, kami ingin menawarkan {{product_name}}..." />
                <div className="mt-1.5 p-2.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-lg space-y-1.5">
                  <p className="text-[11px] text-blue-600 dark:text-blue-400 font-medium">Variabel yang tersedia (klik untuk copy):</p>
                  <div className="flex flex-wrap gap-1.5">
                    {[
                      { v: "{{business_name}}", d: "Nama bisnis lead" },
                      { v: "{{client_name}}", d: "Sama dengan business_name" },
                      { v: "{{product_name}}", d: "Kategori layanan target" },
                      { v: "{{proposal_link}}", d: "Link report/proposal" },
                    ].map(x => (
                      <button key={x.v} type="button"
                        onClick={() => { navigator.clipboard.writeText(x.v); setForm(f => ({ ...f, content: f.content + x.v })); }}
                        className="px-2 py-0.5 bg-blue-100 dark:bg-blue-800/40 text-blue-700 dark:text-blue-300 rounded text-[10px] font-mono hover:bg-blue-200 dark:hover:bg-blue-700/40 transition-colors"
                        title={x.d}>{x.v}</button>
                    ))}
                  </div>
                  <p className="text-[10px] text-blue-500 dark:text-blue-400 mt-1">
                    <strong>WA Blast:</strong> semua variabel · <strong>Proposal:</strong> business_name · <strong>Follow Up:</strong> business_name, proposal_link
                  </p>
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
                  className="w-4 h-4 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
                <span className="text-sm text-gray-700 dark:text-gray-300 font-medium">Aktif</span>
              </label>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setModal(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={save} className="px-4 py-2 text-sm font-semibold bg-brand-yellow hover:bg-amber-600 text-white rounded-xl transition-colors">Simpan</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
