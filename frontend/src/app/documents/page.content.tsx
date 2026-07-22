"use client";
import NativeSelect from "../../components/ui/NativeSelect";

import { useState, useEffect, useCallback } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch } from "../../lib/api";
import {
  BarChart3, ChevronLeft, ChevronRight, Edit2, ExternalLink, Eye, FileText,
  Folder, FolderOpen, Home, Plus, Search, Trash2,
} from "lucide-react";
import Toast from "../../components/Toast";
import ConfirmModal from "../../components/Modal";
import { useAuth } from "../../contexts/AuthContext";
import { Modal, DocForm, FolderForm } from "../../components/documents/DocumentsModal";
import { DocCard } from "../../components/documents/DocCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const SIDEBAR_KEY = "kt_docs_sidebar_collapsed";
const FLOW_CARDS_KEY = "kt_docs_flow_hidden";
const FOLDER_TREE_KEY = "kt_docs_folder_tree_collapsed";

interface DocumentFolder {
  id: string; name: string; parent_id: string | null; color: string;
  lead_id?: number | null; lead_name?: string | null; created_at: string;
}

interface Document {
  id: string; folder_id: string | null; title: string; body: string | null;
  url: string | null; tags: string[]; file_size?: number | null;
  lead_id?: number | null; lead_name?: string | null;
  created_at: string; updated_at: string | null;
}

interface ClientOption {
  lead_id: number;
  business_name: string;
}

interface FolderDeleteSummary {
  folder_id: string;
  folder_name: string;
  folder_count: number;
  subfolder_count: number;
  document_count: number;
}

function folderBgClass(color: string): string {
  const c = (color || "").toLowerCase();
  if (c === "#6b7280" || c === "#9ca3af") return "bg-neutral-200 dark:bg-neutral-700";
  if (c === "#3b82f6" || c === "#60a5fa") return "bg-blue-100 dark:bg-blue-900/30";
  if (c === "#22c55e" || c === "#4ade80") return "bg-green-100 dark:bg-green-900/30";
  if (c === "#eab308" || c === "#facc15") return "bg-yellow-100 dark:bg-yellow-900/30";
  if (c === "#ef4444" || c === "#f87171") return "bg-red-100 dark:bg-red-900/30";
  if (c === "#a855f7" || c === "#c084fc") return "bg-purple-100 dark:bg-purple-900/30";
  return "bg-neutral-200 dark:bg-neutral-700";
}

function folderTextClass(color: string): string {
  const c = (color || "").toLowerCase();
  if (c === "#6b7280" || c === "#9ca3af") return "text-neutral-800 dark:text-neutral-200";
  if (c === "#3b82f6" || c === "#60a5fa") return "text-blue-700 dark:text-blue-300";
  if (c === "#22c55e" || c === "#4ade80") return "text-green-700 dark:text-green-300";
  if (c === "#eab308" || c === "#facc15") return "text-yellow-700 dark:text-yellow-300";
  if (c === "#ef4444" || c === "#f87171") return "text-red-700 dark:text-red-300";
  if (c === "#a855f7" || c === "#c084fc") return "text-purple-700 dark:text-purple-300";
  return "text-neutral-800 dark:text-neutral-200";
}

