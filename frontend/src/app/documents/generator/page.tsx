"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import { Download, Trash2, Mail, FileText, Plus } from "lucide-react";
import Link from "next/link";
import Toast from "../../../components/Toast";
import Modal from "../../../components/Modal";

interface GeneratedDoc {
  id: string;
  template_id: string | null;
  template_name: string | null;
  target_type: string | null;
  target_id: string | null;
  file_url: string | null;
  display_filename: string | null;
  generated_at: string;
  generated_by: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function DocumentGeneratorPage() {
  const [docs, setDocs] = useState<GeneratedDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
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

  const filtered = docs.filter(d =>
    !search || (d.template_name || "").toLowerCase().includes(search.toLowerCase()) ||
    (d.target_type || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Document Generator</h1>
          <p className="text-sm text-gray-500 mt-1">Generate PDF: Invoice, Proposal, Kontrak, Surat Resmi.</p>
        </div>
        <div className="flex gap-2">
          <Link href="/documents/generator/templates"
            className="flex items-center gap-1.5 px-4 py-2 bg-gray-100 dark:bg-neutral-800 hover:bg-gray-200 dark:hover:bg-neutral-700 text-gray-700 dark:text-neutral-200 text-xs font-semibold rounded-lg transition-colors">
            <FileText size={14} /> Templates
          </Link>
          <Link href="/documents/generator/new"
            className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-lg transition-colors">
            <Plus size={14} /> Generate Baru
          </Link>
        </div>
      </div>

      <input
        type="text"
        placeholder="Cari dokumen..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        className="w-full max-w-sm px-4 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-900 focus:outline-none focus:ring-2 focus:ring-amber-300"
      />

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
                  {doc.target_type && <span className="mr-2">{doc.target_type}: {doc.target_id?.slice(0, 8)}...</span>}
                  {doc.generated_at && new Date(doc.generated_at).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                  {doc.generated_by && <span className="ml-2 text-gray-400">oleh {doc.generated_by}</span>}
                </p>
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
    </div>
  );
}
