"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../lib/api";
import { Plus, Trash2, Folder, FileText, Search, Edit2 } from "lucide-react";
import Toast from "../../components/Toast";
import ConfirmModal from "../../components/Modal";
import { useAuth } from "../../contexts/AuthContext";
import { Modal, DocForm, FolderForm } from "../../components/documents/DocumentsModal";
import { DocCard } from "../../components/documents/DocCard";

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

export default function DocumentsPage() {
  const { isAdmin } = useAuth();
  const [folders, setFolders] = useState<DocumentFolder[]>([]);
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [showUnfoldered, setShowUnfoldered] = useState(false);
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; type: "doc" | "folder" } | null>(null);

  const [docModal, setDocModal] = useState(false);
  const [editingDoc, setEditingDoc] = useState<Document | null>(null);
  const [docForm, setDocForm] = useState({ title: "", body: "", url: "", tags: "", folder_id: "" });

  const [folderModal, setFolderModal] = useState(false);
  const [editingFolder, setEditingFolder] = useState<DocumentFolder | null>(null);
  const [folderForm, setFolderForm] = useState({ name: "", color: "#6B7280", parent_id: "" });

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
    const tags = docForm.tags.split(",").map(t => t.trim()).filter(Boolean);
    const payload = { title: docForm.title.trim(), body: docForm.body || null, url: docForm.url || null, tags, folder_id: docForm.folder_id || null };
    try {
      const method = editingDoc ? "PUT" : "POST";
      const url = editingDoc ? `/api/archive/${editingDoc.id}` : "/api/archive";
      const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
      if (res.ok) { setDocModal(false); setToast({ message: editingDoc ? "Dokumen diperbarui" : "Dokumen disimpan", type: "success" }); fetchDocs(); }
      else { setToast({ message: "Gagal menyimpan dokumen", type: "error" }); }
    } finally { setSaving(false); }
  }

  async function deleteDoc(id: string) {
    const res = await apiFetch(`/api/archive/${id}`, { method: "DELETE" });
    if (res.ok) { setDocs(prev => prev.filter(d => d.id !== id)); setToast({ message: "Dokumen dihapus", type: "success" }); }
    else { setToast({ message: "Gagal menghapus", type: "error" }); }
  }

  function openNewFolder() {
    setEditingFolder(null);
    setFolderForm({ name: "", color: "#6B7280", parent_id: "" });
    setFolderModal(true);
  }

  function openEditFolder(folder: DocumentFolder, e: React.MouseEvent) {
    e.stopPropagation();
    setEditingFolder(folder);
    setFolderForm({ name: folder.name, color: folder.color, parent_id: folder.parent_id || "" });
    setFolderModal(true);
  }

  async function saveFolder() {
    if (!folderForm.name.trim()) return;
    setSaving(true);
    try {
      const method = editingFolder ? "PUT" : "POST";
      const url = editingFolder ? `/api/archive/folders/${editingFolder.id}` : "/api/archive/folders";
      const res = await apiFetch(url, { method, body: JSON.stringify({ name: folderForm.name.trim(), color: folderForm.color, parent_id: folderForm.parent_id || null }) });
      if (res.ok) { setFolderModal(false); setToast({ message: editingFolder ? "Folder diperbarui" : "Folder dibuat", type: "success" }); fetchFolders(); }
      else { setToast({ message: "Gagal menyimpan folder", type: "error" }); }
    } finally { setSaving(false); }
  }

  async function deleteFolder(id: string) {
    const res = await apiFetch(`/api/archive/folders/${id}`, { method: "DELETE" });
    if (res.ok) { setFolders(prev => prev.filter(f => f.id !== id)); if (selectedFolder === id) setSelectedFolder(null); setToast({ message: "Folder dihapus", type: "success" }); fetchDocs(); }
    else { setToast({ message: "Gagal menghapus folder", type: "error" }); }
  }

  function selectAll() { setSelectedFolder(null); setShowUnfoldered(false); }
  function selectUnfoldered() { setSelectedFolder(null); setShowUnfoldered(true); }
  function selectFolder(id: string) { setSelectedFolder(id); setShowUnfoldered(false); }

  const activeLabel = showUnfoldered ? "Tanpa Folder" : selectedFolder ? folders.find(f => f.id === selectedFolder)?.name || "Folder" : "Semua Dokumen";

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
      <ConfirmModal
        open={!!deleteTarget}
        title={deleteTarget?.type === "folder" ? "Hapus Folder?" : "Hapus Dokumen?"}
        message={deleteTarget?.type === "folder" ? "Folder akan dihapus. Dokumen di dalamnya dipindahkan ke Tanpa Folder." : "Dokumen yang dihapus tidak bisa dikembalikan."}
        confirmLabel="Hapus"
        confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => { if (!deleteTarget) return; if (deleteTarget.type === "folder") deleteFolder(deleteTarget.id); else deleteDoc(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* Sidebar */}
      <aside className="w-full md:w-48 shrink-0 flex flex-col gap-1">
        <button onClick={selectAll}
          className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors text-left w-full ${!showUnfoldered && selectedFolder === null ? "bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300" : "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}>
          <FileText size={15} /> Semua Dokumen
        </button>
        <button onClick={selectUnfoldered}
          className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors text-left w-full ${showUnfoldered ? "bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300" : "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}>
          <FileText size={15} /> Tanpa Folder
        </button>

        <div className="my-1 border-t border-neutral-100 dark:border-neutral-800" />

        {folders.map(folder => (
          <div key={folder.id} onClick={() => selectFolder(folder.id)}
            className={`group flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium cursor-pointer transition-colors ${selectedFolder === folder.id ? "bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300" : "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}>
            <span className="w-2.5 h-2.5 rounded-full shrink-0 mt-px" style={{ backgroundColor: folder.color }} />
            <span className="flex-1 truncate">{folder.parent_id ? `-- ${folder.name}` : folder.name}</span>
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
              <button onClick={e => openEditFolder(folder, e)} className="p-0.5 hover:text-amber-500 transition-colors"><Edit2 size={11} /></button>
              {isAdmin && (
                <button onClick={e => { e.stopPropagation(); setDeleteTarget({ id: folder.id, type: "folder" }); }} className="p-0.5 hover:text-red-500 transition-colors"><Trash2 size={11} /></button>
              )}
            </div>
          </div>
        ))}

        <button onClick={openNewFolder}
          className="mt-2 flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold text-amber-600 dark:text-yellow-400 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 transition-colors">
          <Plus size={13} /> Folder Baru
        </button>
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center shrink-0">
              <Folder size={18} className="text-amber-500" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-50 leading-tight">Arsip Tim</h1>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">{activeLabel} · simpan link Google Docs, Drive, atau Notion</p>
            </div>
          </div>
          <button onClick={openNewDoc}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold bg-amber-500 hover:bg-amber-600 text-white transition-colors shrink-0">
            <Plus size={15} /> Tambah Dokumen
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Cari dokumen..."
            className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-white dark:bg-[var(--bg-canvas)] border border-gray-200 dark:border-gray-700 text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
        </div>

        {/* Documents grid */}
        {docs.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center py-20 text-center">
            <FileText size={40} className="text-neutral-300 dark:text-neutral-600 mb-3" />
            <p className="text-neutral-500 dark:text-neutral-400 text-sm">
              {search ? "Tidak ada dokumen yang cocok." : "Belum ada dokumen di sini."}
            </p>
            {!search && (
              <button onClick={openNewDoc} className="mt-4 flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold bg-amber-500 hover:bg-amber-600 text-white transition-colors">
                <Plus size={14} /> Tambah Pertama
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {docs.map(doc => (
              <DocCard key={doc.id} doc={doc}
                folderColor={folders.find(f => f.id === doc.folder_id)?.color}
                folderName={folders.find(f => f.id === doc.folder_id)?.name}
                onEdit={() => openEditDoc(doc)}
                onDelete={isAdmin ? () => setDeleteTarget({ id: doc.id, type: "doc" }) : undefined}
              />
            ))}
          </div>
        )}
      </div>

      {/* Document Modal */}
      <Modal open={docModal} onClose={() => setDocModal(false)} title={editingDoc ? "Edit Dokumen" : "Dokumen Baru"}>
        <DocForm form={docForm} onChange={setDocForm} folders={folders}
          onSave={saveDoc} onCancel={() => setDocModal(false)} saving={saving} />
      </Modal>

      {/* Folder Modal */}
      <Modal open={folderModal} onClose={() => setFolderModal(false)} title={editingFolder ? "Edit Folder" : "Folder Baru"}>
        <FolderForm form={folderForm} onChange={setFolderForm} folders={folders}
          onSave={saveFolder} onCancel={() => setFolderModal(false)} saving={saving} editingId={editingFolder?.id} />
      </Modal>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}