function readFlag(key: string, fallback = false): boolean {
  if (typeof window === "undefined") return fallback;
  try {
    return localStorage.getItem(key) === "1";
  } catch {
    return fallback;
  }
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
  const [docForm, setDocForm] = useState({ title: "", body: "", url: "", tags: "", folder_id: "", lead_id: "" });
  const [docFile, setDocFile] = useState<File | null>(null);
  const [folderModal, setFolderModal] = useState(false);
  const [editingFolder, setEditingFolder] = useState<DocumentFolder | null>(null);
  const [folderForm, setFolderForm] = useState({ name: "", color: "#6B7280", parent_id: "", lead_id: "" });
  const [dragOverFolder, setDragOverFolder] = useState<string | null>(null);
  const [dragOverRoot, setDragOverRoot] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [flowHidden, setFlowHidden] = useState(false);
  const [viewDoc, setViewDoc] = useState<Document | null>(null);
  const [moveDoc, setMoveDoc] = useState<Document | null>(null);
  const [moveFolderId, setMoveFolderId] = useState("");
  const [collapsedFolderIds, setCollapsedFolderIds] = useState<Set<string>>(new Set());
  const [clients, setClients] = useState<ClientOption[]>([]);

  useEffect(() => {
    setSidebarCollapsed(readFlag(SIDEBAR_KEY));
    setFlowHidden(readFlag(FLOW_CARDS_KEY));
    try {
      const raw = localStorage.getItem(FOLDER_TREE_KEY);
      if (raw) setCollapsedFolderIds(new Set(JSON.parse(raw) as string[]));
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    apiFetch("/api/contacts")
      .then(r => (r.ok ? r.json() : []))
      .then((rows: { lead_id?: number | null; business_name?: string }[]) => {
        const mapped = (Array.isArray(rows) ? rows : [])
          .filter(c => c.lead_id)
          .map(c => ({ lead_id: c.lead_id as number, business_name: c.business_name || `Lead #${c.lead_id}` }));
        // de-dupe by lead_id
        const seen = new Set<number>();
        setClients(mapped.filter(c => (seen.has(c.lead_id) ? false : (seen.add(c.lead_id), true))));
      })
      .catch(() => setClients([]));
  }, []);

  const showUnfoldered = searchParams.get("unfoldered") === "1";
  // showAll=1 → explicit "semua termasuk yang di folder"; default root hides foldered docs
  const showAll = searchParams.get("all") === "1";
  const selectedFolder = searchParams.get("folder") || null;

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

  // Root default: hide docs that already live in a folder (unfoldered only + folder cards)
  function selectRoot() { setSearch(""); updateQuery({ folder: null, unfoldered: "1", all: null, search: null }); }
  function selectAllIncludingFoldered() { setSearch(""); updateQuery({ folder: null, unfoldered: null, all: "1", search: null }); }
  function selectFolder(id: string) { setSearch(""); updateQuery({ folder: id, unfoldered: null, all: null, search: null }); }

  function handleSearch(value: string) {
    setSearch(value);
    if (value) updateQuery({ search: value });
    else updateQuery({ search: null });
  }

  function toggleSidebar() {
    setSidebarCollapsed(prev => {
      const next = !prev;
      try { localStorage.setItem(SIDEBAR_KEY, next ? "1" : "0"); } catch { /* ignore */ }
      return next;
    });
  }

  function toggleFlowCards() {
    setFlowHidden(prev => {
      const next = !prev;
      try { localStorage.setItem(FLOW_CARDS_KEY, next ? "1" : "0"); } catch { /* ignore */ }
      return next;
    });
  }

  const folderById = new Map(folders.map(f => [f.id, f]));
  const childFolders = folders.filter(f => (selectedFolder ? f.parent_id === selectedFolder : f.parent_id === null));
  const isRootUnfoldered = !selectedFolder && (showUnfoldered || (!showAll && !search));
  const activeLabel = selectedFolder
    ? folderById.get(selectedFolder)?.name || "Folder"
    : showAll
      ? "Semua Dokumen"
      : "Tanpa Folder";
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
    if (selectedFolder) {
      params.set("folder_id", selectedFolder);
    } else if (search) {
      // global search: all docs
    } else if (showAll) {
      // all docs including foldered
    } else {
      // default root / unfoldered: hide docs that already live in folders
      params.set("unfoldered", "true");
    }
    if (search) params.set("search", search);
    params.set("limit", "200");
    const res = await apiFetch(`/api/archive?${params.toString()}`);
    if (res.ok) setDocs(await res.json());
  }, [selectedFolder, showUnfoldered, showAll, search]);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchFolders(), fetchDocs()]).finally(() => setLoading(false));
  }, [fetchFolders, fetchDocs]);

  // First visit without query → default to unfoldered root (hide foldered docs)
  useEffect(() => {
    if (!searchParams.get("folder") && !searchParams.get("unfoldered") && !searchParams.get("all") && !searchParams.get("search")) {
      updateQuery({ unfoldered: "1" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function openNewDoc() {
    setEditingDoc(null);
    setDocForm({ title: "", body: "", url: "", tags: "", folder_id: selectedFolder || "", lead_id: "" });
    setDocFile(null);
    setDocModal(true);
  }

  function openEditDoc(doc: Document) {
    setEditingDoc(doc);
    setViewDoc(null);
    setDocForm({
      title: doc.title,
      body: doc.body || "",
      url: doc.url || "",
      tags: doc.tags.join(", "),
      folder_id: doc.folder_id || "",
      lead_id: doc.lead_id ? String(doc.lead_id) : "",
    });
    setDocFile(null);
    setDocModal(true);
  }

  function toggleFolderExpand(folderId: string, e: React.MouseEvent) {
    e.stopPropagation();
    setCollapsedFolderIds(prev => {
      const next = new Set(prev);
      if (next.has(folderId)) next.delete(folderId);
      else next.add(folderId);
      try { localStorage.setItem(FOLDER_TREE_KEY, JSON.stringify(Array.from(next))); } catch { /* ignore */ }
      return next;
    });
  }

  function folderPathLabel(folderId: string | null): string {
    if (!folderId) return "Tanpa Folder";
    const parts: string[] = [];
    let current = folderById.get(folderId);
    const seen = new Set<string>();
    while (current && !seen.has(current.id)) {
      parts.unshift(current.name);
      seen.add(current.id);
      current = current.parent_id ? folderById.get(current.parent_id) : undefined;
    }
    return parts.join(" / ") || "Folder";
  }

  function openMoveDoc(doc: Document) {
    setMoveDoc(doc);
    setMoveFolderId(doc.folder_id || "");
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
    const payload = {
      title: docForm.title.trim(),
      body: docForm.body || null,
      url: docForm.url || null,
      tags,
      folder_id: docForm.folder_id || null,
      lead_id: docForm.lead_id ? Number(docForm.lead_id) : null,
    };
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
      } else {
        const err = await res.json().catch(() => ({}));
        setToast({ message: typeof err.detail === "string" ? err.detail : "Gagal menyimpan dokumen", type: "error" });
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
    setFolderForm({ name: "", color: "#6B7280", parent_id: selectedFolder || "", lead_id: "" });
    setFolderModal(true);
  }

  function openEditFolder(folder: DocumentFolder, e: React.MouseEvent) {
    e.stopPropagation();
    setEditingFolder(folder);
    setFolderForm({ name: folder.name, color: folder.color || "#6B7280", parent_id: folder.parent_id || "", lead_id: folder.lead_id ? String(folder.lead_id) : "" });
    setFolderModal(true);
  }

  async function saveFolder() {
    if (!folderForm.name.trim()) return;
    setSaving(true);
    try {
      const method = editingFolder ? "PUT" : "POST";
      const url = editingFolder ? `/api/archive/folders/${editingFolder.id}` : "/api/archive/folders";
      const payload = {
        name: folderForm.name.trim(),
        color: folderForm.color || "#6B7280",
        parent_id: folderForm.parent_id || null,
        lead_id: folderForm.lead_id ? Number(folderForm.lead_id) : null,
      };
      const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
      if (res.ok) {
        setFolderModal(false);
        setToast({ message: editingFolder ? "Folder diperbarui" : "Folder dibuat", type: "success" });
        fetchFolders();
      } else {
        const err = await res.json().catch(() => ({}));
        const detail = typeof err.detail === "string" ? err.detail : Array.isArray(err.detail) ? err.detail.map((d: any) => d.msg || d).join(", ") : "Gagal menyimpan folder";
        setToast({ message: detail, type: "error" });
      }
    } catch (e: any) {
      setToast({ message: e.message || "Gagal menyimpan folder", type: "error" });
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
      if (selectedFolder === id) selectRoot();
      setToast({ message: "Folder dan isinya dihapus", type: "success" });
      fetchFolders();
      fetchDocs();
    } else { setToast({ message: "Gagal menghapus folder", type: "error" }); }
  }

  async function moveDocument(docId: string, targetFolderId: string | null) {
    try {
      const res = await apiFetch(`/api/archive/${docId}`, {
        method: "PUT",
        body: JSON.stringify({ folder_id: targetFolderId }),
      });
      if (res.ok) {
        setToast({ message: "Dokumen dipindahkan", type: "success" });
        setMoveDoc(null);
        fetchDocs();
      } else {
        const err = await res.json().catch(() => ({}));
        setToast({ message: typeof err.detail === "string" ? err.detail : "Gagal memindahkan dokumen", type: "error" });
      }
    } catch {
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
    if (docId) moveDocument(docId, folderId);
  }

  function handleDropOnRoot(e: React.DragEvent) {
    e.preventDefault();
    setDragOverRoot(false);
    const docId = e.dataTransfer.getData("text/plain");
    if (docId) moveDocument(docId, null);
  }

  function renderFolderTree(parentId: string | null = null, depth = 0): ReactNode {
    return folders
      .filter(folder => folder.parent_id === parentId)
      .map(folder => {
        const isSelected = selectedFolder === folder.id;
        const hasChildren = folders.some(f => f.parent_id === folder.id);
        const isCollapsed = collapsedFolderIds.has(folder.id);
        // Keep ancestors of selected folder expanded even if marked collapsed
        const onSelectedPath = !!selectedFolder && (() => {
          let cur = selectedFolder ? folderById.get(selectedFolder) : null;
          const seen = new Set<string>();
          while (cur && !seen.has(cur.id)) {
            if (cur.id === folder.id) return true;
            seen.add(cur.id);
            cur = cur.parent_id ? folderById.get(cur.parent_id) : undefined;
          }
          return false;
        })();
        const showChildren = hasChildren && (!isCollapsed || onSelectedPath);
        const bgClass = folderBgClass(folder.color);
        const textClass = folderTextClass(folder.color);
        const isDragOver = dragOverFolder === folder.id;
        return (
          <div key={folder.id}
            onDragOver={e => handleDragOver(e, folder.id)}
            onDragLeave={() => setDragOverFolder(null)}
            onDrop={e => handleDropOnFolder(e, folder.id)}>
            <div onClick={() => selectFolder(folder.id)}
              className={`group flex cursor-pointer items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors ${isSelected ? `${bgClass} ${textClass} font-semibold` : "text-neutral-600 dark:text-neutral-400 hover:bg-amber-50/70 dark:hover:bg-amber-950/20"} ${isDragOver ? "ring-2 ring-amber-400 bg-amber-50 dark:bg-amber-950/30" : ""}`}
              style={{ paddingLeft: `${12 + depth * 14}px` }}>
              {hasChildren ? (
                <button
                  type="button"
                  onClick={e => toggleFolderExpand(folder.id, e)}
                  className="shrink-0 rounded p-0.5 text-neutral-400 hover:bg-amber-100 hover:text-amber-700 dark:hover:bg-amber-950/30"
                  title={showChildren ? "Ciutkan subfolder" : "Perluas subfolder"}
                  aria-label={showChildren ? "Ciutkan" : "Perluas"}
                >
                  {showChildren ? <ChevronLeft size={12} className="rotate-[-90deg]" /> : <ChevronRight size={12} />}
                </button>
              ) : (
                <span className="w-3 shrink-0" />
              )}
              <span className="w-2.5 h-2.5 rounded-full shrink-0 mt-px" style={{ backgroundColor: folder.color }} />
              <span className="flex-1 truncate">{folder.name}</span>
              {(folder.lead_name || clients.find(c => c.lead_id === folder.lead_id)?.business_name) && (
                <span className="max-w-[72px] truncate rounded bg-blue-50 px-1 text-[9px] font-semibold text-blue-700 dark:bg-blue-950/30 dark:text-blue-300" title={folder.lead_name || clients.find(c => c.lead_id === folder.lead_id)?.business_name || ""}>
                  {folder.lead_name || clients.find(c => c.lead_id === folder.lead_id)?.business_name}
                </span>
              )}
              <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                <button type="button" onClick={e => openEditFolder(folder, e)} className="p-0.5 hover:text-neutral-500 transition-colors"><Edit2 size={11} /></button>
                {isAdmin && (
                  <button type="button" onClick={e => { e.stopPropagation(); confirmDeleteFolder(folder.id); }} className="p-0.5 hover:text-red-500 transition-colors"><Trash2 size={11} /></button>
                )}
              </div>
            </div>
            {showChildren && renderFolderTree(folder.id, depth + 1)}
          </div>
        );
      });
  }

  const viewUrl = viewDoc?.url
    ? (viewDoc.url.startsWith("/") ? `${API_BASE}${viewDoc.url}` : viewDoc.url)
    : null;

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
      <aside className={`flex shrink-0 flex-col gap-1 rounded-2xl border border-amber-100 bg-white p-3 shadow-sm transition-all dark:border-amber-900/40 dark:bg-[var(--bg-surface)] ${sidebarCollapsed ? "w-full md:w-14" : "w-full md:w-56"}`}>
        <div className={`mb-1 flex items-center ${sidebarCollapsed ? "justify-center" : "justify-between"}`}>
          {!sidebarCollapsed && <span className="px-1 text-[10px] font-bold uppercase tracking-wide text-neutral-400">Folder</span>}
          <button type="button" onClick={toggleSidebar} title={sidebarCollapsed ? "Perluas sidebar" : "Sembunyikan sidebar"}
            className="rounded-lg p-1.5 text-neutral-400 hover:bg-amber-50 hover:text-amber-700 dark:hover:bg-amber-950/20">
            {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        {!sidebarCollapsed && (
          <>
            <button type="button" onClick={selectRoot}
              onDragOver={handleDragOverRoot}
              onDragLeave={() => setDragOverRoot(false)}
              onDrop={handleDropOnRoot}
              className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-medium transition-colors ${isRootUnfoldered ? "bg-amber-50 text-amber-800 dark:bg-amber-950/20 dark:text-amber-300 font-semibold" : "text-neutral-600 dark:text-neutral-400 hover:bg-amber-50/70 dark:hover:bg-amber-950/20"} ${dragOverRoot ? "ring-2 ring-amber-400 bg-amber-50 dark:bg-amber-950/30" : ""}`}>
              <FileText size={15} /> Tanpa Folder
            </button>
            <button type="button" onClick={selectAllIncludingFoldered}
              className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-medium transition-colors ${showAll && !selectedFolder ? "bg-amber-50 text-amber-800 dark:bg-amber-950/20 dark:text-amber-300 font-semibold" : "text-neutral-600 dark:text-neutral-400 hover:bg-amber-50/70 dark:hover:bg-amber-950/20"}`}>
              <FolderOpen size={15} /> Semua (termasuk folder)
            </button>
            <div className="my-1 border-t border-neutral-100 dark:border-neutral-800" />
            {renderFolderTree()}
            <button type="button" onClick={openNewFolder}
              className="mt-2 flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-amber-700 transition-colors hover:bg-amber-50 dark:text-amber-300 dark:hover:bg-amber-950/20">
              <Plus size={13} /> Folder Baru
            </button>
            <p className="mt-1 px-2 text-[10px] leading-relaxed text-neutral-400">
              Drag kartu ke folder, atau ikon pindah. Chevron ciutkan subfolder. Kredensial klien ≠ folder arsip.
            </p>
          </>
        )}

        {sidebarCollapsed && (
          <div className="flex flex-col items-center gap-2 pt-1">
            <button type="button" onClick={selectRoot} title="Tanpa Folder" className="rounded-lg p-2 text-amber-700 hover:bg-amber-50 dark:text-amber-300"><FileText size={16} /></button>
            <button type="button" onClick={openNewFolder} title="Folder Baru" className="rounded-lg p-2 text-amber-700 hover:bg-amber-50 dark:text-amber-300"><Plus size={16} /></button>
          </div>
        )}
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col gap-4">
        <div className="rounded-2xl border border-amber-100 bg-white p-4 shadow-sm dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-50">Dokumen</h1>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">Hub: dokumen resmi, proposal, laporan klien (delivery), audit lead, dan arsip tim.</p>
            </div>
            <button type="button" onClick={toggleFlowCards}
              className="shrink-0 rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800">
              {flowHidden ? "Tampil flow" : "Sembunyi flow"}
            </button>
          </div>
          {!flowHidden && (
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
                <p className="text-sm font-bold text-neutral-900 dark:text-neutral-100">Laporan Delivery (PDF)</p>
                <p className="mt-1 text-xs text-neutral-500">PDF bulanan/selesai proyek + link tracked /client-report. Beda dari report web audit di Prospek.</p>
              </Link>
              <Link href="/leads" className="rounded-xl border border-neutral-200 bg-neutral-50 p-3 transition hover:border-amber-300 hover:bg-amber-50 dark:border-neutral-800 dark:bg-neutral-900 dark:hover:bg-amber-950/20">
                <Search className="mb-2 h-5 w-5 text-amber-600" />
                <p className="text-sm font-bold text-neutral-900 dark:text-neutral-100">Report Web (WA blast)</p>
                <p className="mt-1 text-xs text-neutral-500">Audit digital interaktif /report/&#123;slug&#125; — tombol di Prospek (Lihat Report / Chat WA). Bukan PDF delivery.</p>
              </Link>
            </div>
          )}
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
          <button type="button" onClick={openNewDoc}
            className="flex shrink-0 items-center gap-1.5 rounded-xl bg-amber-500 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-amber-600">
            <Plus size={15} /> Tambah Dokumen
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-1 rounded-xl border border-amber-100 bg-white px-3 py-2 text-xs text-neutral-500 dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
          <button type="button" onClick={selectRoot} className="inline-flex items-center gap-1 rounded-lg px-2 py-1 font-semibold text-neutral-700 hover:bg-amber-50 dark:text-neutral-300 dark:hover:bg-amber-950/20">
            <Home size={13} /> Arsip
          </button>
          {showAll && !selectedFolder ? (
            <>
              <ChevronRight size={13} />
              <span className="rounded-lg bg-amber-50 px-2 py-1 font-semibold text-amber-800 dark:bg-amber-950/20 dark:text-amber-300">Semua dokumen</span>
            </>
          ) : isRootUnfoldered ? (
            <>
              <ChevronRight size={13} />
              <span className="rounded-lg bg-amber-50 px-2 py-1 font-semibold text-amber-800 dark:bg-amber-950/20 dark:text-amber-300">Tanpa Folder</span>
            </>
          ) : breadcrumbs.map(folder => (
            <span key={folder.id} className="inline-flex items-center gap-1">
              <ChevronRight size={13} />
              <button type="button" onClick={() => selectFolder(folder.id)} className="rounded-lg px-2 py-1 font-semibold text-neutral-700 hover:bg-amber-50 dark:text-neutral-300 dark:hover:bg-amber-950/20">{folder.name}</button>
            </span>
          ))}
        </div>

        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
          <input value={search} onChange={e => handleSearch(e.target.value)} placeholder="Cari dokumen..."
            className="w-full rounded-xl border border-amber-100 bg-white py-2.5 pl-9 pr-4 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-amber-900/40 dark:bg-[var(--bg-surface)]" />
        </div>

        {childFolders.length > 0 && !search && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {childFolders.map(folder => (
              <div key={folder.id} onClick={() => selectFolder(folder.id)}
                onDragOver={e => handleDragOver(e, folder.id)}
                onDragLeave={() => setDragOverFolder(null)}
                onDrop={e => handleDropOnFolder(e, folder.id)}
                className={`group flex cursor-pointer items-center gap-3 rounded-xl border border-amber-100 bg-white p-4 shadow-sm transition hover:border-amber-300 hover:shadow-md dark:border-amber-900/40 dark:bg-[var(--bg-surface)] ${dragOverFolder === folder.id ? "ring-2 ring-amber-400" : ""}`}>
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${folderBgClass(folder.color)}`}>
                  <FolderOpen size={18} className={folderTextClass(folder.color)} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-neutral-800 dark:text-neutral-100">{folder.name}</p>
                  <p className="text-xs text-neutral-400">Drop dokumen di sini untuk pindah</p>
                </div>
                <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <button type="button" onClick={e => openEditFolder(folder, e)} className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 dark:hover:bg-neutral-800"><Edit2 size={13} /></button>
                  {isAdmin && <button type="button" onClick={e => { e.stopPropagation(); confirmDeleteFolder(folder.id); }} className="rounded-lg p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/20"><Trash2 size={13} /></button>}
                </div>
              </div>
            ))}
          </div>
        )}

        {loading ? (
          <div className="py-16 text-center text-sm text-neutral-400">Memuat…</div>
        ) : docs.length === 0 && childFolders.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center py-20 text-center">
            <FileText size={40} className="text-neutral-300 dark:text-neutral-600 mb-3" />
            <p className="text-neutral-500 dark:text-neutral-400 text-sm">
              {search ? "Tidak ada dokumen yang cocok." : "Belum ada dokumen di sini."}
            </p>
            {!search && (
              <button type="button" onClick={openNewDoc} className="mt-4 flex items-center gap-1.5 rounded-xl bg-amber-500 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-amber-600">
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
                clientName={doc.lead_name || clients.find(c => c.lead_id === doc.lead_id)?.business_name || null}
                onView={() => setViewDoc(doc)}
                onEdit={() => openEditDoc(doc)}
                onMove={() => openMoveDoc(doc)}
                onDelete={isAdmin ? () => setDeleteTarget({ id: doc.id, type: "doc" }) : undefined}
              />
            ))}
          </div>
        )}
      </div>

      {/* Document Modal */}
      <Modal open={docModal} onClose={() => setDocModal(false)} title={editingDoc ? "Edit Dokumen" : "Dokumen Baru"} size="lg">
        <DocForm form={docForm} onChange={setDocForm} folders={folders} clients={clients}
          attachmentFile={docFile} onFileChange={setDocFile}
          onSave={saveDoc} onCancel={() => setDocModal(false)} saving={saving} />
      </Modal>

      {/* Folder Modal */}
      <Modal open={folderModal} onClose={() => setFolderModal(false)} title={editingFolder ? "Edit Folder" : "Folder Baru"}>
        <FolderForm form={folderForm} onChange={setFolderForm} folders={folders} clients={clients}
          onSave={saveFolder} onCancel={() => setFolderModal(false)} saving={saving} editingId={editingFolder?.id} />
      </Modal>

      {/* View-only Modal */}
      <Modal open={!!viewDoc} onClose={() => setViewDoc(null)} title={viewDoc?.title || "Dokumen"} size="xl">
        {viewDoc && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-500">
              <span className="rounded-lg bg-neutral-100 px-2 py-1 dark:bg-neutral-800">{folderPathLabel(viewDoc.folder_id)}</span>
              {(viewDoc.lead_name || clients.find(c => c.lead_id === viewDoc.lead_id)?.business_name) && (
                <span className="rounded-lg bg-blue-50 px-2 py-1 font-medium text-blue-700 dark:bg-blue-950/30 dark:text-blue-300">
                  {viewDoc.lead_name || clients.find(c => c.lead_id === viewDoc.lead_id)?.business_name}
                </span>
              )}
            </div>
            {viewUrl && (
              <a href={viewUrl} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-xl bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-100 dark:bg-blue-950/30 dark:text-blue-300">
                <ExternalLink size={14} /> Buka link / file
              </a>
            )}
            {viewDoc.body ? (
              <div className="max-h-[50vh] overflow-y-auto whitespace-pre-wrap rounded-xl bg-neutral-50 p-4 text-sm text-neutral-700 dark:bg-neutral-900 dark:text-neutral-200">
                {viewDoc.body}
              </div>
            ) : (
              <p className="text-sm text-neutral-400">Tidak ada catatan.</p>
            )}
            {viewDoc.tags?.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {viewDoc.tags.map(tag => (
                  <span key={tag} className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">{tag}</span>
                ))}
              </div>
            )}
            <div className="flex flex-wrap justify-end gap-2 pt-2">
              <button type="button" onClick={() => openMoveDoc(viewDoc)} className="rounded-xl bg-neutral-100 px-3 py-2 text-sm font-semibold text-neutral-700 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-200">
                Pindah ke folder…
              </button>
              <button type="button" onClick={() => openEditDoc(viewDoc)} className="inline-flex items-center gap-1.5 rounded-xl bg-amber-500 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-600">
                <Edit2 size={14} /> Edit
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Move folder Modal */}
      <Modal open={!!moveDoc} onClose={() => setMoveDoc(null)} title="Pindah ke Folder" size="lg">
        {moveDoc && (
          <div className="space-y-4">
            <p className="text-sm text-neutral-600 dark:text-neutral-300">
              Pindahkan <span className="font-semibold">{moveDoc.title}</span>
            </p>
            <p className="text-xs text-neutral-500">
              Saat ini: <span className="font-semibold text-neutral-700 dark:text-neutral-200">{folderPathLabel(moveDoc.folder_id)}</span>
              {" → "}
              target: <span className="font-semibold text-amber-700 dark:text-amber-300">{folderPathLabel(moveFolderId || null)}</span>
            </p>
            <NativeSelect
              value={moveFolderId}
              onChange={setMoveFolderId}
              placeholder="— Tanpa Folder —"
              searchPlaceholder="Cari folder…"
              options={[...folders]
                .sort((a, b) => folderPathLabel(a.id).localeCompare(folderPathLabel(b.id), "id"))
                .map(f => ({ value: f.id, label: folderPathLabel(f.id) }))}
            />
            <p className="text-[11px] text-neutral-400">Tip: drag-drop kartu ke folder di sidebar juga bisa. Kredensial/password → tab Kredensial di detail klien, bukan folder arsip.</p>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setMoveDoc(null)} className="rounded-xl bg-gray-100 px-4 py-2 text-sm dark:bg-neutral-800">Batal</button>
              <button type="button" onClick={() => moveDocument(moveDoc.id, moveFolderId || null)}
                className="rounded-xl bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600">
                Pindahkan
              </button>
            </div>
          </div>
        )}
      </Modal>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
