"use client";

import { useState, useEffect, useCallback } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch } from "../../lib/api";
import { BarChart3, ChevronRight, Edit2, ExternalLink, FileText, Folder, FolderOpen, Home, Plus, Search, Trash2 } from "lucide-react";
import Toast from "../../components/Toast";
import ConfirmModal from "../../components/Modal";
import { useAuth } from "../../contexts/AuthContext";
import { Modal, DocForm, FolderForm } from "../../components/documents/DocumentsModal";
import { DocCard } from "../../components/documents/DocCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DocumentFolder {
  id: string; name: string; parent_id: string | null; color: string; created_at: string;
}

interface Document {
  id: string; folder_id: string | null; title: string; body: string | null;
  url: string | null; tags: string[]; file_size?: number | null; created_at: string; updated_at: string | null;
}

interface FolderDeleteSummary {
  folder_id: string;
  folder_name: string;
  folder_count: number;
  subfolder_count: number;
  document_count: number;
}

function folderBgClass(color: string): string {
  const c = color.toLowerCase();
  if (c === "#6B7280" || c === "#9ca3af") return "bg-neutral-200 dark:bg-neutral-700";
  if (c === "#3B82F6" || c === "#60a5fa") return "bg-blue-100 dark:bg-blue-900/30";
  if (c === "#22C55E" || c === "#4ade80") return "bg-green-100 dark:bg-green-900/30";
  if (c === "#EAB308" || c === "#facc15") return "bg-yellow-100 dark:bg-yellow-900/30";
  if (c === "#EF4444" || c === "#f87171") return "bg-red-100 dark:bg-red-900/30";
  if (c === "#A855F7" || c === "#c084fc") return "bg-purple-100 dark:bg-purple-900/30";
  return "bg-neutral-200 dark:bg-neutral-700";
}

function folderTextClass(color: string): string {
  const c = color.toLowerCase();
  if (c === "#6B7280" || c === "#9ca3af") return "text-neutral-800 dark:text-neutral-200";
  if (c === "#3B82F6" || c === "#60a5fa") return "text-blue-700 dark:text-blue-300";
  if (c === "#22C55E" || c === "#4ade80") return "text-green-700 dark:text-green-300";
  if (c === "#EAB308" || c === "#facc15") return "text-yellow-700 dark:text-yellow-300";
  if (c === "#EF4444" || c === "#f87171") return "text-red-700 dark:text-red-300";
  if (c === "#A855F7" || c === "#c084fc") return "text-purple-700 dark:text-purple-300";
  return "text-neutral-800 dark:text-neutral-200";
}

