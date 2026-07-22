"use client";
import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../../../lib/api";
import { Download, FileText, Plus, Trash2 } from "lucide-react";
import Toast from "../../../../../components/Toast";
import Modal from "../../../../../components/Modal";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const DOC_TYPE_LABELS: Record<string, string> = {
  proposal_pdf: "Proposal PDF",
  invoice: "Invoice",
  receipt: "Kwitansi",
  kontrak: "Kontrak",
  mou: "MOU",
  surat_penawaran: "Surat Penawaran",
  custom: "Custom",
};

interface DocumentData {
  id: string;
  lead_id: number | null;
  title: string;
  cloud_url: string;
  created_at: string;
}

interface GeneratedDocumentData {
  id: string;
  template_name: string | null;
  template_type?: string | null;
  target_display_name?: string | null;
  display_filename?: string | null;
  status?: string | null;
  payment_status?: string | null;
  generated_at: string;
}

interface ArchiveDocumentData {
  id: string;
  title: string;
  body: string | null;
  url: string | null;
  folder_id: string | null;
  tags: string[];
  created_at: string;
  updated_at: string | null;
}

interface ArchiveFolderData {
  id: string;
  name: string;
  parent_id: string | null;
  color: string;
  lead_id?: number | null;
  lead_name?: string | null;
  created_at: string;
}

function generatedDocTypeLabel(doc: GeneratedDocumentData) {
  if (doc.template_type && DOC_TYPE_LABELS[doc.template_type]) return DOC_TYPE_LABELS[doc.template_type];
  const name = (doc.template_name || doc.display_filename || "").toLowerCase();
  if (name.includes("invoice")) return "Invoice";
  if (name.includes("kwitansi") || name.includes("receipt")) return "Kwitansi";
  if (name.includes("kontrak")) return "Kontrak";
  if (name.includes("mou")) return "MOU";
  if (name.includes("penawaran")) return "Surat Penawaran";
  if (name.includes("proposal")) return "Proposal PDF";
  return "Dokumen";
}

