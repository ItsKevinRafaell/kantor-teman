"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../lib/api";
import Toast from "../../components/Toast";
import { Plus, Trash2, ExternalLink, Folder, FileText, Search, Edit2, X } from "lucide-react";

interface DocumentFolder {
  id: string;
  name: string;
  parent_id: string | null;
  color: string;
  created_at: string;
}

interface Document {
  id: string;
  folder_id: string | null;
  title: string;
  body: string | null;
  url: string | null;
  tags: string[];
  created_at: string;
  updated_at: string | null;
}

const FOLDER_COLORS = [
  { hex: "#6B7280", label: "Gray" },
  { hex: "#3B82F6", label: "Blue" },
  { hex: "#22C55E", label: "Green" },
  { hex: "#EAB308", label: "Yellow" },
  { hex: "#EF4444", label: "Red" },
  { hex: "#A855F7", label: "Purple" },
];

function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
      <div
        className="relative bg-white dark:bg-[#242423] rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-white dark:bg-[#242423] px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between rounded-t-2xl">
          <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-50">{title}</h2>
          <button onClick={onClose} className="p-1 text-neutral-400 hover:text-neutral-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

export default function DocumentsPage() {
  const [folders, setFolders] = useState<DocumentFolder[]>([]);
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(undefined as unknown as null);
  const [showUnfoldered, setShowUnfoldered] = useState(false);
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [saving, setSaving] = useState(false);

  const [docModal, setDocModal] = useState(false);
  const [editingDoc, setEditingDoc] = useState<Document | null>(null);
  const [docForm, setDocForm] = useState({ title: "", body: "", url: "", tags: "", folder_id: "" });

  const [folderModal, setFolderModal] = useState(false);
  const [editingFolder, setEditingFolder] = useState<DocumentFolder | null>(null);
  const [folderForm, setFolderForm] = useState({ name: "", color: "#6B7280" });

  const fetchFolders = useCallback(async () => {
    const res = await apiFetch("/api/archive/folders");
    if (res.ok) setFolders(await res.json());
  }, []);

  const fetchDocs = useCallback(async () => {
    const params = new URLSearchParams();
    if (showUnfoldered) {
      params.set("unfoldered", "true");
    } else if (selectedFolder !== null && selectedFolder !== undefined) {
      params.set("folder_id", selectedFolder);
    }
    if (search) params.set("search", search);
    const res = await apiFetch(`/api/archive?${params.toString()}`);
    if (res.ok) setDocs(await res.json());
  }, [selectedFolder, showUnfoldered, search]);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchFolders(), fetchDocs()]).finally(() => setLoading(false));
  }, [fetchFolders, fetchDocs]);

  function openNewDoc() {
    setEditingDoc(null);
    setDocForm({
      title: "",
      body: "",
      url: "",
      tags: "",
      folder_id: selectedFolder && !showUnfoldered ? selectedFolder : "",
    });
    setDocModal(true);
  }

  function openEditDoc(doc: Document) {
    setEditingDoc(doc);
    setDocForm({
      title: doc.title,
      body: doc.body || "",
      url: doc.url || "",
      tags: doc.tags.join(", "),
      folder_id: doc.folder_id || "",
    });
    setDocModal(true);
  }

  async function saveDoc() {
    if (!docForm.title.trim()) return;
    setSaving(true);
    const tags = docForm.tags
      .split(",")
      .map(t => t.trim())
      .filter(Boolean);
    const payload = {
      title: docForm.title.trim(),
      body: docForm.body || null,
      url: docForm.url || null,
      tags,
      folder_id: docForm.folder_id || null,
    };
    try {
      const method = editingDoc ? "PUT" : "POST";
      const url = editingDoc ? `/api/archive/${editingDoc.id}` : "/api/archive";
      const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
      if (res.ok) {
        setDocModal(false);
        setToast({ message: editingDoc ? "Dokumen diperbarui" : "Dokumen disimpan", type: "success" });
        fetchDocs();
      } else {
        setToast({ message: "Gagal menyimpan dokumen", type: "error" });
      }
    } finally {
      setSaving(false);
    }
  }

  async function deleteDoc(id: string) {
    const res = await apiFetch(`/api/archive/${id}`, { method: "DELETE" });
    if (res.ok) {
      setDocs(prev => prev.filter(d => d.id !== id));
      setToast({ message: "Dokumen dihapus", type: "success" });
    } else {
      setToast({ message: "Gagal menghapus", type: "error" });
    }
  }

  function openNewFolder() {
    setEditingFolder(null);
    setFolderForm({ name: "", color: "#6B7280" });
    setFolderModal(true);
  }

  function openEditFolder(folder: DocumentFolder, e: React.MouseEvent) {
    e.stopPropagation();
    setEditingFolder(folder);
    setFolderForm({ name: folder.name, color: folder.color });
    setFolderModal(true);
  }

  async function saveFolder() {
    if (!folderForm.name.trim()) return;
    setSaving(true);
    try {
      const method = editingFolder ? "PUT" : "POST";
      const url = editingFolder ? `/api/archive/folders/${editingFolder.id}` : "/api/archive/folders";
      const res = await apiFetch(url, {
        method,
        body: JSON.stringify({ name: folderForm.name.trim(), color: folderForm.color }),
      });
      if (res.ok) {
        setFolderModal(false);
        setToast({ message: editingFolder ? "Folder diperbarui" : "Folder dibuat", type: "success" });
        fetchFolders();
      } else {
        setToast({ message: "Gagal menyimpan folder", type: "error" });
      }
    } finally {
      setSaving(false);
    }
  }

  async function deleteFolder(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    const res = await apiFetch(`/api/archive/folders/${id}`, { method: "DELETE" });
    if (res.ok) {
      setFolders(prev => prev.filter(f => f.id !== id));
      if (selectedFolder === id) setSelectedFolder(null);
      setToast({ message: "Folder dihapus", type: "success" });
      fetchDocs();
    } else {
      setToast({ message: "Gagal menghapus folder", type: "error" });
    }
  }

  function selectAll() {
    setSelectedFolder(null);
    setShowUnfoldered(false);
  }

  function selectUnfoldered() {
    setSelectedFolder(null);
    setShowUnfoldered(true);
  }

  function selectFolder(id: string) {
    setSelectedFolder(id);
    setShowUnfoldered(false);
  }

  const activeLabel =
    showUnfoldered
      ? "Tanpa Folder"
      : selectedFolder
      ? folders.find(f => f.id === selectedFolder)?.name || "Folder"
      : "Semua Dokumen";

  if (loading) {
    return (
      <div className="flex flex-col md:flex-row gap-4 md:gap-6 h-full animate-pulse">
        <div className="w-full md:w-48 shrink-0 space-y-2">
          {[1, 2, 3].map(i => <div key={i} className="h-9 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />)}
        </div>
        <div className="flex-1 space-y-4">
          <div className="h-10 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-36 bg-neutral-100 dark:bg-neutral-800 rounded-2xl" />)}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col md:flex-row gap-4 md:gap-6 h-full">
      {/* Sidebar */}
      <aside className="w-full md:w-48 shrink-0 flex flex-col gap-1">
        <button
          onClick={selectAll}
          className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors text-left w-full ${
            !showUnfoldered && selectedFolder === null
              ? "bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300"
              : "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"
          }`}
        >
          <FileText size={15} /> Semua Dokumen
        </button>
        <button
          onClick={selectUnfoldered}
          className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors text-left w-full ${
            showUnfoldered
              ? "bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300"
              : "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"
          }`}
        >
          <FileText size={15} /> Tanpa Folder
        </button>

        <div className="my-1 border-t border-neutral-100 dark:border-neutral-800" />

        {folders.map(folder => (
          <div
            key={folder.id}
            onClick={() => selectFolder(folder.id)}
            className={`group flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium cursor-pointer transition-colors ${
              selectedFolder === folder.id
                ? "bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300"
                : "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"
            }`}
          >
            <span className="w-2.5 h-2.5 rounded-full shrink-0 mt-px" style={{ backgroundColor: folder.color }} />
            <span className="flex-1 truncate">{folder.name}</span>
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
              <button onClick={e => openEditFolder(folder, e)} className="p-0.5 hover:text-yellow-500 transition-colors">
                <Edit2 size={11} />
              </button>
              <button onClick={e => deleteFolder(folder.id, e)} className="p-0.5 hover:text-red-500 transition-colors">
                <Trash2 size={11} />
              </button>
            </div>
          </div>
        ))}

        <button
          onClick={openNewFolder}
          className="mt-2 flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-yellow-600 dark:text-yellow-400 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 transition-colors"
        >
          <Plus size={13} /> Folder Baru
        </button>
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center shrink-0">
              <Folder size={18} className="text-yellow-500" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-50 leading-tight">Dokumen</h1>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">{activeLabel}</p>
            </div>
          </div>
          <button
            onClick={openNewDoc}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold bg-yellow-500 hover:bg-yellow-600 text-white transition-colors shrink-0"
          >
            <Plus size={15} /> Tambah Dokumen
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Cari dokumen..."
            className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-white dark:bg-[#242423] border border-gray-200 dark:border-gray-700 text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
          />
        </div>

        {/* Documents grid */}
        {docs.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center py-20 text-center">
            <FileText size={40} className="text-neutral-300 dark:text-neutral-600 mb-3" />
            <p className="text-neutral-500 dark:text-neutral-400 text-sm">
              {search ? "Tidak ada dokumen yang cocok." : "Belum ada dokumen di sini."}
            </p>
            {!search && (
              <button onClick={openNewDoc} className="mt-4 flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold bg-yellow-500 hover:bg-yellow-600 text-white transition-colors">
                <Plus size={14} /> Tambah Pertama
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {docs.map(doc => (
              <DocCard
                key={doc.id}
                doc={doc}
                folderColor={folders.find(f => f.id === doc.folder_id)?.color}
                folderName={folders.find(f => f.id === doc.folder_id)?.name}
                onEdit={() => openEditDoc(doc)}
                onDelete={() => deleteDoc(doc.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Document Modal */}
      <Modal open={docModal} onClose={() => setDocModal(false)} title={editingDoc ? "Edit Dokumen" : "Dokumen Baru"}>
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Judul *</label>
            <input
              autoFocus
              value={docForm.title}
              onChange={e => setDocForm(p => ({ ...p, title: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
              placeholder="Judul dokumen..."
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Link Eksternal</label>
            <input
              value={docForm.url}
              onChange={e => setDocForm(p => ({ ...p, url: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
              placeholder="https://..."
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Catatan / Body</label>
            <textarea
              value={docForm.body}
              onChange={e => setDocForm(p => ({ ...p, body: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none resize-none"
              rows={4}
              placeholder="Tulis catatan di sini..."
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Tags</label>
            <input
              value={docForm.tags}
              onChange={e => setDocForm(p => ({ ...p, tags: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
              placeholder="seo, panduan, internal (pisah dengan koma)"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Folder</label>
            <select
              value={docForm.folder_id}
              onChange={e => setDocForm(p => ({ ...p, folder_id: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
            >
              <option value="">— Tanpa Folder —</option>
              {folders.map(f => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button onClick={() => setDocModal(false)} className="px-4 py-2 text-sm rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
              Batal
            </button>
            <button
              onClick={saveDoc}
              disabled={saving || !docForm.title.trim()}
              className="px-4 py-2 text-sm rounded-xl font-semibold bg-yellow-500 hover:bg-yellow-600 text-white transition-colors disabled:opacity-50"
            >
              {saving ? "Menyimpan..." : "Simpan"}
            </button>
          </div>
        </div>
      </Modal>

      {/* Folder Modal */}
      <Modal open={folderModal} onClose={() => setFolderModal(false)} title={editingFolder ? "Edit Folder" : "Folder Baru"}>
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Nama Folder</label>
            <input
              autoFocus
              value={folderForm.name}
              onChange={e => setFolderForm(p => ({ ...p, name: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
              placeholder="Nama folder..."
              onKeyDown={e => e.key === "Enter" && saveFolder()}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">Warna</label>
            <div className="flex gap-2 flex-wrap">
              {FOLDER_COLORS.map(c => (
                <button
                  key={c.hex}
                  type="button"
                  title={c.label}
                  onClick={() => setFolderForm(p => ({ ...p, color: c.hex }))}
                  className={`w-8 h-8 rounded-full transition-all border-2 ${folderForm.color === c.hex ? "border-neutral-800 dark:border-white scale-110" : "border-transparent hover:scale-105"}`}
                  style={{ backgroundColor: c.hex }}
                />
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button onClick={() => setFolderModal(false)} className="px-4 py-2 text-sm rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
              Batal
            </button>
            <button
              onClick={saveFolder}
              disabled={saving || !folderForm.name.trim()}
              className="px-4 py-2 text-sm rounded-xl font-semibold bg-yellow-500 hover:bg-yellow-600 text-white transition-colors disabled:opacity-50"
            >
              {saving ? "Menyimpan..." : "Simpan"}
            </button>
          </div>
        </div>
      </Modal>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

function DocCard({
  doc,
  folderColor,
  folderName,
  onEdit,
  onDelete,
}: {
  doc: Document;
  folderColor?: string;
  folderName?: string;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const dateStr = new Date(doc.updated_at || doc.created_at).toLocaleDateString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  return (
    <div className="group relative bg-white dark:bg-[#242423] rounded-2xl border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow flex flex-col gap-2">
      {folderColor && (
        <div className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl" style={{ backgroundColor: folderColor }} />
      )}

      <div className="flex items-start justify-between gap-2 mt-1">
        <h3 className="text-sm font-bold text-neutral-900 dark:text-neutral-50 leading-snug line-clamp-2 flex-1">{doc.title}</h3>
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <button onClick={onEdit} className="p-1.5 text-neutral-400 hover:text-yellow-500 rounded-lg transition-colors">
            <Edit2 size={13} />
          </button>
          <button onClick={onDelete} className="p-1.5 text-neutral-400 hover:text-red-500 rounded-lg transition-colors">
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {doc.url && (
        <a
          href={doc.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={e => e.stopPropagation()}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 text-xs font-medium hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors w-fit max-w-full"
        >
          <ExternalLink size={10} />
          <span className="truncate max-w-[180px]">{doc.url.replace(/^https?:\/\//, "")}</span>
        </a>
      )}

      {doc.body && (
        <p className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2 leading-relaxed">
          {doc.body.slice(0, 120)}{doc.body.length > 120 ? "…" : ""}
        </p>
      )}

      {doc.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {doc.tags.map(tag => (
            <span key={tag} className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between mt-auto pt-1 border-t border-gray-100 dark:border-gray-800">
        {folderName ? (
          <span className="flex items-center gap-1 text-[10px] text-neutral-400">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: folderColor }} />
            {folderName}
          </span>
        ) : (
          <span className="text-[10px] text-neutral-300 dark:text-neutral-600">Tanpa folder</span>
        )}
        <span className="text-[10px] text-neutral-400">{dateStr}</span>
      </div>
    </div>
  );
}