export default function DocumentsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAdmin } = useAuth();
  const [folders, setFolders] = useState<DocumentFolder[]>([]);
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; type: "doc" | "folder"; summary?: FolderDeleteSummary } | null>(null);
  const [docModal, setDocModal] = useState(false);
  const [editingDoc, setEditingDoc] = useState<Document | null>(null);
  const [docForm, setDocForm] = useState({ title: "", body: "", url: "", tags: "", folder_id: "" });
  const [docFile, setDocFile] = useState<File | null>(null);
  const [folderModal, setFolderModal] = useState(false);
  const [editingFolder, setEditingFolder] = useState<DocumentFolder | null>(null);
  const [folderForm, setFolderForm] = useState({ name: "", color: "#6B7280", parent_id: "" });
  const [dragOverFolder, setDragOverFolder] = useState<string | null>(null);
  const [dragOverRoot, setDragOverRoot] = useState(false);

  const showUnfoldered = searchParams.get("unfoldered") === "1";
  const selectedFolder = searchParams.get("folder") || null;

  // Sync search input when URL search param changes (browser back/forward)
  useEffect(() => {
    const urlSearch = searchParams.get("search") || "";
    if (urlSearch !== search) setSearch(urlSearch);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  function updateQuery(params: Record<string, string | null>) {
    const q = new URLSearchParams(searchParams.toString());
    for (const [k, v] of Object.entries(params)) {
      if (v === null || v === "") q.delete(k);
      else q.set(k, v);
    }
    router.replace(`/documents?${q.toString()}`, { scroll: false });
  }

  function selectAll() { setSearch(""); updateQuery({ folder: null, unfoldered: null, search: null }); }
  function selectUnfoldered() { setSearch(""); updateQuery({ folder: null, unfoldered: "1", search: null }); }
  function selectFolder(id: string) { setSearch(""); updateQuery({ folder: id, unfoldered: null, search: null }); }

  function handleSearch(value: string) {
    setSearch(value);
    if (value) updateQuery({ search: value });
    else updateQuery({ search: null });
  }

  const folderById = new Map(folders.map(f => [f.id, f]));
  const childFolders = folders.filter(f => (selectedFolder ? f.parent_id === selectedFolder : f.parent_id === null));
  const activeLabel = showUnfoldered ? "Tanpa Folder" : selectedFolder ? folderById.get(selectedFolder)?.name || "Folder" : "Semua Dokumen";
  const breadcrumbs = (() => {
    const chain: DocumentFolder[] = [];
    let current = selectedFolder ? folderById.get(selectedFolder) : null;
    const seen = new Set<string>();
    while (current && !seen.has(current.id)) {
      chain.unshift(current);
      seen.add(current.id);
      current = current.parent_id ? folderById.get(current.parent_id) || null : null;
    }
    return chain;
  })();

  const fetchFolders = useCallback(async () => {
    const res = await apiFetch("/api/archive/folders");
    if (res.ok) setFolders(await res.json());
  }, []);

  const fetchDocs = useCallback(async () => {
    const params = new URLSearchParams();
    if (showUnfoldered) params.set("unfoldered", "true");
    else if (selectedFolder) params.set("folder_id", selectedFolder);
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
    setDocForm({ title: "", body: "", url: "", tags: "", folder_id: selectedFolder || "" });
    setDocFile(null);
    setDocModal(true);
  }

  function openEditDoc(doc: Document) {
    setEditingDoc(doc);
    setDocForm({ title: doc.title, body: doc.body || "", url: doc.url || "", tags: doc.tags.join(", "), folder_id: doc.folder_id || "" });
    setDocFile(null);
    setDocModal(true);
  }

  async function uploadArchiveAttachment(docId: string, file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/archive/${docId}/attachment`, {
      method: "POST",
      body: formData,
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Gagal upload file dokumen");
    }
    return res.json();
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
      if (res.ok) {
        const saved = await res.json();
        if (docFile) await uploadArchiveAttachment(saved.id, docFile);
        setDocModal(false);
        setDocFile(null);
        setToast({ message: editingDoc ? "Dokumen diperbarui" : "Dokumen disimpan", type: "success" });
        fetchDocs();
      }
      else {
        const err = await res.json().catch(() => ({}));
        setToast({ message: err.detail || "Gagal menyimpan dokumen", type: "error" });
      }
    } catch (e: any) {
      setToast({ message: e.message || "Gagal menyimpan dokumen", type: "error" });
    } finally { setSaving(false); }
  }

  async function deleteDoc(id: string) {
    const res = await apiFetch(`/api/archive/${id}`, { method: "DELETE" });
    if (res.ok) { setDocs(prev => prev.filter(d => d.id !== id)); setToast({ message: "Dokumen dihapus", type: "success" }); }
    else { setToast({ message: "Gagal menghapus", type: "error" }); }
  }

  function openNewFolder() {
    setEditingFolder(null);
    setFolderForm({ name: "", color: "#6B7280", parent_id: selectedFolder || "" });
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

  async function confirmDeleteFolder(id: string) {
    const res = await apiFetch(`/api/archive/folders/${id}/delete-summary`);
    if (res.ok) {
      setDeleteTarget({ id, type: "folder", summary: await res.json() });
      return;
    }
    setDeleteTarget({ id, type: "folder" });
  }

  async function deleteFolder(id: string) {
    const res = await apiFetch(`/api/archive/folders/${id}`, { method: "DELETE" });
    if (res.ok) {
      setFolders(prev => prev.filter(f => f.id !== id && f.parent_id !== id));
      if (selectedFolder === id) selectAll();
      setToast({ message: "Folder dan isinya dihapus", type: "success" });
      fetchFolders();
      fetchDocs();
    }
    else { setToast({ message: "Gagal menghapus folder", type: "error" }); }
  }

  async function moveDocument(docId: string, targetFolderId: string | null) {
    try {
      const res = await apiFetch(`/api/archive/${docId}`, {
        method: "PUT",
        body: JSON.stringify({ folder_id: targetFolderId })
      });
      if (res.ok) {
        setToast({ message: "Dokumen dipindahkan", type: "success" });
        fetchDocs();
      } else {
        setToast({ message: "Gagal memindahkan dokumen", type: "error" });
      }
    } catch (err) {
      setToast({ message: "Gagal memindahkan dokumen", type: "error" });
    }
  }

  function handleDragOver(e: React.DragEvent, folderId: string) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverFolder(folderId);
  }

  function handleDragOverRoot(e: React.DragEvent) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverRoot(true);
  }

  function handleDropOnFolder(e: React.DragEvent, folderId: string) {
    e.preventDefault();
    setDragOverFolder(null);
    const docId = e.dataTransfer.getData("text/plain");
    if (docId) {
      moveDocument(docId, folderId);
    }
  }

  function handleDropOnRoot(e: React.DragEvent) {
    e.preventDefault();
    setDragOverRoot(false);
    const docId = e.dataTransfer.getData("text/plain");
    if (docId) {
      moveDocument(docId, null);
    }
  }

  function renderFolderTree(parentId: string | null = null, depth = 0): ReactNode {
    return folders
      .filter(folder => folder.parent_id === parentId)
      .map(folder => {
        const isSelected = selectedFolder === folder.id;
        const hasChildren = folders.some(f => f.parent_id === folder.id);
        const bgClass = folderBgClass(folder.color);
        const textClass = folderTextClass(folder.color);
        const isDragOver = dragOverFolder === folder.id;
        return (
          <div key={folder.id}
            draggable={false}
            onDragOver={e => handleDragOver(e, folder.id)}
            onDragLeave={() => setDragOverFolder(null)}
            onDrop={e => handleDropOnFolder(e, folder.id)}>
            <div onClick={() => selectFolder(folder.id)}
              className={`group flex cursor-pointer items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors ${isSelected ? `${bgClass} ${textClass} font-semibold` : "text-neutral-600 dark:text-neutral-400 hover:bg-amber-50/70 dark:hover:bg-amber-950/20"} ${isDragOver ? "ring-2 ring-amber-400 bg-amber-50 dark:bg-amber-950/30" : ""}`}
              style={{ paddingLeft: `${12 + depth * 14}px` }}>
              {hasChildren ? <ChevronRight size={12} className="shrink-0 text-neutral-400" /> : <span className="w-3 shrink-0" />}
              <span className="w-2.5 h-2.5 rounded-full shrink-0 mt-px" style={{ backgroundColor: folder.color }} />
              <span className="flex-1 truncate">{folder.name}</span>
              <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                <button onClick={e => openEditFolder(folder, e)} className="p-0.5 hover:text-neutral-500 transition-colors"><Edit2 size={11} /></button>
                {isAdmin && (
                  <button onClick={e => { e.stopPropagation(); confirmDeleteFolder(folder.id); }} className="p-0.5 hover:text-red-500 transition-colors"><Trash2 size={11} /></button>
                )}
              </div>
            </div>
            {renderFolderTree(folder.id, depth + 1)}
          </div>
        );
      });
  }

  return (
    <div className="flex min-h-full flex-col gap-4 rounded-2xl bg-amber-50/20 p-3 md:flex-row md:gap-6 dark:bg-amber-950/5">
      <ConfirmModal
        open={!!deleteTarget}
        title={deleteTarget?.type === "folder" ? "Hapus Folder?" : "Hapus Dokumen?"}
        message={deleteTarget?.type === "folder"
          ? `Folder "${deleteTarget.summary?.folder_name || "ini"}" akan dihapus permanen beserta ${deleteTarget.summary?.subfolder_count ?? 0} subfolder dan ${deleteTarget.summary?.document_count ?? 0} dokumen di dalamnya.`
          : "Dokumen dihapus permanen."}
        confirmLabel="Hapus" confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={() => { if (!deleteTarget) return; if (deleteTarget.type === "folder") deleteFolder(deleteTarget.id); else deleteDoc(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* Sidebar */}
      <aside className="flex w-full shrink-0 flex-col gap-1 rounded-2xl border border-amber-100 bg-white p-3 shadow-sm md:w-52 dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
        <button onClick={selectAll}
          onDragOver={handleDragOverRoot}
          onDragLeave={() => setDragOverRoot(false)}
          onDrop={handleDropOnRoot}
          className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-medium transition-colors ${!showUnfoldered && selectedFolder === null ? "bg-amber-50 text-amber-800 dark:bg-amber-950/20 dark:text-amber-300 font-semibold" : "text-neutral-600 dark:text-neutral-400 hover:bg-amber-50/70 dark:hover:bg-amber-950/20"} ${dragOverRoot ? "ring-2 ring-amber-400 bg-amber-50 dark:bg-amber-950/30" : ""}`}>
          <FileText size={15} /> Semua Dokumen
        </button>
        <button onClick={selectUnfoldered}
          onDragOver={handleDragOverRoot}
          onDragLeave={() => setDragOverRoot(false)}
          onDrop={handleDropOnRoot}
          className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-medium transition-colors ${showUnfoldered ? "bg-amber-50 text-amber-800 dark:bg-amber-950/20 dark:text-amber-300 font-semibold" : "text-neutral-600 dark:text-neutral-400 hover:bg-amber-50/70 dark:hover:bg-amber-950/20"} ${dragOverRoot ? "ring-2 ring-amber-400 bg-amber-50 dark:bg-amber-950/30" : ""}`}>
          <FileText size={15} /> Tanpa Folder
        </button>
        <div className="my-1 border-t border-neutral-100 dark:border-neutral-800" />

        {renderFolderTree()}

        <button onClick={openNewFolder}
          className="mt-2 flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-amber-700 transition-colors hover:bg-amber-50 dark:text-amber-300 dark:hover:bg-amber-950/20">
          <Plus size={13} /> Folder Baru
        </button>
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col gap-4">
        <div className="rounded-2xl border border-amber-100 bg-white p-4 shadow-sm dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
          <div className="mb-3">
            <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-50">Dokumen & Laporan</h1>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">Pilih flow dulu supaya dokumen resmi, proposal, laporan klien, dan arsip tidak tercampur.</p>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Link href="/documents/generator/new" className="rounded-xl border border-neutral-200 bg-neutral-50 p-3 transition hover:border-amber-300 hover:bg-amber-50 dark:border-neutral-800 dark:bg-neutral-900 dark:hover:bg-amber-950/20">
              <FileText className="mb-2 h-5 w-5 text-amber-600" />
              <p className="text-sm font-bold text-neutral-900 dark:text-neutral-100">Buat Dokumen Resmi</p>
              <p className="mt-1 text-xs text-neutral-500">Invoice, kontrak, MoU, surat penawaran, proposal PDF.</p>
            </Link>
            <Link href="/proposals" className="rounded-xl border border-neutral-200 bg-neutral-50 p-3 transition hover:border-amber-300 hover:bg-amber-50 dark:border-neutral-800 dark:bg-neutral-900 dark:hover:bg-amber-950/20">
              <ExternalLink className="mb-2 h-5 w-5 text-amber-600" />
              <p className="text-sm font-bold text-neutral-900 dark:text-neutral-100">Buat Proposal</p>
              <p className="mt-1 text-xs text-neutral-500">Proposal sales interaktif dengan accept/reject dan tracking.</p>
            </Link>
            <Link href="/documents/reports" className="rounded-xl border border-neutral-200 bg-neutral-50 p-3 transition hover:border-amber-300 hover:bg-amber-50 dark:border-neutral-800 dark:bg-neutral-900 dark:hover:bg-amber-950/20">
              <BarChart3 className="mb-2 h-5 w-5 text-amber-600" />
              <p className="text-sm font-bold text-neutral-900 dark:text-neutral-100">Buat Laporan Klien</p>
              <p className="mt-1 text-xs text-neutral-500">Bulanan/selesai proyek dari workspace, metric, dan bukti kerja.</p>
            </Link>
            <Link href="/leads" className="rounded-xl border border-neutral-200 bg-neutral-50 p-3 transition hover:border-amber-300 hover:bg-amber-50 dark:border-neutral-800 dark:bg-neutral-900 dark:hover:bg-amber-950/20">
              <Search className="mb-2 h-5 w-5 text-amber-600" />
              <p className="text-sm font-bold text-neutral-900 dark:text-neutral-100">Audit Lead</p>
              <p className="mt-1 text-xs text-neutral-500">Pre-sales report untuk prospek dari scrape/lead.</p>
            </Link>
          </div>
        </div>

        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-100 dark:bg-amber-950/30">
              <Folder size={18} className="text-amber-700 dark:text-amber-300" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-50 leading-tight">Arsip Tim</h2>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">{activeLabel} · simpan link Google Docs, Drive, atau Notion</p>
            </div>
          </div>
          <button onClick={openNewDoc}
            className="flex shrink-0 items-center gap-1.5 rounded-xl bg-amber-500 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-amber-600">
            <Plus size={15} /> Tambah Dokumen
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-1 rounded-xl border border-amber-100 bg-white px-3 py-2 text-xs text-neutral-500 dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
          <button onClick={selectAll} className="inline-flex items-center gap-1 rounded-lg px-2 py-1 font-semibold text-neutral-700 hover:bg-amber-50 dark:text-neutral-300 dark:hover:bg-amber-950/20">
            <Home size={13} /> Arsip
          </button>
          {showUnfoldered ? (
            <>
              <ChevronRight size={13} />
              <span className="rounded-lg bg-amber-50 px-2 py-1 font-semibold text-amber-800 dark:bg-amber-950/20 dark:text-amber-300">Tanpa Folder</span>
            </>
          ) : breadcrumbs.map(folder => (
            <span key={folder.id} className="inline-flex items-center gap-1">
              <ChevronRight size={13} />
              <button onClick={() => selectFolder(folder.id)} className="rounded-lg px-2 py-1 font-semibold text-neutral-700 hover:bg-amber-50 dark:text-neutral-300 dark:hover:bg-amber-950/20">{folder.name}</button>
            </span>
          ))}
        </div>

        {/* Search */}
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
          <input value={search} onChange={e => handleSearch(e.target.value)} placeholder="Cari dokumen..."
            className="w-full rounded-xl border border-amber-100 bg-white py-2.5 pl-9 pr-4 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-amber-900/40 dark:bg-[var(--bg-surface)]" />
        </div>

        {childFolders.length > 0 && !showUnfoldered && !search && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {childFolders.map(folder => (
              <div key={folder.id} onClick={() => selectFolder(folder.id)}
                className="group flex cursor-pointer items-center gap-3 rounded-xl border border-amber-100 bg-white p-4 shadow-sm transition hover:border-amber-300 hover:shadow-md dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${folderBgClass(folder.color)}`}>
                  <FolderOpen size={18} className={folderTextClass(folder.color)} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-neutral-800 dark:text-neutral-100">{folder.name}</p>
                  <p className="text-xs text-neutral-400">Subfolder</p>
                </div>
                <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <button onClick={e => openEditFolder(folder, e)} className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 dark:hover:bg-neutral-800"><Edit2 size={13} /></button>
                  {isAdmin && <button onClick={e => { e.stopPropagation(); confirmDeleteFolder(folder.id); }} className="rounded-lg p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/20"><Trash2 size={13} /></button>}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Documents grid */}
        {docs.length === 0 && childFolders.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center py-20 text-center">
            <FileText size={40} className="text-neutral-300 dark:text-neutral-600 mb-3" />
            <p className="text-neutral-500 dark:text-neutral-400 text-sm">
              {search ? "Tidak ada dokumen yang cocok." : "Belum ada dokumen di sini."}
            </p>
            {!search && (
              <button onClick={openNewDoc} className="mt-4 flex items-center gap-1.5 rounded-xl bg-amber-500 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-amber-600">
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
          attachmentFile={docFile} onFileChange={setDocFile}
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