export default function DocumentsTab({ leadId }: { leadId: number | null }) {
  const [documents, setDocuments] = useState<DocumentData[]>([]);
  const [generatedDocuments, setGeneratedDocuments] = useState<GeneratedDocumentData[]>([]);
  const [archiveDocuments, setArchiveDocuments] = useState<ArchiveDocumentData[]>([]);
  const [archiveFolders, setArchiveFolders] = useState<ArchiveFolderData[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ title: "", cloud_url: "" });
  const [saving, setSaving] = useState(false);
  const [deleteDocId, setDeleteDocId] = useState<string | null>(null);
  const [docToast, setDocToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  const fetchDocuments = useCallback(async () => {
    if (!leadId) {
      setDocuments([]);
      setGeneratedDocuments([]);
      setArchiveDocuments([]);
      setArchiveFolders([]);
      setLoading(false);
      return;
    }
    try {
      const [manualRes, generatedRes, archiveRes, folderRes] = await Promise.all([
        apiFetch(`/api/documents?lead_id=${leadId}`),
        apiFetch(`/api/generated-documents?lead_id=${leadId}`),
        apiFetch(`/api/archive?lead_id=${leadId}&limit=100`),
        apiFetch(`/api/archive/folders?lead_id=${leadId}`),
      ]);
      if (manualRes.ok) setDocuments(await manualRes.json());
      if (generatedRes.ok) setGeneratedDocuments(await generatedRes.json());
      if (archiveRes.ok) setArchiveDocuments(await archiveRes.json());
      else setArchiveDocuments([]);
      if (folderRes.ok) setArchiveFolders(await folderRes.json());
      else setArchiveFolders([]);
    } finally {
      setLoading(false);
    }
  }, [leadId]);

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

  async function saveDocument() {
    if (!leadId || !form.title || !form.cloud_url) return;
    setSaving(true);
    try {
      const res = await apiFetch("/api/documents", {
        method: "POST",
        body: JSON.stringify({ ...form, lead_id: leadId }),
      });
      if (res.ok) {
        setShowModal(false);
        setForm({ title: "", cloud_url: "" });
        fetchDocuments();
      }
    } finally {
      setSaving(false);
    }
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

  const hasAnyDocument = documents.length > 0 || generatedDocuments.length > 0 || archiveDocuments.length > 0 || archiveFolders.length > 0;

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
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
            Hub: link cloud, PDF generator, dan arsip tim yang ditautkan ke klien. Password/API key → tab Kredensial.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={leadId ? `/documents?search=` : "/documents"}
            className="rounded-xl border border-neutral-200 px-2.5 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
          >
            Buka Arsip Tim
          </a>
          <button onClick={() => setShowModal(true)} disabled={!leadId} className="btn-primary flex items-center gap-1.5 text-xs disabled:opacity-50">
            <Plus size={14} /> Tambah link
          </button>
        </div>
      </div>

      {!leadId ? (
        <div className="text-center py-12 text-amber-600 dark:text-amber-400 text-sm">Kontak ini belum memiliki relasi lead.</div>
      ) : !hasAnyDocument ? (
        <div className="space-y-2 px-5 py-10 text-center text-sm text-neutral-400">
          <p>Belum ada dokumen tersimpan untuk klien ini.</p>
          <p className="text-xs">Tambah link cloud di sini, generate PDF di Dokumen Resmi, atau tautkan arsip di /documents (field Terkait klien).</p>
        </div>
      ) : (
        <div className="divide-y divide-[var(--border-subtle)]">
          {generatedDocuments.length > 0 && (
            <div className="px-5 py-3 text-[11px] font-bold uppercase tracking-wide text-neutral-400">
              Dokumen dari Generator
            </div>
          )}
          {generatedDocuments.map(doc => (
            <div key={doc.id} className="px-5 py-4 flex items-center justify-between hover:bg-[var(--bg-surface-hover)] transition-colors group">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-amber-50 dark:bg-amber-950/20 flex items-center justify-center shrink-0">
                  <FileText size={16} className="text-amber-600 dark:text-amber-300" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{doc.display_filename || doc.template_name || "Dokumen resmi"}</p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate">
                    <span className="font-medium text-amber-700 dark:text-amber-300">{generatedDocTypeLabel(doc)}</span>
                    {doc.status && <span className="ml-2">{doc.status}</span>}
                    {doc.payment_status && <span className="ml-2">Pembayaran: {doc.payment_status}</span>}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[10px] text-neutral-400">
                  {new Date(doc.generated_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}
                </span>
                <a href={`${API_BASE}/api/documents/${doc.id}/download`} target="_blank" rel="noopener noreferrer"
                  className="p-1.5 text-neutral-400 hover:text-amber-600 rounded-lg transition-colors">
                  <Download size={13} />
                </a>
              </div>
            </div>
          ))}
          {documents.length > 0 && (
            <div className="px-5 py-3 text-[11px] font-bold uppercase tracking-wide text-neutral-400">
              Link Cloud Manual
            </div>
          )}
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
          {archiveFolders.length > 0 && (
            <div className="px-5 py-3 text-[11px] font-bold uppercase tracking-wide text-neutral-400">
              Folder Arsip (ditautkan)
            </div>
          )}
          {archiveFolders.map(folder => (
            <a
              key={folder.id}
              href={`/documents?folder=${folder.id}`}
              className="px-5 py-4 flex items-center justify-between hover:bg-[var(--bg-surface-hover)] transition-colors group"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: `${folder.color || "#6B7280"}22` }}>
                  <FileText size={16} style={{ color: folder.color || "#6B7280" }} />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{folder.name}</p>
                  <p className="text-xs text-neutral-500">Buka folder di Arsip Tim</p>
                </div>
              </div>
            </a>
          ))}
          {archiveDocuments.length > 0 && (
            <div className="px-5 py-3 text-[11px] font-bold uppercase tracking-wide text-neutral-400">
              Arsip Tim (ditautkan)
            </div>
          )}
          {archiveDocuments.map(doc => {
            const href = doc.url
              ? (doc.url.startsWith("/") ? `${API_BASE}${doc.url}` : doc.url)
              : `/documents`;
            return (
              <div key={doc.id} className="px-5 py-4 flex items-center justify-between hover:bg-[var(--bg-surface-hover)] transition-colors group">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-emerald-50 dark:bg-emerald-950/20 flex items-center justify-center shrink-0">
                    <FileText size={16} className="text-emerald-600 dark:text-emerald-300" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{doc.title}</p>
                    <p className="text-xs text-neutral-500 truncate">
                      {doc.body ? doc.body.slice(0, 80) : "Catatan arsip"}
                      {doc.tags?.length ? ` · ${doc.tags.slice(0, 3).join(", ")}` : ""}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] text-neutral-400">
                    {new Date(doc.updated_at || doc.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" })}
                  </span>
                  <a href={href} target="_blank" rel="noopener noreferrer"
                    className="p-1.5 text-neutral-400 hover:text-emerald-600 rounded-lg transition-colors">
                    <Download size={13} />
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}

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
                <input
                  value={form.title}
                  onChange={e => setForm(prev => ({ ...prev, title: e.target.value }))}
                  className="input-field"
                  placeholder="Desain Logo Final"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">Cloud URL</label>
                <input
                  value={form.cloud_url}
                  onChange={e => setForm(prev => ({ ...prev, cloud_url: e.target.value }))}
                  className="input-field"
                  placeholder="https://drive.google.com/..."
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowModal(false)} className="btn-ghost">Batal</button>
              <button onClick={saveDocument} disabled={saving} className="btn-primary">{saving ? "Menyimpan..." : "Simpan"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
