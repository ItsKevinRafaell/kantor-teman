"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "../../lib/api";
import { Plus, Trash2, Calendar, User, MessageSquare, CheckSquare, X, Archive, ArchiveRestore, Activity } from "lucide-react";
import Toast from "../../components/Toast";

const COLORS = {
  primary: "bg-yellow-500 hover:bg-yellow-600 text-white",
  secondary: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700",
};

const COLUMN_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  yellow: { bg: "bg-yellow-50 dark:bg-yellow-900/20", border: "border-yellow-300 dark:border-yellow-700", text: "text-yellow-700 dark:text-yellow-300" },
  red: { bg: "bg-red-50 dark:bg-red-900/20", border: "border-red-300 dark:border-red-700", text: "text-red-700 dark:text-red-300" },
  orange: { bg: "bg-orange-50 dark:bg-orange-900/20", border: "border-orange-300 dark:border-orange-700", text: "text-orange-700 dark:text-orange-300" },
  green: { bg: "bg-green-50 dark:bg-green-900/20", border: "border-green-300 dark:border-green-700", text: "text-green-700 dark:text-green-300" },
  blue: { bg: "bg-blue-50 dark:bg-blue-900/20", border: "border-blue-300 dark:border-blue-700", text: "text-blue-700 dark:text-blue-300" },
  purple: { bg: "bg-purple-50 dark:bg-purple-900/20", border: "border-purple-300 dark:border-purple-700", text: "text-purple-700 dark:text-purple-300" },
  pink: { bg: "bg-pink-50 dark:bg-pink-900/20", border: "border-pink-300 dark:border-pink-700", text: "text-pink-700 dark:text-pink-300" },
  slate: { bg: "bg-slate-50 dark:bg-slate-900/20", border: "border-slate-300 dark:border-slate-600", text: "text-slate-700 dark:text-slate-300" },
};

// Card colors: tinted background only, no extra border
const CARD_COLORS: Record<string, { bg: string; accent: string; text: string }> = {
  yellow: { bg: "bg-yellow-50 dark:bg-yellow-900/25", accent: "", text: "text-yellow-700 dark:text-yellow-300" },
  red: { bg: "bg-red-50 dark:bg-red-900/25", accent: "", text: "text-red-700 dark:text-red-300" },
  orange: { bg: "bg-orange-50 dark:bg-orange-900/25", accent: "", text: "text-orange-700 dark:text-orange-300" },
  green: { bg: "bg-green-50 dark:bg-green-900/25", accent: "", text: "text-green-700 dark:text-green-300" },
  blue: { bg: "bg-blue-50 dark:bg-blue-900/25", accent: "", text: "text-blue-700 dark:text-blue-300" },
  purple: { bg: "bg-purple-50 dark:bg-purple-900/25", accent: "", text: "text-purple-700 dark:text-purple-300" },
  pink: { bg: "bg-pink-50 dark:bg-pink-900/25", accent: "", text: "text-pink-700 dark:text-pink-300" },
  slate: { bg: "bg-slate-50 dark:bg-slate-900/25", accent: "", text: "text-slate-700 dark:text-slate-300" },
};

// Board accent: thick top border for the board container
const BOARD_TOP_BORDER: Record<string, string> = {
  yellow: "border-t-4 border-yellow-400",
  red: "border-t-4 border-red-400",
  orange: "border-t-4 border-orange-400",
  green: "border-t-4 border-green-400",
  blue: "border-t-4 border-blue-400",
  purple: "border-t-4 border-purple-400",
  pink: "border-t-4 border-pink-400",
  slate: "border-t-4 border-slate-400",
};

const LABEL_COLORS: Record<string, string> = {
  red: "bg-red-500", orange: "bg-orange-500", yellow: "bg-yellow-500",
  green: "bg-green-500", blue: "bg-blue-500", purple: "bg-purple-500", pink: "bg-pink-500",
};

