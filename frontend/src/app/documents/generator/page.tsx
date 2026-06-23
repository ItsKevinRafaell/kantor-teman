"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { apiFetch } from "../../../lib/api";
import { Download, Trash2, FileText, Plus, Search } from "lucide-react";
import Link from "next/link";
import Toast from "../../../components/Toast";
import Modal from "../../../components/Modal";
import Breadcrumb from "../../../components/Breadcrumb";

interface GeneratedDoc {
  id: string;
  template_id: string | null;
  template_name: string | null;
  template_type?: string | null;
  target_type: string | null;
  target_id: string | null;
  target_display_name: string | null;
  file_url: string | null;
  display_filename: string | null;
  status?: string | null;
  payment_status?: string | null;
  generated_at: string;
  generated_by: string | null;
}

const DOC_STATUSES = ["Draft", "Menunggu Review", "Disetujui", "Ditolak", "Dikirim", "Ditandatangani", "Diarsipkan"];
const PAYMENT_STATUSES = ["Belum Dibayar", "Dibayar Sebagian", "Lunas"];
const DOC_TYPE_LABELS: Record<string, string> = {
  report: "Laporan Klien",
  proposal_pdf: "Proposal PDF",
  invoice: "Invoice",
  receipt: "Kwitansi",
  kontrak: "Kontrak",
  kontrak_web_dev: "Kontrak — Website Dev",
  kontrak_seo: "Kontrak — SEO",
  kontrak_sosmed: "Kontrak — Sosmed",
  kontrak_maintenance: "Kontrak — Maintenance",
  kontrak_branding: "Kontrak — Branding",
  kontrak_retainer: "Kontrak — Retainer",
  mou: "MOU",
  surat_penawaran: "Surat Penawaran",
  custom: "Custom",
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function normalizeDocType(doc: GeneratedDoc) {
  if (doc.template_type) return doc.template_type;
  const name = (doc.template_name || doc.display_filename || "").toLowerCase();
  if (name.includes("invoice")) return "invoice";
  if (name.includes("kwitansi") || name.includes("receipt")) return "receipt";
  if (name.includes("kontrak")) {
    if (name.includes("website") || name.includes("web dev")) return "kontrak_web_dev";
    if (name.includes("seo") || name.includes("google business")) return "kontrak_seo";
    if (name.includes("sosmed") || name.includes("social media") || name.includes("socialmedia")) return "kontrak_sosmed";
    if (name.includes("maintenance") || name.includes("support")) return "kontrak_maintenance";
    if (name.includes("branding") || name.includes("brand kit") || name.includes("visual identity")) return "kontrak_branding";
    if (name.includes("retainer")) return "kontrak_retainer";
    return "kontrak";
  }
  if (name.includes("mou")) return "mou";
  if (name.includes("penawaran")) return "surat_penawaran";
  if (name.includes("proposal")) return "proposal_pdf";
  if (name.includes("laporan")) return "report";
  return "custom";
}

function docTypeLabel(doc: GeneratedDoc) {
  return DOC_TYPE_LABELS[normalizeDocType(doc)] || "Custom";
}

export default function DocumentGeneratorPage() {
  const [docs, setDocs] = useState<GeneratedDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const fetchDocs = useCallback(async () => {
    try {
      const res = await apiFetch("/api/generated-documents");
      if (res.ok) setDocs(await res.json());
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);

  async function deleteDoc(id: string) {
    const res = await apiFetch(`/api/documents/generated/${id}`, { method: "DELETE" });
    if (res.ok || res.status === 204) {
      setDocs(prev => prev.filter(d => d.id !== id));
      setToast({ message: "Dokumen dihapus", type: "success" });
    }
    setDeleteId(null);
  }

  async function updateWorkflow(doc: GeneratedDoc, status: string, paymentStatus = doc.payment_status || null) {
    const res = await apiFetch(`/api/documents/generated/${doc.id}/workflow`, {
      method: "PATCH",
      body: JSON.stringify({ status, payment_status: paymentStatus }),
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      setToast({ message: d.detail || "Gagal update status dokumen", type: "error" });
      return;
    }
    setDocs(prev => prev.map(item => item.id === doc.id ? { ...item, status, payment_status: paymentStatus } : item));
    setToast({ message: "Status dokumen diperbarui", type: "success" });
  }

  const filtered = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    const fromMs = dateFrom ? new Date(`${dateFrom}T00:00:00`).getTime() : null;
    const toMs = dateTo ? new Date(`${dateTo}T23:59:59`).getTime() : null;
    return docs
      .filter(d => {
        const docType = normalizeDocType(d);
        if (categoryFilter !== "all" && docType !== categoryFilter) return false;
        if (normalizedSearch) {
          const haystack = [
            d.display_filename || "",
            d.template_name || "",
            docTypeLabel(d),
            d.target_display_name || "",
            d.target_type || "",
            d.generated_by || "",
          ].join(" ").toLowerCase();
          if (!haystack.includes(normalizedSearch)) return false;
        }
        const generatedMs = new Date(d.generated_at).getTime();
        if (!Number.isNaN(generatedMs)) {
          if (fromMs !== null && generatedMs < fromMs) return false;
          if (toMs !== null && generatedMs > toMs) return false;
        }
        return true;
      })
      .sort((a, b) => {
        const aMs = new Date(a.generated_at).getTime() || 0;
        const bMs = new Date(b.generated_at).getTime() || 0;
        return sortDir === "desc" ? bMs - aMs : aMs - bMs;
      });
  }, [categoryFilter, dateFrom, dateTo, docs, search, sortDir]);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <Breadcrumb items={[{ label: "Dokumen & Laporan", href: "/documents" }, { label: "Dokumen Resmi" }]} showBack backHref="/documents" />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Dokumen Resmi</h1>
          <p className="text-sm text-gray-500 mt-1">Generate PDF formal: invoice, kwitansi, kontrak, MoU, surat penawaran, dan proposal PDF.</p>
        </div>
        <div className="flex gap-2">
          <Link href="/documents/generator/templates"
            className="flex items-center gap-1.5 px-4 py-2 bg-gray-100 dark:bg-neutral-800 hover:bg-gray-200 dark:hover:bg-neutral-700 text-gray-700 dark:text-neutral-200 text-xs font-semibold rounded-lg transition-colors">
            <FileText size={14} /> Templates
          </Link>
          <Link href="/documents/generator/new"
            className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-lg transition-colors">
            <Plus size={14} /> Buat Dokumen
          </Link>
        </div>
      </div>

      <div className="rounded-2xl border border-amber-100 bg-white p-4 shadow-sm dark:border-amber-900/40 dark:bg-neutral-900">
        <div className="grid gap-3 md:grid-cols-[minmax(220px,1fr)_180px_150px_150px_150px]">
          <label className="relative">
            <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Cari</span>
            <Search className="pointer-events-none absolute bottom-2.5 left-3 h-4 w-4 text-neutral-400" />
            <input
              type="text"
              placeholder="Nama dokumen, klien, atau template..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full rounded-xl border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-800"
            />
          </label>
          <label>
            <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Kategori</span>
            <select
              value={categoryFilter}
              onChange={e => setCategoryFilter(e.target.value)}
              className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-800"
            >
              <option value="all">Semua kategori</option>
              {Object.entries(DOC_TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>
            <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Dari tanggal</span>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-800"
            />
          </label>
          <label>
            <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Sampai tanggal</span>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-800"
            />
          </label>
          <label>
            <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Urutan</span>
            <select
              value={sortDir}
              onChange={e => setSortDir(e.target.value as "desc" | "asc")}
              className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-300 dark:border-neutral-700 dark:bg-neutral-800"
            >
              <option value="desc">Terbaru dulu</option>
              <option value="asc">Terlama dulu</option>
            </select>
          </label>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">Memuat...</p>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <FileText size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">Belum ada dokumen. Klik "Generate Baru" untuk mulai.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(doc => (
            <div key={doc.id} className="flex items-center justify-between p-4 bg-white dark:bg-neutral-900 border border-[var(--border-default)] rounded-xl">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100 truncate">{doc.display_filename || doc.template_name || "Untitled"}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  <span className="mr-2 rounded-full bg-amber-50 px-2 py-0.5 font-medium text-amber-700 dark:bg-amber-950/20 dark:text-amber-300">{docTypeLabel(doc)}</span>
                  {doc.target_type && <span className="mr-2 text-neutral-400">{doc.target_type}</span>}
                  {doc.target_display_name && <span className="font-medium text-neutral-600 dark:text-neutral-300 mr-2">{doc.target_display_name}</span>}
                  {doc.generated_at && new Date(doc.generated_at).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                  {doc.generated_by && <span className="ml-2 text-gray-400">oleh {doc.generated_by}</span>}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <select value={doc.status || "Draft"} onChange={e => updateWorkflow(doc, e.target.value)}
                    className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs text-neutral-700 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100">
                    {DOC_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                  {(doc.template_name || "").toLowerCase().includes("invoice") && (
                    <select value={doc.payment_status || "Belum Dibayar"} onChange={e => updateWorkflow(doc, doc.status || "Draft", e.target.value)}
                      className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs text-neutral-700 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100">
                      {PAYMENT_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 ml-3">
                {doc.file_url && (
                  <a href={`${API_BASE}/api/documents/${doc.id}/download`} target="_blank" rel="noopener noreferrer"
                    className="p-2 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-lg transition-colors" title="Download">
                    <Download size={14} className="text-gray-500" />
                  </a>
                )}
                <button onClick={() => setDeleteId(doc.id)}
                  className="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors" title="Hapus">
                  <Trash2 size={14} className="text-red-400" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      <Modal
        open={!!deleteId}
        title="Hapus Dokumen?"
        message="Dokumen hasil generator akan dihapus permanen."
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => deleteId && deleteDoc(deleteId)}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  );
}
