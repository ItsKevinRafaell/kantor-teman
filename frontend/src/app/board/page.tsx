"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "../../lib/api";
import { Plus, Trash2, Archive, ArchiveRestore, X, User, Calendar, MessageSquare, CheckSquare, Activity } from "lucide-react";
import Toast from "../../components/Toast";
import ConfirmModal from "../../components/ConfirmModal";
import { useAuth } from "../../contexts/AuthContext";
import { BoardColumnItem } from "../../components/board/BoardColumn";
import { BoardOverviewCard } from "../../components/board/BoardOverview";
import { COLUMN_COLORS, BOARD_TOP_BORDER, CARD_COLORS, LABEL_COLORS } from "../../components/board/types";
import type { Lead, Project, BoardCard, BoardColumn, Board, BoardOverview } from "../../components/board/types";

const COLORS = {
  primary: "bg-amber-500 hover:bg-amber-600 text-white",
  secondary: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700",
};

function Modal({ open, onClose, title, children, size = "md" }: {
  open: boolean; onClose: () => void; title: string; children: React.ReactNode; size?: "sm" | "md" | "lg"
}) {
  if (!open) return null;
  const sizeClass = size === "sm" ? "max-w-sm" : size === "lg" ? "max-w-2xl" : "max-w-lg";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
      <div
        className={`relative bg-white dark:bg-[var(--bg-canvas)] rounded-2xl shadow-2xl ${sizeClass} w-full max-h-[90vh] overflow-y-auto`}
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-white dark:bg-[var(--bg-canvas)] px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between rounded-t-2xl">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">{title}</h2>
          <button onClick={onClose} className="p-1 text-neutral-400 hover:text-neutral-600 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

export default function BoardPage() {
  const { isAdmin } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [board, setBoard] = useState<Board | null>(null);
  const [overview, setOverview] = useState<BoardOverview[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"overview" | "board">("overview");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const [cardModal, setCardModal] = useState<{ open: boolean; card: BoardCard | null; columnId: string }>({ open: false, card: null, columnId: "" });
  const [cardForm, setCardForm] = useState({ title: "", description: "", due_date: "", labels: [] as string[], assignee: "", lead_id: null as number | null, color: "yellow" });
  const [saving, setSaving] = useState(false);
  const [showArchived, setShowArchived] = useState(false);

  const [columnModal, setColumnModal] = useState<{ open: boolean; column: BoardColumn | null }>({ open: false, column: null });
  const [columnName, setColumnName] = useState("");
  const [columnColor, setColumnColor] = useState("yellow");

  const [projectModal, setProjectModal] = useState(false);
  const [projectForm, setProjectForm] = useState({ name: "", type: "FIXED" as "FIXED" | "RETAINER", status: "ACTIVE", nominal: 0, lead_id: null as number | null, color: "yellow" });

  const [draggedCard, setDraggedCard] = useState<{ card: BoardCard; fromColumn: string } | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);

  // Confirm modal
  const [confirmModal, setConfirmModal] = useState<{ open: boolean; title: string; message: string; onConfirm: () => void } | null>(null);
  function showConfirm(title: string, message: string, onConfirm: () => void) {
    setConfirmModal({ open: true, title, message, onConfirm });
  }

  // Overview: show archived projects toggle
  const [showArchivedProjects, setShowArchivedProjects] = useState(false);

  // Project edit modal
  const [editProjectModal, setEditProjectModal] = useState<{ open: boolean; projectId: string } | null>(null);
  const [editProjectForm, setEditProjectForm] = useState({ name: "", type: "FIXED" as "FIXED" | "RETAINER", status: "ACTIVE", nominal: 0, lead_id: null as number | null, color: "yellow" });

  const [filterAssignee, setFilterAssignee] = useState("");
  const [filterDue, setFilterDue] = useState("");

  useEffect(() => { fetchProjects(); fetchOverview(false); fetchLeads(); }, []);
  useEffect(() => { fetchOverview(showArchivedProjects); }, [showArchivedProjects]);

  useEffect(() => {
    if (selectedProject) { fetchBoard(selectedProject); setViewMode("board"); }
    else { setBoard(null); setViewMode("overview"); }
  }, [selectedProject]);

  async function fetchProjects() {
    try { const res = await apiFetch("/api/projects"); if (res.ok) setProjects(await res.json()); }
    catch (e) { console.error(e); }
  }
  async function fetchOverview(archived = false) {
    try {
      const res = await apiFetch(`/api/boards/overview?show_archived=${archived}`);
      if (res.ok) setOverview(await res.json());
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }
  async function fetchLeads() {
    try { const res = await apiFetch("/api/leads"); if (res.ok) setLeads(await res.json()); }
    catch (e) { console.error(e); }
  }
  async function fetchBoard(projectId: string) {
    try { const res = await apiFetch(`/api/projects/${projectId}/board`); if (res.ok) setBoard(await res.json()); }
    catch (e) { console.error(e); }
  }

  async function createProject() {
    if (!projectForm.name.trim()) return;
    setSaving(true);
    try {
      const res = await apiFetch("/api/projects", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: projectForm.name, type: projectForm.type, status: projectForm.status, nominal: projectForm.nominal, lead_id: projectForm.lead_id, color: projectForm.color }),
      });
      if (res.ok) {
        const newProject = await res.json();
        setProjects(prev => [...prev, newProject]);
        setProjectModal(false);
        await fetchOverview();
        setSelectedProject(newProject.id);
        setToast({ message: "Proyek dibuat", type: "success" });
      } else {
        const err = await res.json().catch(() => ({}));
        setToast({ message: err.detail || "Gagal buat proyek", type: "error" });
      }
    } catch (e) { setToast({ message: "Gagal buat proyek", type: "error" }); } finally { setSaving(false); }
  }

  async function updateProjectColor(projectId: string, color: string) {
    try {
      const res = await apiFetch(`/api/projects/${projectId}/color`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ color }),
      });
      if (res.ok) setOverview(prev => prev.map(item => item.project_id === projectId ? { ...item, color } : item));
    } catch (e) { setToast({ message: "Gagal ubah warna", type: "error" }); }
  }

  async function createCard(columnId: string) {
    if (!cardForm.title.trim()) return;
    setSaving(true);
    const effectiveLeadId = currentProject?.lead_id ?? cardForm.lead_id;
    try {
      const res = await apiFetch(`/api/board-columns/${columnId}/cards`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: cardForm.title, description: cardForm.description || null, due_date: cardForm.due_date || null, labels: cardForm.labels, assignee: cardForm.assignee || undefined, lead_id: effectiveLeadId, color: cardForm.color }),
      });
      if (res.ok) {
        const newCard = await res.json();
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => col.id === columnId ? { ...col, cards: [...(col.cards || []), newCard] } : col) } : prev);
        setCardForm({ title: "", description: "", due_date: "", labels: [], assignee: "", lead_id: null, color: "yellow" });
        setCardModal({ open: false, card: null, columnId: "" });
        setToast({ message: "Card dibuat", type: "success" });
      }
    } catch (e) { setToast({ message: "Gagal membuat card", type: "error" }); } finally { setSaving(false); }
  }

  async function updateCard(cardId: string) {
    const effectiveLeadId = currentProject?.lead_id ?? cardForm.lead_id;
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: cardForm.title, description: cardForm.description || null, due_date: cardForm.due_date || null, labels: cardForm.labels, assignee: cardForm.assignee || null, lead_id: effectiveLeadId, color: cardForm.color }),
      });
      if (res.ok) {
        const updated = await res.json();
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, ...updated } : c) })) } : prev);
        setCardModal({ open: false, card: null, columnId: "" });
        setToast({ message: "Card diupdate", type: "success" });
      }
    } catch (e) { setToast({ message: "Gagal update card", type: "error" }); }
  }

  async function archiveCard(cardId: string, isArchived: boolean) {
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_archived: isArchived }),
      });
      if (res.ok) {
        await fetchBoard(selectedProject);
        setCardModal({ open: false, card: null, columnId: "" });
        setToast({ message: isArchived ? "Card diarsipkan" : "Card dipulihkan", type: "success" });
      }
    } catch (e) { setToast({ message: "Gagal arsipkan card", type: "error" }); }
  }

  async function archiveProject(projectId: string, isArchived: boolean) {
    try {
      const res = await apiFetch(`/api/projects/${projectId}/archive`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_archived: isArchived }),
      });
      if (res.ok) {
        await fetchOverview(showArchivedProjects);
        setToast({ message: isArchived ? "Proyek diarsipkan" : "Proyek dipulihkan", type: "success" });
      }
    } catch (e) { setToast({ message: "Gagal arsipkan proyek", type: "error" }); }
  }

  async function deleteProjectFromBoard(projectId: string, projectName: string) {
    try {
      const res = await apiFetch(`/api/projects/${projectId}`, { method: "DELETE" });
      if (res.ok) {
        setProjects(prev => prev.filter(p => p.id !== projectId));
        await fetchOverview(showArchivedProjects);
        if (selectedProject === projectId) setSelectedProject("");
        setToast({ message: `Proyek "${projectName}" dihapus`, type: "success" });
      }
    } catch (e) { setToast({ message: "Gagal hapus proyek", type: "error" }); }
  }

  async function saveEditProject() {
    if (!editProjectModal || !editProjectForm.name.trim()) return;
    setSaving(true);
    try {
      const res = await apiFetch(`/api/projects/${editProjectModal.projectId}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editProjectForm),
      });
      if (res.ok) {
        const updated = await res.json();
        setProjects(prev => prev.map(p => p.id === editProjectModal.projectId ? updated : p));
        await fetchOverview(showArchivedProjects);
        setEditProjectModal(null);
        setToast({ message: "Proyek diupdate", type: "success" });
      }
    } catch (e) { setToast({ message: "Gagal update proyek", type: "error" }); } finally { setSaving(false); }
  }

  async function deleteCard(cardId: string) {
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}`, { method: "DELETE" });
      if (res.ok) {
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).filter(c => c.id !== cardId) })) } : prev);
        setCardModal({ open: false, card: null, columnId: "" });
        setToast({ message: "Card dihapus", type: "success" });
      }
    } catch (e) { setToast({ message: "Gagal hapus card", type: "error" }); }
  }

  async function moveCard(cardId: string, toColumnId: string, toPosition?: number) {
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}/move`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ column_id: toColumnId, position: toPosition }),
      });
      if (res.ok) { if (selectedProject) fetchBoard(selectedProject); }
    } catch (e) { setToast({ message: "Gagal memindahkan card", type: "error" }); }
  }

  async function createColumn() {
    if (!columnName.trim() || !board) return;
    try {
      const res = await apiFetch(`/api/boards/${board.id}/columns`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: columnName, color: columnColor }) });
      if (res.ok) {
        const newCol = await res.json();
        setBoard(prev => prev ? { ...prev, columns: [...prev.columns, { ...newCol, cards: [] }] } : prev);
        setColumnName(""); setColumnColor("yellow");
        setColumnModal({ open: false, column: null });
        setToast({ message: "Kolom dibuat", type: "success" });
      }
    } catch (e) { setToast({ message: "Gagal membuat kolom", type: "error" }); }
  }

  async function updateColumn(columnId: string) {
    try {
      const res = await apiFetch(`/api/board-columns/${columnId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: columnName, color: columnColor }) });
      if (res.ok) {
        const updated = await res.json();
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => col.id === columnId ? { ...col, ...updated } : col) } : prev);
        setColumnModal({ open: false, column: null });
        setToast({ message: "Kolom diupdate", type: "success" });
      }
    } catch (e) { setToast({ message: "Gagal update kolom", type: "error" }); }
  }

  async function deleteColumn(columnId: string) {
    try {
      const res = await apiFetch(`/api/board-columns/${columnId}`, { method: "DELETE" });
      if (res.ok) { setBoard(prev => prev ? { ...prev, columns: prev.columns.filter(col => col.id !== columnId) } : prev); setToast({ message: "Kolom dihapus", type: "success" }); }
    } catch (e) { setToast({ message: "Gagal hapus kolom", type: "error" }); }
  }

  async function addChecklistItem(cardId: string, text: string) {
    if (!text.trim()) return;
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}/checklist`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
      if (res.ok) {
        const item = await res.json();
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, checklist: [...c.checklist, item] } : c) })) } : prev);
        setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, checklist: [...(prev.card!.checklist || []), item] } } : prev);
        refreshCardActivity(cardId);
      } else { setToast({ message: "Gagal tambah checklist", type: "error" }); }
    } catch (e) { setToast({ message: "Gagal tambah checklist", type: "error" }); }
  }

  async function toggleChecklist(cardId: string, itemId: string, isDone: boolean) {
    // Optimistic update
    setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, checklist: c.checklist.map(i => i.id === itemId ? { ...i, is_done: isDone } : i) } : c) })) } : prev);
    setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, checklist: prev.card!.checklist.map(i => i.id === itemId ? { ...i, is_done: isDone } : i) } } : prev);
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}/checklist/${itemId}?is_done=${isDone}`, { method: "PATCH" });
      if (res.ok) {
        refreshCardActivity(cardId);
      } else {
        // Revert on failure
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, checklist: c.checklist.map(i => i.id === itemId ? { ...i, is_done: !isDone } : i) } : c) })) } : prev);
        setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, checklist: prev.card!.checklist.map(i => i.id === itemId ? { ...i, is_done: !isDone } : i) } } : prev);
        setToast({ message: "Gagal update checklist", type: "error" });
      }
    } catch (e) {
      setToast({ message: "Gagal update checklist", type: "error" });
    }
  }

  async function addComment(cardId: string, content: string) {
    if (!content.trim()) return;
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}/comments`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }) });
      if (res.ok) {
        const comment = await res.json();
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, comments: [...c.comments, comment] } : c) })) } : prev);
        setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, comments: [...(prev.card!.comments || []), comment] } } : prev);
        refreshCardActivity(cardId);
      } else { setToast({ message: "Gagal tambah komentar", type: "error" }); }
    } catch (e) { setToast({ message: "Gagal tambah komentar", type: "error" }); }
  }

  async function refreshCardActivity(cardId: string) {
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}`);
      if (res.ok) {
        const updated = await res.json();
        setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, activity: updated.activity || [] } } : prev);
      }
    } catch (e) {}
  }

  function handleDragStart(card: BoardCard, fromColumn: string) { setDraggedCard({ card, fromColumn }); }
  function handleDragEnd() { setDraggedCard(null); setDragOverColumn(null); }
  function handleDragOver(e: React.DragEvent, columnId: string) { e.preventDefault(); setDragOverColumn(columnId); }
  function handleDragLeave(e: React.DragEvent) {
    if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOverColumn(null);
  }
  function handleDrop(toColumnId: string) {
    if (draggedCard && draggedCard.fromColumn !== toColumnId) moveCard(draggedCard.card.id, toColumnId);
    setDraggedCard(null); setDragOverColumn(null);
  }

  function formatDate(d: string | null) { if (!d) return ""; return new Date(d).toLocaleDateString("id-ID", { day: "numeric", month: "short" }); }
  function formatDateTime(d: string) { return new Date(d).toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); }
  function toggleLabel(label: string) { setCardForm(prev => ({ ...prev, labels: prev.labels.includes(label) ? prev.labels.filter(l => l !== label) : [...prev.labels, label] })); }

  function openNewCardModal(columnId: string) {
    setCardModal({ open: true, card: null, columnId });
    setCardForm({ title: "", description: "", due_date: "", labels: [], assignee: localStorage.getItem("kt_name") || "", lead_id: null, color: "yellow" });
  }
  async function openEditCardModal(card: BoardCard, columnId: string) {
    setCardModal({ open: true, card, columnId });
    setCardForm({ title: card.title, description: card.description || "", due_date: card.due_date || "", labels: Array.isArray(card.labels) ? card.labels : [], assignee: card.assignee || "", lead_id: card.lead_id ?? null, color: card.color || "yellow" });
    // Fetch fresh card data to get latest checklist/comments/activity
    try {
      const res = await apiFetch(`/api/board-cards/${card.id}`);
      if (res.ok) {
        const fresh = await res.json();
        setCardModal(prev => prev.card?.id === card.id ? { ...prev, card: fresh } : prev);
      }
    } catch (e) {}
  }

  if (loading) return <div className="p-6 animate-pulse space-y-4"><div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded" /><div className="h-64 bg-gray-100 dark:bg-gray-800 rounded-xl" /></div>;

  const currentProject = projects.find(p => p.id === selectedProject);
  const currentProjectLead = leads.find(l => l.id === currentProject?.lead_id);
  const currentOverview = overview.find(o => o.project_id === selectedProject);
  const boardColor = currentOverview?.color || currentProject?.color || "yellow";

  return (
    <div className="h-full flex flex-col p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          {viewMode === "board" && currentProject ? (
            <div>
              <button onClick={() => setSelectedProject("")} className="flex items-center gap-1 text-sm text-neutral-500 hover:text-amber-600 dark:hover:text-yellow-400 mb-1 transition-colors">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"/></svg>
                Semua Proyek
              </button>
              <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">{currentProject.name}</h1>
            </div>
          ) : (
            <div>
              <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Project Board</h1>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Kelola task proyek dengan kanban board</p>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          {viewMode === "overview" && (
            <label className="flex items-center gap-2 px-3 py-2 text-sm rounded-xl cursor-pointer select-none bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
              <input type="checkbox" checked={showArchivedProjects} onChange={e => setShowArchivedProjects(e.target.checked)} className="accent-amber-500 w-4 h-4" />
              Tampilkan arsip
            </label>
          )}
          {isAdmin && <button onClick={() => { setProjectModal(true); setProjectForm({ name: "", type: "FIXED", status: "ACTIVE", nominal: 0, lead_id: null, color: "yellow" }); }} className={`px-3 py-2 text-sm rounded-xl flex items-center gap-1 ${COLORS.secondary}`}>
            <Plus className="w-4 h-4" /> Proyek Baru
          </button>}
          {board && (
            <>
              <button onClick={() => setShowArchived(!showArchived)} className={`px-3 py-2 text-sm rounded-xl flex items-center gap-1 ${showArchived ? COLORS.primary : COLORS.secondary}`}>
                {showArchived ? <ArchiveRestore className="w-4 h-4" /> : <Archive className="w-4 h-4" />}
                {showArchived ? "Card Aktif" : "Card Arsip"}
              </button>
              <button onClick={() => { setColumnModal({ open: true, column: null }); setColumnName(""); setColumnColor("yellow"); }} className={`px-3 py-2 text-sm rounded-xl flex items-center gap-1 ${COLORS.primary}`}>
                <Plus className="w-4 h-4" /> Kolom
              </button>
            </>
          )}
        </div>
      </div>

      {currentProjectLead && (
        <div className="mb-4 px-3 py-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl w-fit flex items-center gap-2">
          <User className="w-4 h-4 text-amber-600 dark:text-yellow-400" />
          <span className="text-sm font-medium text-yellow-700 dark:text-yellow-300">{currentProjectLead.business_name}</span>
        </div>
      )}

      {/* Overview */}
      {viewMode === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {overview.length === 0 && (
            <div className="col-span-full bg-white dark:bg-[var(--bg-canvas)] rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center">
              <p className="text-neutral-500">Belum ada proyek dengan board.</p>
              <p className="text-xs text-neutral-400 mt-1">Klik "Proyek Baru" untuk mulai.</p>
            </div>
          )}
          {overview.map(item => (
            <BoardOverviewCard
              key={item.project_id}
              item={item}
              projects={projects}
              onSelectProject={setSelectedProject}
              onArchiveProject={archiveProject}
              onDeleteProject={deleteProjectFromBoard}
              onShowConfirm={showConfirm}
              onEditProject={p => {
                setEditProjectForm({ name: p.name, type: p.type as "FIXED"|"RETAINER", status: p.status, nominal: (p as any).nominal || 0, lead_id: p.lead_id, color: p.color || "yellow" });
                setEditProjectModal({ open: true, projectId: p.id });
              }}
            />
          ))}
        </div>
      )}

      {/* Board */}
      {viewMode === "board" && board && (
        <div className="flex-1 overflow-x-auto">
          <div className="flex gap-4 min-w-max pb-4 h-full">
            {board.columns.map(column => (
              <BoardColumnItem
                key={column.id}
                column={column}
                COLUMN_COLORS={COLUMN_COLORS}
                BOARD_TOP_BORDER={BOARD_TOP_BORDER}
                leads={leads}
                draggedCard={draggedCard}
                dragOverColumn={dragOverColumn}
                showArchived={showArchived}
                filterAssignee={filterAssignee}
                filterDue={filterDue}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
                onDragOver={setDragOverColumn}
                onDragLeave={() => setDragOverColumn(null)}
                onDrop={handleDrop}
                onOpenEditCard={openEditCardModal}
                onOpenNewCard={openNewCardModal}
                onEditColumn={col => { const c = board?.columns.find(x => x.id === col.id); setColumnModal({ open: true, column: c || { id: col.id, board_id: "", name: col.name, color: col.color, position: 0, cards: [] } }); setColumnName(col.name); setColumnColor(col.color || "yellow"); }}
                onDeleteColumn={(id, name) => showConfirm("Hapus Kolom", `Kolom "${name}" dan semua card di dalamnya akan dihapus permanen.`, () => deleteColumn(id))}
              />
            ))}
          </div>
        </div>
      )}

      {/* Card Modal */}
      <Modal open={cardModal.open} onClose={() => setCardModal({ open: false, card: null, columnId: "" })} title={cardModal.card ? "Edit Card" : "Card Baru"} size="lg">
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Judul {cardModal.card?.is_workspace_linked && <span className="ml-1 text-[10px] text-gray-400 normal-case">(read-only — diatur dari Workspace)</span>}</label>
            <input type="text" value={cardForm.title} onChange={e => setCardForm(prev => ({ ...prev, title: e.target.value }))} readOnly={cardModal.card?.is_workspace_linked} className={`w-full px-3 py-2 border-0 rounded-xl text-sm outline-none ${cardModal.card?.is_workspace_linked ? "bg-gray-50 dark:bg-gray-900 text-gray-500 cursor-not-allowed" : "bg-gray-100 dark:bg-gray-800 focus:ring-2 focus:ring-yellow-400"}`} placeholder="Judul card..." />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Deskripsi</label>
            <textarea value={cardForm.description} onChange={e => setCardForm(prev => ({ ...prev, description: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none resize-none" rows={3} placeholder="Deskripsi..." />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Assignee</label>
              <input type="text" value={cardForm.assignee} onChange={e => setCardForm(prev => ({ ...prev, assignee: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none" placeholder="Nama assignee..." />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Due Date</label>
              <input type="date" value={cardForm.due_date} onChange={e => setCardForm(prev => ({ ...prev, due_date: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">Labels</label>
            <div className="flex gap-2 flex-wrap">
              {Object.keys(LABEL_COLORS).map(label => (
                <button key={label} type="button" onClick={() => toggleLabel(label)}
                  className={`h-6 w-10 rounded-md ${LABEL_COLORS[label]} transition-all ${cardForm.labels.includes(label) ? "ring-2 ring-offset-2 ring-neutral-700 dark:ring-white" : "opacity-40 hover:opacity-70"}`} />
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">Warna Card</label>
            <div className="flex gap-2 flex-wrap">
              {Object.keys(CARD_COLORS).map(color => (
                <button key={color} type="button" title={color} onClick={() => setCardForm(prev => ({ ...prev, color }))}
                  className={`w-8 h-8 rounded-xl ${CARD_COLORS[color].bg} ${CARD_COLORS[color].accent} transition-all
                    ${cardForm.color === color ? "ring-2 ring-offset-1 ring-neutral-700 dark:ring-white scale-110" : "hover:scale-105"}`} />
              ))}
            </div>
          </div>

          {/* Client field */}
          {currentProject && (
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Client</label>
              {currentProject.lead_id ? (
                <div className="px-3 py-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl text-sm flex items-center gap-2">
                  <User className="w-4 h-4 text-amber-600" />
                  <span className="font-medium text-yellow-700 dark:text-yellow-300">{currentProjectLead?.business_name || `Lead #${currentProject.lead_id}`}</span>
                  <span className="text-neutral-400 text-xs">(dari proyek)</span>
                </div>
              ) : (
                <select value={cardForm.lead_id ?? ""} onChange={e => setCardForm(prev => ({ ...prev, lead_id: e.target.value ? Number(e.target.value) : null }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm">
                  <option value="">— Tanpa client —</option>
                  {leads.map(l => <option key={l.id} value={l.id}>{l.business_name}</option>)}
                </select>
              )}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-2 pt-2">
            <button onClick={() => cardModal.card ? updateCard(cardModal.card.id) : createCard(cardModal.columnId)} disabled={saving || !cardForm.title.trim()} className={`flex-1 px-4 py-2 text-sm rounded-xl font-medium ${COLORS.primary} disabled:opacity-50`}>
              {saving ? "Menyimpan..." : cardModal.card ? "Simpan Perubahan" : "Buat Card"}
            </button>
            {cardModal.card && (
              <>
                <button onClick={() => archiveCard(cardModal.card!.id, !cardModal.card!.is_archived)}
                  className={`px-3 py-2 text-sm rounded-xl ${cardModal.card.is_archived ? "bg-green-100 text-green-600 hover:bg-green-200" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                  title={cardModal.card.is_archived ? "Pulihkan" : "Arsipkan"}>
                  {cardModal.card.is_archived ? <ArchiveRestore className="w-4 h-4" /> : <Archive className="w-4 h-4" />}
                </button>
                <button onClick={() => showConfirm("Hapus Card", "Card ini akan dihapus permanen beserta semua checklist, komentar, dan aktivitasnya.", () => deleteCard(cardModal.card!.id))} className="px-3 py-2 text-sm rounded-xl bg-red-100 text-red-600 hover:bg-red-200" title="Hapus">
                  <Trash2 className="w-4 h-4" />
                </button>
              </>
            )}
          </div>

          {/* Checklist, Comments, Activity — only for existing cards */}
          {cardModal.card && (
            <>
              <hr className="border-gray-200 dark:border-gray-700 my-2" />
              {/* Checklist */}
              <div>
                <h4 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 flex items-center gap-2">
                  <CheckSquare className="w-4 h-4 text-amber-500" /> Checklist
                  {(cardModal.card.checklist?.length || 0) > 0 && (
                    <span className="text-xs text-neutral-400">{cardModal.card.checklist.filter(i => i.is_done).length}/{cardModal.card.checklist.length}</span>
                  )}
                </h4>
                {(cardModal.card.checklist?.length || 0) > 0 && (
                  <div className="mb-2 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div className="h-full bg-yellow-400 rounded-full transition-all" style={{ width: `${(cardModal.card.checklist.filter(i => i.is_done).length / cardModal.card.checklist.length) * 100}%` }} />
                  </div>
                )}
                <div className="space-y-1.5 mb-2">
                  {cardModal.card.checklist?.map(item => (
                    <label key={item.id} className="flex items-center gap-2 text-sm cursor-pointer group">
                      <input type="checkbox" checked={item.is_done} onChange={e => toggleChecklist(cardModal.card!.id, item.id, e.target.checked)} className="rounded accent-amber-500" />
                      <span className={`transition-all ${item.is_done ? "line-through text-neutral-400" : "text-neutral-700 dark:text-neutral-300"}`}>{item.text}</span>
                    </label>
                  ))}
                </div>
                <input type="text" placeholder="+ Tambah item checklist, Enter untuk simpan" className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
                  onKeyDown={e => { if (e.key === "Enter") { addChecklistItem(cardModal.card!.id, (e.target as HTMLInputElement).value); (e.target as HTMLInputElement).value = ""; } }} />
              </div>

              {/* Comments */}
              <div>
                <h4 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-blue-500" /> Komentar
                  {(cardModal.card.comments?.length || 0) > 0 && <span className="text-xs text-neutral-400">{cardModal.card.comments.length}</span>}
                </h4>
                <div className="space-y-2 mb-2 max-h-36 overflow-y-auto">
                  {cardModal.card.comments?.map(c => (
                    <div key={c.id} className="bg-gray-100 dark:bg-gray-800 rounded-xl p-2.5 text-sm">
                      <p className="text-neutral-800 dark:text-neutral-200">{c.content}</p>
                      <p className="text-xs text-neutral-400 mt-1">{c.author} · {formatDateTime(c.created_at)}</p>
                    </div>
                  ))}
                </div>
                <input type="text" placeholder="Tulis komentar, Enter untuk kirim" className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
                  onKeyDown={e => { if (e.key === "Enter") { addComment(cardModal.card!.id, (e.target as HTMLInputElement).value); (e.target as HTMLInputElement).value = ""; } }} />
              </div>

              {/* Activity */}
              {(cardModal.card.activity?.length || 0) > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-purple-500" /> Aktivitas
                  </h4>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {[...(cardModal.card.activity || [])].reverse().map(a => (
                      <div key={a.id} className="flex items-start gap-2 text-xs">
                        <div className="w-1.5 h-1.5 rounded-full bg-neutral-400 mt-1.5 shrink-0" />
                        <span className="font-medium text-neutral-700 dark:text-neutral-300">{a.actor}</span>
                        <span className="text-neutral-500">{a.description}</span>
                        <span className="text-neutral-400 shrink-0 ml-auto">{formatDateTime(a.created_at)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </Modal>

      {/* Column Modal */}
      <Modal open={columnModal.open} onClose={() => setColumnModal({ open: false, column: null })} title={columnModal.column ? "Edit Kolom" : "Kolom Baru"}>
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Nama Kolom</label>
            <input type="text" value={columnName} onChange={e => setColumnName(e.target.value)} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none" placeholder="e.g., In Progress" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">Warna</label>
            <div className="flex gap-2 flex-wrap">
              {Object.keys(COLUMN_COLORS).map(color => (
                <button key={color} type="button" title={color} onClick={() => setColumnColor(color)}
                  className={`w-8 h-8 rounded-xl ${COLUMN_COLORS[color].bg} border-2 transition-all ${columnColor === color ? "border-neutral-900 dark:border-white scale-110" : `${COLUMN_COLORS[color].border} hover:scale-105`}`} />
              ))}
            </div>
          </div>
          <button onClick={() => columnModal.column ? updateColumn(columnModal.column.id) : createColumn()} disabled={!columnName.trim()} className={`w-full px-4 py-2 text-sm rounded-xl font-medium ${COLORS.primary} disabled:opacity-50`}>
            {columnModal.column ? "Update Kolom" : "Buat Kolom"}
          </button>
        </div>
      </Modal>

      {/* Project Modal */}
      <Modal open={projectModal} onClose={() => setProjectModal(false)} title="Buat Proyek Baru">
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Nama Proyek</label>
            <input type="text" value={projectForm.name} onChange={e => setProjectForm(p => ({ ...p, name: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none" placeholder="Nama proyek..." />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Tipe</label>
            <select value={projectForm.type} onChange={e => setProjectForm(p => ({ ...p, type: e.target.value as "FIXED" | "RETAINER" }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm">
              <option value="FIXED">Fixed</option>
              <option value="RETAINER">Retainer</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Client (opsional)</label>
            <select value={projectForm.lead_id ?? ""} onChange={e => setProjectForm(p => ({ ...p, lead_id: e.target.value ? Number(e.target.value) : null }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm">
              <option value="">— Tanpa client —</option>
              {leads.map(l => <option key={l.id} value={l.id}>{l.business_name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">Warna Proyek</label>
            <div className="flex gap-2 flex-wrap">
              {Object.keys(COLUMN_COLORS).map(color => (
                <button key={color} type="button" title={color} onClick={() => setProjectForm(p => ({ ...p, color }))}
                  className={`w-8 h-8 rounded-xl ${COLUMN_COLORS[color].bg} border-2 transition-all ${projectForm.color === color ? "border-neutral-900 dark:border-white scale-110" : `${COLUMN_COLORS[color].border} hover:scale-105`}`} />
              ))}
            </div>
          </div>
          <button onClick={createProject} disabled={saving || !projectForm.name.trim()} className={`w-full px-4 py-2 text-sm rounded-xl font-medium ${COLORS.primary} disabled:opacity-50`}>
            {saving ? "Membuat..." : "Buat Proyek"}
          </button>
        </div>
      </Modal>

      {/* Edit Project Modal */}
      <Modal open={editProjectModal?.open || false} onClose={() => setEditProjectModal(null)} title="Edit Proyek">
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Nama Proyek</label>
            <input type="text" value={editProjectForm.name} onChange={e => setEditProjectForm(p => ({ ...p, name: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Tipe</label>
            <select value={editProjectForm.type} onChange={e => setEditProjectForm(p => ({ ...p, type: e.target.value as "FIXED"|"RETAINER" }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm">
              <option value="FIXED">Fixed</option>
              <option value="RETAINER">Retainer</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Client (opsional)</label>
            <select value={editProjectForm.lead_id ?? ""} onChange={e => setEditProjectForm(p => ({ ...p, lead_id: e.target.value ? Number(e.target.value) : null }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm">
              <option value="">— Tanpa client —</option>
              {leads.map(l => <option key={l.id} value={l.id}>{l.business_name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">Warna</label>
            <div className="flex gap-2 flex-wrap">
              {Object.keys(COLUMN_COLORS).map(color => (
                <button key={color} type="button" onClick={() => setEditProjectForm(p => ({ ...p, color }))}
                  className={`w-8 h-8 rounded-xl ${COLUMN_COLORS[color].bg} border-2 transition-all ${editProjectForm.color === color ? "border-neutral-900 dark:border-white scale-110" : `${COLUMN_COLORS[color].border} hover:scale-105`}`} />
              ))}
            </div>
          </div>
          <button onClick={saveEditProject} disabled={saving || !editProjectForm.name.trim()} className={`w-full px-4 py-2 text-sm rounded-xl font-medium ${COLORS.primary} disabled:opacity-50`}>
            {saving ? "Menyimpan..." : "Simpan Perubahan"}
          </button>
        </div>
      </Modal>

      {confirmModal && (
        <ConfirmModal
          open={confirmModal.open}
          title={confirmModal.title}
          message={confirmModal.message}
          onConfirm={confirmModal.onConfirm}
          onClose={() => setConfirmModal(null)}
        />
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