interface Lead { id: number; business_name: string; }
interface Project { id: string; name: string; status: string; lead_id: number | null; color?: string; }
interface BoardCard {
  id: string; column_id: string; title: string; description: string | null;
  assignee: string | null; due_date: string | null; labels: string[];
  position: number; is_archived: boolean; created_at: string; updated_at: string | null;
  lead_id?: number | null; lead?: Lead | null; color?: string;
  comments: { id: string; content: string; author: string; created_at: string }[];
  checklist: { id: string; text: string; is_done: boolean }[];
  activity: { id: string; action: string; description: string; actor: string; created_at: string }[];
}
interface BoardColumn { id: string; board_id: string; name: string; position: number; color?: string; cards: BoardCard[]; }
interface Board { id: string; project_id: string; created_at: string; color?: string; columns: BoardColumn[]; }
interface BoardOverview {
  project_id: string; project_name: string; board_id: string;
  cards_count: number; columns_count: number; client_name?: string;
  overdue_cards?: string[]; due_soon_cards?: string[];
  color?: string; project_lead_id?: number | null;
}

function Modal({ open, onClose, title, children, size = "md" }: {
  open: boolean; onClose: () => void; title: string; children: React.ReactNode; size?: "sm" | "md" | "lg"
}) {
  if (!open) return null;
  const sizeClass = size === "sm" ? "max-w-sm" : size === "lg" ? "max-w-2xl" : "max-w-lg";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
      <div
        className={`relative bg-white dark:bg-[#242423] rounded-2xl shadow-2xl ${sizeClass} w-full max-h-[90vh] overflow-y-auto`}
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-white dark:bg-[#242423] px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between rounded-t-2xl">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">{title}</h2>
          <button onClick={onClose} className="p-1 text-neutral-400 hover:text-neutral-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

export default function BoardPage() {
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

  const [filterAssignee, setFilterAssignee] = useState("");
  const [filterDue, setFilterDue] = useState("");

  useEffect(() => { fetchProjects(); fetchOverview(); fetchLeads(); }, []);

  useEffect(() => {
    if (selectedProject) { fetchBoard(selectedProject); setViewMode("board"); }
    else { setBoard(null); setViewMode("overview"); }
  }, [selectedProject]);

  async function fetchProjects() {
    try { const res = await apiFetch("/api/projects"); if (res.ok) setProjects(await res.json()); }
    catch (e) { console.error(e); }
  }
  async function fetchOverview() {
    try { const res = await apiFetch("/api/boards/overview"); if (res.ok) setOverview(await res.json()); }
    catch (e) { console.error(e); } finally { setLoading(false); }
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
      if (res.ok) { await fetchBoard(selectedProject); setToast({ message: isArchived ? "Card diarsipkan" : "Card dipulihkan", type: "success" }); }
    } catch (e) { setToast({ message: "Gagal arsipkan card", type: "error" }); }
  }

  async function deleteCard(cardId: string) {
    if (!confirm("Yakin hapus card ini?")) return;
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
    if (!confirm("Yakin hapus kolom ini beserta semua card?")) return;
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
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Project Board</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Kelola task proyek dengan kanban board</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <select value={selectedProject} onChange={e => setSelectedProject(e.target.value)} className="px-3 py-2 bg-white dark:bg-[#242423] border border-gray-200 dark:border-gray-700 rounded-lg text-sm">
            <option value="">Semua Proyek (Overview)</option>
            {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button onClick={() => { setProjectModal(true); setProjectForm({ name: "", type: "FIXED", status: "ACTIVE", nominal: 0, lead_id: null, color: "yellow" }); }} className={`px-3 py-2 text-sm rounded-lg flex items-center gap-1 ${COLORS.secondary}`}>
            <Plus className="w-4 h-4" /> Proyek Baru
          </button>
          {board && (
            <>
              <button onClick={() => setShowArchived(!showArchived)} className={`px-3 py-2 text-sm rounded-lg flex items-center gap-1 ${showArchived ? COLORS.primary : COLORS.secondary}`}>
                {showArchived ? <ArchiveRestore className="w-4 h-4" /> : <Archive className="w-4 h-4" />}
                {showArchived ? "Aktif" : "Arsip"}
              </button>
              <button onClick={() => { setColumnModal({ open: true, column: null }); setColumnName(""); setColumnColor("yellow"); }} className={`px-3 py-2 text-sm rounded-lg flex items-center gap-1 ${COLORS.primary}`}>
                <Plus className="w-4 h-4" /> Kolom
              </button>
            </>
          )}
        </div>
      </div>

      {currentProjectLead && (
        <div className="mb-4 px-3 py-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg w-fit flex items-center gap-2">
          <User className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
          <span className="text-sm font-medium text-yellow-700 dark:text-yellow-300">{currentProjectLead.business_name}</span>
        </div>
      )}

      {/* Overview */}
      {viewMode === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {overview.length === 0 && (
            <div className="col-span-full bg-white dark:bg-[#242423] rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center">
              <p className="text-neutral-500">Belum ada proyek dengan board.</p>
              <p className="text-xs text-neutral-400 mt-1">Klik "Proyek Baru" untuk mulai.</p>
            </div>
          )}
          {overview.map(item => {
            const itemColor = COLUMN_COLORS[item.color || "yellow"] || COLUMN_COLORS.yellow;
            return (
              <div key={item.project_id} onClick={() => setSelectedProject(item.project_id)}
                className={`rounded-xl border p-4 cursor-pointer transition-all hover:shadow-md ${itemColor.bg} ${itemColor.border}`}>
                {/* Header row */}
                <div className="flex items-start justify-between gap-2 mb-3">
                  <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 leading-tight">{item.project_name}</h3>
                </div>

                {/* Client name */}
                {item.client_name && (
                  <p className="text-xs font-medium text-yellow-600 dark:text-yellow-400 mb-2 flex items-center gap-1">
                    <User className="w-3 h-3" /> {item.client_name}
                  </p>
                )}

                {/* Stats */}
                <div className="flex items-center gap-3 text-sm text-neutral-500 mb-2">
                  <span>{item.cards_count} card</span>
                  <span>{item.columns_count} kolom</span>
                </div>

                {/* Badges */}
                {((item.overdue_cards?.length || 0) > 0 || (item.due_soon_cards?.length || 0) > 0) && (
                  <div className="flex gap-1 flex-wrap">
                    {(item.overdue_cards?.length || 0) > 0 && (
                      <span className="text-xs bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400 px-2 py-0.5 rounded-full">{item.overdue_cards?.length} overdue</span>
                    )}
                    {(item.due_soon_cards?.length || 0) > 0 && (
                      <span className="text-xs bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-full">{item.due_soon_cards?.length} due soon</span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Board */}
      {viewMode === "board" && board && (
        <div className="flex-1 overflow-x-auto">
          <div className="flex gap-4 min-w-max pb-4 h-full">
            {board.columns.map(column => {
              const colColor = COLUMN_COLORS[column.color || "yellow"] || COLUMN_COLORS.yellow;
              const isDropTarget = dragOverColumn === column.id && draggedCard !== null;
              let cards = Array.isArray(column.cards) ? column.cards : [];
              cards = cards.filter(c => showArchived ? c.is_archived : !c.is_archived);
              if (filterAssignee) cards = cards.filter(c => c.assignee === filterAssignee);
              if (filterDue === "overdue") cards = cards.filter(c => c.due_date && new Date(c.due_date) < new Date());
              if (filterDue === "soon") cards = cards.filter(c => c.due_date && new Date(c.due_date) <= new Date(Date.now() + 3 * 24 * 60 * 60 * 1000));

              const colTopBorder = BOARD_TOP_BORDER[column.color || "yellow"] || BOARD_TOP_BORDER.yellow;
              return (
                <div key={column.id}
                  className={`w-72 shrink-0 rounded-xl flex flex-col transition-all ${colColor.bg} ${colTopBorder} ${isDropTarget ? `ring-2 ring-yellow-400 ring-inset shadow-lg` : ""}`}
                  onDragOver={e => handleDragOver(e, column.id)}
                  onDragLeave={handleDragLeave}
                  onDrop={() => handleDrop(column.id)}
                >
                  <div className={`p-3 border-b ${colColor.border} flex items-center justify-between`}>
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${COLUMN_COLORS[column.color || "yellow"].border.replace("border-", "bg-").split(" ")[0]}`} />
                      <h3 className={`font-semibold text-sm ${colColor.text}`}>{column.name}</h3>
                      <span className="text-xs text-neutral-400 bg-white/60 dark:bg-black/20 px-1.5 py-0.5 rounded-full">{cards.length}</span>
                    </div>
                    <div className="flex items-center gap-0.5">
                      <button onClick={() => { setColumnModal({ open: true, column }); setColumnName(column.name); setColumnColor(column.color || "yellow"); }} className="p-1 text-neutral-400 hover:text-yellow-500 rounded text-xs">Edit</button>
                      <button onClick={() => deleteColumn(column.id)} className="p-1 text-neutral-400 hover:text-red-500 rounded"><Trash2 className="w-3.5 h-3.5" /></button>
                    </div>
                  </div>

                  <div className={`flex-1 overflow-y-auto p-2 space-y-2 min-h-[80px] transition-colors ${isDropTarget ? "bg-yellow-50/50 dark:bg-yellow-900/10" : ""}`}>
                    {cards.map(card => {
                      const cc = CARD_COLORS[card.color || "yellow"] || CARD_COLORS.yellow;
                      const isDragging = draggedCard?.card.id === card.id;
                      return (
                        <div key={card.id} draggable
                          onDragStart={() => handleDragStart(card, column.id)}
                          onDragEnd={handleDragEnd}
                          onClick={() => openEditCardModal(card, column.id)}
                          className={`rounded-lg p-3 shadow-sm cursor-pointer select-none transition-all duration-150
                            ${cc.bg} ${cc.accent}
                            ${card.is_archived ? "opacity-50" : ""}
                            ${isDragging ? "opacity-40 scale-95 rotate-1 shadow-xl" : "hover:shadow-md hover:-translate-y-0.5"}`}
                        >
                          {Array.isArray(card.labels) && card.labels.length > 0 && (
                            <div className="flex gap-1 mb-2">
                              {card.labels.map(label => <span key={label} className={`h-1.5 w-8 rounded-full ${LABEL_COLORS[label]}`} />)}
                            </div>
                          )}
                          <h4 className="font-medium text-neutral-800 dark:text-neutral-200 text-sm leading-snug">{card.title}</h4>
                          {(card.lead?.business_name || leads.find(l => l.id === card.lead_id)?.business_name) && (
                            <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                              {card.lead?.business_name || leads.find(l => l.id === card.lead_id)?.business_name}
                            </p>
                          )}
                          <div className="flex items-center gap-2 mt-2 flex-wrap">
                            {card.due_date && (
                              <span className={`flex items-center gap-1 text-xs px-1.5 py-0.5 rounded ${new Date(card.due_date) < new Date() ? "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400" : "text-neutral-500"}`}>
                                <Calendar className="w-3 h-3" />{formatDate(card.due_date)}
                              </span>
                            )}
                            {card.assignee && <span className="flex items-center gap-1 text-xs text-neutral-500"><User className="w-3 h-3" />{card.assignee}</span>}
                            {(card.comments?.length || 0) > 0 && <span className="flex items-center gap-1 text-xs text-neutral-500"><MessageSquare className="w-3 h-3" />{card.comments.length}</span>}
                            {(card.checklist?.length || 0) > 0 && (
                              <span className="flex items-center gap-1 text-xs text-neutral-500">
                                <CheckSquare className="w-3 h-3" />
                                {card.checklist.filter(c => c.is_done).length}/{card.checklist.length}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}

                    {/* Drop indicator */}
                    {isDropTarget && (
                      <div className="h-12 rounded-lg border-2 border-dashed border-yellow-400 bg-yellow-50/50 dark:bg-yellow-900/10 flex items-center justify-center">
                        <span className="text-xs text-yellow-500">Lepas di sini</span>
                      </div>
                    )}

                    {!showArchived && (
                      <button onClick={() => openNewCardModal(column.id)}
                        className="w-full p-2 text-sm text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-white/60 dark:hover:bg-black/20 rounded-lg flex items-center justify-center gap-1 transition-colors">
                        <Plus className="w-4 h-4" /> Tambah Card
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Card Modal */}
      <Modal open={cardModal.open} onClose={() => setCardModal({ open: false, card: null, columnId: "" })} title={cardModal.card ? "Edit Card" : "Card Baru"} size="lg">
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Judul</label>
            <input type="text" value={cardForm.title} onChange={e => setCardForm(prev => ({ ...prev, title: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" placeholder="Judul card..." />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Deskripsi</label>
            <textarea value={cardForm.description} onChange={e => setCardForm(prev => ({ ...prev, description: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none resize-none" rows={3} placeholder="Deskripsi..." />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Assignee</label>
              <input type="text" value={cardForm.assignee} onChange={e => setCardForm(prev => ({ ...prev, assignee: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" placeholder="Nama assignee..." />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Due Date</label>
              <input type="date" value={cardForm.due_date} onChange={e => setCardForm(prev => ({ ...prev, due_date: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
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
                  className={`w-8 h-8 rounded-lg ${CARD_COLORS[color].bg} ${CARD_COLORS[color].accent} transition-all
                    ${cardForm.color === color ? "ring-2 ring-offset-1 ring-neutral-700 dark:ring-white scale-110" : "hover:scale-105"}`} />
              ))}
            </div>
          </div>

          {/* Client field */}
          {currentProject && (
            <div>
              <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Client</label>
              {currentProject.lead_id ? (
                <div className="px-3 py-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-sm flex items-center gap-2">
                  <User className="w-4 h-4 text-yellow-600" />
                  <span className="font-medium text-yellow-700 dark:text-yellow-300">{currentProjectLead?.business_name || `Lead #${currentProject.lead_id}`}</span>
                  <span className="text-neutral-400 text-xs">(dari proyek)</span>
                </div>
              ) : (
                <select value={cardForm.lead_id ?? ""} onChange={e => setCardForm(prev => ({ ...prev, lead_id: e.target.value ? Number(e.target.value) : null }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm">
                  <option value="">— Tanpa client —</option>
                  {leads.map(l => <option key={l.id} value={l.id}>{l.business_name}</option>)}
                </select>
              )}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-2 pt-2">
            <button onClick={() => cardModal.card ? updateCard(cardModal.card.id) : createCard(cardModal.columnId)} disabled={saving || !cardForm.title.trim()} className={`flex-1 px-4 py-2 text-sm rounded-lg font-medium ${COLORS.primary} disabled:opacity-50`}>
              {saving ? "Menyimpan..." : cardModal.card ? "Simpan Perubahan" : "Buat Card"}
            </button>
            {cardModal.card && (
              <>
                <button onClick={() => archiveCard(cardModal.card!.id, !cardModal.card!.is_archived)}
                  className={`px-3 py-2 text-sm rounded-lg ${cardModal.card.is_archived ? "bg-green-100 text-green-600 hover:bg-green-200" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                  title={cardModal.card.is_archived ? "Pulihkan" : "Arsipkan"}>
                  {cardModal.card.is_archived ? <ArchiveRestore className="w-4 h-4" /> : <Archive className="w-4 h-4" />}
                </button>
                <button onClick={() => deleteCard(cardModal.card!.id)} className="px-3 py-2 text-sm rounded-lg bg-red-100 text-red-600 hover:bg-red-200" title="Hapus">
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
                  <CheckSquare className="w-4 h-4 text-yellow-500" /> Checklist
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
                      <input type="checkbox" checked={item.is_done} onChange={e => toggleChecklist(cardModal.card!.id, item.id, e.target.checked)} className="rounded accent-yellow-500" />
                      <span className={`transition-all ${item.is_done ? "line-through text-neutral-400" : "text-neutral-700 dark:text-neutral-300"}`}>{item.text}</span>
                    </label>
                  ))}
                </div>
                <input type="text" placeholder="+ Tambah item checklist, Enter untuk simpan" className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
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
                    <div key={c.id} className="bg-gray-100 dark:bg-gray-800 rounded-lg p-2.5 text-sm">
                      <p className="text-neutral-800 dark:text-neutral-200">{c.content}</p>
                      <p className="text-xs text-neutral-400 mt-1">{c.author} · {formatDateTime(c.created_at)}</p>
                    </div>
                  ))}
                </div>
                <input type="text" placeholder="Tulis komentar, Enter untuk kirim" className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
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
            <input type="text" value={columnName} onChange={e => setColumnName(e.target.value)} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" placeholder="e.g., In Progress" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">Warna</label>
            <div className="flex gap-2 flex-wrap">
              {Object.keys(COLUMN_COLORS).map(color => (
                <button key={color} type="button" title={color} onClick={() => setColumnColor(color)}
                  className={`w-8 h-8 rounded-lg ${COLUMN_COLORS[color].bg} border-2 transition-all ${columnColor === color ? "border-neutral-900 dark:border-white scale-110" : `${COLUMN_COLORS[color].border} hover:scale-105`}`} />
              ))}
            </div>
          </div>
          <button onClick={() => columnModal.column ? updateColumn(columnModal.column.id) : createColumn()} disabled={!columnName.trim()} className={`w-full px-4 py-2 text-sm rounded-lg font-medium ${COLORS.primary} disabled:opacity-50`}>
            {columnModal.column ? "Update Kolom" : "Buat Kolom"}
          </button>
        </div>
      </Modal>

      {/* Project Modal */}
      <Modal open={projectModal} onClose={() => setProjectModal(false)} title="Buat Proyek Baru">
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Nama Proyek</label>
            <input type="text" value={projectForm.name} onChange={e => setProjectForm(p => ({ ...p, name: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" placeholder="Nama proyek..." />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Tipe</label>
            <select value={projectForm.type} onChange={e => setProjectForm(p => ({ ...p, type: e.target.value as "FIXED" | "RETAINER" }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm">
              <option value="FIXED">Fixed</option>
              <option value="RETAINER">Retainer</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Client (opsional)</label>
            <select value={projectForm.lead_id ?? ""} onChange={e => setProjectForm(p => ({ ...p, lead_id: e.target.value ? Number(e.target.value) : null }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm">
              <option value="">— Tanpa client —</option>
              {leads.map(l => <option key={l.id} value={l.id}>{l.business_name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">Warna Proyek</label>
            <div className="flex gap-2 flex-wrap">
              {Object.keys(COLUMN_COLORS).map(color => (
                <button key={color} type="button" title={color} onClick={() => setProjectForm(p => ({ ...p, color }))}
                  className={`w-8 h-8 rounded-lg ${COLUMN_COLORS[color].bg} border-2 transition-all ${projectForm.color === color ? "border-neutral-900 dark:border-white scale-110" : `${COLUMN_COLORS[color].border} hover:scale-105`}`} />
              ))}
            </div>
          </div>
          <button onClick={createProject} disabled={saving || !projectForm.name.trim()} className={`w-full px-4 py-2 text-sm rounded-lg font-medium ${COLORS.primary} disabled:opacity-50`}>
            {saving ? "Membuat..." : "Buat Proyek"}
          </button>
        </div>
      </Modal>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
