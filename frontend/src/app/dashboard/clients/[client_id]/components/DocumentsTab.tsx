"use client";
import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../../../lib/api";
import { FileText, Plus, Trash2 } from "lucide-react";
import Toast from "../../../../../components/Toast";
import Modal from "../../../../../components/Modal";

interface DocumentData {
  id: string;
  lead_id: number | null;
  title: string;
  cloud_url: string;
  created_at: string;
}

export default function DocumentsTab({ leadId }: { leadId: number | null }) {
  const [documents, setDocuments] = useState<DocumentData[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ title: "", cloud_url: "" });
  const [saving, setSaving] = useState(false);
  const [deleteDocId, setDeleteDocId] = useState<string | null>(null);
  const [docToast, setDocToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  const fetchDocuments = useCallback(async () => {
    if (!leadId) {
      setDocuments([]);
      setLoading(false);
      return;
    }
    try {
      const res = await apiFetch(`/api/documents?lead_id=${leadId}`);
      if (res.ok) setDocuments(await res.json());
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
        <button onClick={() => setShowModal(true)} disabled={!leadId} className="btn-primary flex items-center gap-1.5 text-xs disabled:opacity-50">
          <Plus size={14} /> Tambah
        </button>
      </div>

      {!leadId ? (
        <div className="text-center py-12 text-amber-600 dark:text-amber-400 text-sm">Kontak ini belum memiliki relasi lead.</div>
      ) : documents.length === 0 ? (
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
