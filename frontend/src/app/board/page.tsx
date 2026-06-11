"use client";
import { useState, useEffect, useRef } from "react";
import { apiFetch } from "../../lib/api";
import { Search, User } from "lucide-react";
import type { DragEvent } from "react";
import Toast from "../../components/Toast";
import ConfirmModal from "../../components/ConfirmModal";
import { useAuth } from "../../contexts/AuthContext";
import { BoardColumnItem } from "../../components/board/BoardColumn";
import { BoardOverviewCard } from "../../components/board/BoardOverview";
import BoardHeader from "../../components/board/BoardHeader";
import { ColumnModal, ProjectModal, EditProjectModal } from "../../components/board/BoardModals";
import { CardModal } from "../../components/board/CardModal";
import { COLUMN_COLORS, BOARD_TOP_BORDER } from "../../components/board/types";
import type { Lead, Project, BoardCard, BoardColumn, Board, BoardOverview, BoardUser } from "../../components/board/types";

export default function BoardPage() {
  const { isAdmin } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [users, setUsers] = useState<BoardUser[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [board, setBoard] = useState<Board | null>(null);
  const [overview, setOverview] = useState<BoardOverview[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"overview" | "board">("overview");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const [cardModal, setCardModal] = useState<{ open: boolean; card: BoardCard | null; columnId: string }>({ open: false, card: null, columnId: "" });
  const [cardForm, setCardForm] = useState({ title: "", description: "", due_date: "", labels: [] as string[], assignee: "", lead_id: null as number | null, color: "gray" });
  const [saving, setSaving] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterAssignee, setFilterAssignee] = useState("");
  const [filterDue, setFilterDue] = useState("");

  const [columnModal, setColumnModal] = useState<{ open: boolean; column: BoardColumn | null }>({ open: false, column: null });
  const [columnName, setColumnName] = useState("");
  const [columnColor, setColumnColor] = useState("gray");

  const [projectModal, setProjectModal] = useState(false);
  const [projectForm, setProjectForm] = useState({ name: "", type: "FIXED" as "FIXED" | "RETAINER", status: "ACTIVE", nominal: 0, lead_id: null as number | null, color: "gray" });

  const [draggedCard, setDraggedCard] = useState<{ card: BoardCard; fromColumn: string } | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
  const draggedCardRef = useRef<{ card: BoardCard; fromColumn: string } | null>(null);

  const [confirmModal, setConfirmModal] = useState<{ open: boolean; title: string; message: string; onConfirm: () => void } | null>(null);
  function showConfirm(title: string, message: string, onConfirm: () => void) {
    setConfirmModal({ open: true, title, message, onConfirm });
  }

  const [showArchivedProjects, setShowArchivedProjects] = useState(false);
  const [editProjectModal, setEditProjectModal] = useState<{ open: boolean; projectId: string } | null>(null);
  const [editProjectForm, setEditProjectForm] = useState({ name: "", type: "FIXED" as "FIXED" | "RETAINER", status: "ACTIVE", nominal: 0, lead_id: null as number | null, color: "gray" });

  // Data fetching
  async function fetchProjects() { try { const r = await apiFetch("/api/projects"); if (r.ok) setProjects(await r.json()); } catch {} }
  async function fetchOverview(archived = false) { try { const r = await apiFetch(`/api/boards/overview?show_archived=${archived}`); if (r.ok) setOverview(await r.json()); } catch {} finally { setLoading(false); } }
  async function fetchLeads() { try { const r = await apiFetch("/api/leads"); if (r.ok) setLeads(await r.json()); } catch {} }
  async function fetchUsers() { try { const r = await apiFetch("/api/users"); if (r.ok) setUsers(await r.json()); } catch {} }
  async function fetchBoard(projectId: string, includeArchived = showArchived) {
    try {
      const suffix = includeArchived ? "?include_archived=true" : "";
      const r = await apiFetch(`/api/projects/${projectId}/board${suffix}`);
      if (r.ok) setBoard(await r.json());
    } catch {}
  }

  useEffect(() => { fetchProjects(); fetchOverview(false); fetchLeads(); fetchUsers(); }, []);
  useEffect(() => { fetchOverview(showArchivedProjects); }, [showArchivedProjects]);
  useEffect(() => { if (selectedProject) { fetchBoard(selectedProject, showArchived); setViewMode("board"); } else { setBoard(null); setViewMode("overview"); } }, [selectedProject, showArchived]);

  // Project CRUD
  async function createProject() {
    if (!projectForm.name.trim()) return;
    setSaving(true);
    try {
      const res = await apiFetch("/api/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: projectForm.name, type: projectForm.type, status: projectForm.status, nominal: projectForm.nominal, lead_id: projectForm.lead_id, color: projectForm.color }) });
      if (res.ok) { const newProject = await res.json(); setProjects(prev => [...prev, newProject]); setProjectModal(false); await fetchOverview(); setSelectedProject(newProject.id); setToast({ message: "Proyek dibuat", type: "success" }); }
      else { const err = await res.json().catch(() => ({})); setToast({ message: err.detail || "Gagal buat proyek", type: "error" }); }
    } catch { setToast({ message: "Gagal buat proyek", type: "error" }); } finally { setSaving(false); }
  }

  async function deleteProjectFromBoard(projectId: string, projectName: string) {
    try { const res = await apiFetch(`/api/projects/${projectId}`, { method: "DELETE" }); if (res.ok) { setProjects(prev => prev.filter(p => p.id !== projectId)); await fetchOverview(showArchivedProjects); if (selectedProject === projectId) setSelectedProject(""); setToast({ message: `Proyek "${projectName}" dihapus`, type: "success" }); } }
    catch { setToast({ message: "Gagal hapus proyek", type: "error" }); }
  }

  async function saveEditProject() {
    if (!editProjectModal || !editProjectForm.name.trim()) return;
    setSaving(true);
    try { const res = await apiFetch(`/api/projects/${editProjectModal.projectId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(editProjectForm) }); if (res.ok) { const updated = await res.json(); setProjects(prev => prev.map(p => p.id === editProjectModal.projectId ? updated : p)); await fetchOverview(showArchivedProjects); setEditProjectModal(null); setToast({ message: "Proyek diupdate", type: "success" }); } }
    catch { setToast({ message: "Gagal update proyek", type: "error" }); } finally { setSaving(false); }
  }

  // Card CRUD
  async function createCard(columnId: string) {
    if (!cardForm.title.trim()) return;
    setSaving(true);
    const effectiveLeadId = currentProject?.lead_id ?? cardForm.lead_id;
    try {
      const res = await apiFetch(`/api/board-columns/${columnId}/cards`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: cardForm.title, description: cardForm.description || null, due_date: cardForm.due_date || null, labels: cardForm.labels, assignee: cardForm.assignee || undefined, lead_id: effectiveLeadId, color: cardForm.color }) });
      if (res.ok) { const newCard = await res.json(); setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => col.id === columnId ? { ...col, cards: [...(col.cards || []), newCard] } : col) } : prev); setCardForm({ title: "", description: "", due_date: "", labels: [], assignee: "", lead_id: null, color: "gray" }); setCardModal({ open: false, card: null, columnId: "" }); setToast({ message: "Card dibuat", type: "success" }); }
    } catch { setToast({ message: "Gagal membuat card", type: "error" }); } finally { setSaving(false); }
  }

  async function updateCard(cardId: string) {
    const effectiveLeadId = currentProject?.lead_id ?? cardForm.lead_id;
    try { const res = await apiFetch(`/api/board-cards/${cardId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: cardForm.title, description: cardForm.description || null, due_date: cardForm.due_date || null, labels: cardForm.labels, assignee: cardForm.assignee || null, lead_id: effectiveLeadId, color: cardForm.color }) }); if (res.ok) { const updated = await res.json(); setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, ...updated } : c) })) } : prev); setCardModal({ open: false, card: null, columnId: "" }); setToast({ message: "Card diupdate", type: "success" }); } }
    catch { setToast({ message: "Gagal update card", type: "error" }); }
  }

  async function archiveCard(cardId: string, isArchived: boolean) {
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_archived: isArchived }) });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setToast({ message: err.detail || "Gagal arsipkan card", type: "error" });
        return;
      }
      const updated = await res.json();
      setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, ...updated } : c) })) } : prev);
      await fetchBoard(selectedProject, showArchived);
      setCardModal({ open: false, card: null, columnId: "" });
      setToast({ message: isArchived ? "Card diarsipkan" : "Card dipulihkan", type: "success" });
    }
    catch { setToast({ message: "Gagal arsipkan card", type: "error" }); }
  }

  async function deleteCard(cardId: string) {
    try { const res = await apiFetch(`/api/board-cards/${cardId}`, { method: "DELETE" }); if (res.ok) { setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).filter(c => c.id !== cardId) })) } : prev); setCardModal({ open: false, card: null, columnId: "" }); setToast({ message: "Card dihapus", type: "success" }); } else { const err = await res.json().catch(() => ({})); setToast({ message: err.detail || "Gagal hapus card", type: "error" }); } }
    catch { setToast({ message: "Gagal hapus card", type: "error" }); }
  }

  async function moveCard(cardId: string, toColumnId: string, toPosition?: number) {
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}/move`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ column_id: toColumnId, position: toPosition }) });
      if (res.ok) {
        if (selectedProject) fetchBoard(selectedProject, showArchived);
        return;
      }
      const err = await res.json().catch(() => ({}));
      setToast({ message: err.detail || "Gagal memindahkan card", type: "error" });
      if (selectedProject) fetchBoard(selectedProject, showArchived);
    }
    catch {
      setToast({ message: "Gagal memindahkan card", type: "error" });
      if (selectedProject) fetchBoard(selectedProject, showArchived);
    }
  }

  // Column CRUD
  async function createColumn() {
    if (!columnName.trim() || !board) return;
    try { const res = await apiFetch(`/api/boards/${board.id}/columns`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: columnName, color: "gray" }) }); if (res.ok) { const newCol = await res.json(); setBoard(prev => prev ? { ...prev, columns: [...prev.columns, { ...newCol, cards: [] }] } : prev); setColumnName(""); setColumnColor("gray"); setColumnModal({ open: false, column: null }); setToast({ message: "Kolom dibuat", type: "success" }); } }
    catch { setToast({ message: "Gagal membuat kolom", type: "error" }); }
  }

  async function updateColumn(columnId: string) {
    try { const res = await apiFetch(`/api/board-columns/${columnId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: columnName, color: "gray" }) }); if (res.ok) { const updated = await res.json(); setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => col.id === columnId ? { ...col, ...updated } : col) } : prev); setColumnModal({ open: false, column: null }); setToast({ message: "Kolom diupdate", type: "success" }); } }
    catch { setToast({ message: "Gagal update kolom", type: "error" }); }
  }

  async function deleteColumn(columnId: string) {
    try { const res = await apiFetch(`/api/board-columns/${columnId}`, { method: "DELETE" }); if (res.ok) { setBoard(prev => prev ? { ...prev, columns: prev.columns.filter(col => col.id !== columnId) } : prev); setToast({ message: "Kolom dihapus", type: "success" }); } }
    catch { setToast({ message: "Gagal hapus kolom", type: "error" }); }
  }

  // Checklist & Comments
  async function addChecklistItem(cardId: string, text: string) {
    if (!text.trim()) return;
    try { const res = await apiFetch(`/api/board-cards/${cardId}/checklist`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) }); if (res.ok) { const item = await res.json(); setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, checklist: [item, ...(c.checklist || [])] } : c) })) } : prev); setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, checklist: [item, ...(prev.card!.checklist || [])] } } : prev); refreshCardActivity(cardId); } else { setToast({ message: "Gagal tambah checklist", type: "error" }); } }
    catch { setToast({ message: "Gagal tambah checklist", type: "error" }); }
  }

  async function toggleChecklist(cardId: string, itemId: string, isDone: boolean) {
    setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, checklist: c.checklist.map(i => i.id === itemId ? { ...i, is_done: isDone } : i) } : c) })) } : prev);
    setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, checklist: prev.card!.checklist.map(i => i.id === itemId ? { ...i, is_done: isDone } : i) } } : prev);
    try { const res = await apiFetch(`/api/board-cards/${cardId}/checklist/${itemId}?is_done=${isDone}`, { method: "PATCH" }); if (!res.ok) { setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, checklist: c.checklist.map(i => i.id === itemId ? { ...i, is_done: !isDone } : i) } : c) })) } : prev); setToast({ message: "Gagal update checklist", type: "error" }); } else { refreshCardActivity(cardId); } }
    catch { setToast({ message: "Gagal update checklist", type: "error" }); }
  }

  async function addComment(cardId: string, content: string) {
    if (!content.trim()) return;
    try { const res = await apiFetch(`/api/board-cards/${cardId}/comments`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }) }); if (res.ok) { const comment = await res.json(); setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, comments: [comment, ...(c.comments || [])] } : c) })) } : prev); setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, comments: [comment, ...(prev.card!.comments || [])] } } : prev); refreshCardActivity(cardId); } else { setToast({ message: "Gagal tambah komentar", type: "error" }); } }
    catch { setToast({ message: "Gagal tambah komentar", type: "error" }); }
  }

  async function uploadCardAttachment(cardId: string, file: File) {
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/board-cards/${cardId}/attachments`, {
        method: "POST",
        body: form,
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setToast({ message: err.detail || "Gagal upload file", type: "error" });
        return;
      }
      const attachment = await res.json();
      setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, attachments: [attachment, ...(c.attachments || [])] } : c) })) } : prev);
      setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, attachments: [attachment, ...(prev.card!.attachments || [])] } } : prev);
      refreshCardActivity(cardId);
      setToast({ message: "File ditambahkan", type: "success" });
    } catch {
      setToast({ message: "Gagal upload file", type: "error" });
    }
  }

  async function refreshCardActivity(cardId: string) {
    try { const res = await apiFetch(`/api/board-cards/${cardId}`); if (res.ok) { const updated = await res.json(); setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, activity: updated.activity || [] } } : prev); setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, activity: updated.activity || c.activity || [] } : c) })) } : prev); } } catch {}
  }

  // Drag & Drop
  function handleDragStart(card: BoardCard, fromColumn: string) {
    const payload = { card, fromColumn };
    draggedCardRef.current = payload;
    setDraggedCard(payload);
  }
  function handleDragEnd() {
    draggedCardRef.current = null;
    setDraggedCard(null);
    setDragOverColumn(null);
  }
  function handleDrop(toColumnId: string, event?: DragEvent<HTMLDivElement>) {
    const transferJson = event?.dataTransfer.getData("application/json");
    const transferCardId = event?.dataTransfer.getData("text/plain");
    let activeDrag = draggedCardRef.current || draggedCard;
    if (!activeDrag && (transferJson || transferCardId) && board) {
      let cardId = transferCardId;
      let fromColumn = "";
      if (transferJson) {
        try {
          const parsed = JSON.parse(transferJson);
          cardId = parsed.cardId || cardId;
          fromColumn = parsed.fromColumn || "";
        } catch {}
      }
      for (const column of board.columns) {
        const found = (column.cards || []).find(c => c.id === cardId);
        if (found) {
          activeDrag = { card: found, fromColumn: fromColumn || column.id };
          break;
        }
      }
    }
    if (activeDrag && activeDrag.fromColumn !== toColumnId) {
      setBoard(prev => prev ? {
        ...prev,
        columns: prev.columns.map(col => {
          if (col.id === activeDrag!.fromColumn) {
            return { ...col, cards: (col.cards || []).filter(c => c.id !== activeDrag!.card.id) };
          }
          if (col.id === toColumnId) {
            return { ...col, cards: [...(col.cards || []), { ...activeDrag!.card, column_id: toColumnId }] };
          }
          return col;
        }),
      } : prev);
      moveCard(activeDrag.card.id, toColumnId);
    }
    handleDragEnd();
  }
  function formatDateTime(d: string) { return new Date(d).toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); }

  // Card modal helpers
  function openNewCardModal(columnId: string) {
    setCardModal({ open: true, card: null, columnId });
    const nonAdmin = users.filter(u => u.role !== "admin");
    const fallback = nonAdmin[0]?.name || users.find(u => u.role === "admin")?.name || localStorage.getItem("kt_name") || "";
    setCardForm({ title: "", description: "", due_date: "", labels: [], assignee: fallback, lead_id: null, color: "gray" });
  }
  async function openEditCardModal(card: BoardCard, columnId: string) {
    setCardModal({ open: true, card, columnId });
    setCardForm({ title: card.title, description: card.description || "", due_date: card.due_date || "", labels: Array.isArray(card.labels) ? card.labels : [], assignee: card.assignee || "", lead_id: card.lead_id ?? null, color: "gray" });
    try { const res = await apiFetch(`/api/board-cards/${card.id}`); if (res.ok) { const fresh = await res.json(); setCardModal(prev => prev.card?.id === card.id ? { ...prev, card: fresh } : prev); } } catch {}
  }

  if (loading) return <div className="p-6 animate-pulse space-y-4"><div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded" /><div className="h-64 bg-gray-100 dark:bg-gray-800 rounded-xl" /></div>;

  const currentProject = projects.find(p => p.id === selectedProject);
  const currentProjectLead = leads.find(l => l.id === currentProject?.lead_id);
  const normalizedSearch = searchQuery.trim().toLowerCase();
  const filteredOverview = overview.filter(item => {
    if (!normalizedSearch) return true;
    return [item.project_name, item.client_name].some(v => (v || "").toLowerCase().includes(normalizedSearch));
  });

  return (
    <div className="h-full flex flex-col p-6">
      <BoardHeader
        viewMode={viewMode} currentProject={currentProject} isAdmin={isAdmin}
        showArchivedProjects={showArchivedProjects} setShowArchivedProjects={setShowArchivedProjects}
        showArchived={showArchived} setShowArchived={setShowArchived}
        board={board}
        onNewProject={() => { setProjectModal(true); setProjectForm({ name: "", type: "FIXED", status: "ACTIVE", nominal: 0, lead_id: null, color: "gray" }); }}
        onNewColumn={() => { setColumnModal({ open: true, column: null }); setColumnName(""); setColumnColor("gray"); }}
        onBackToOverview={() => setSelectedProject("")}
      />

      {currentProjectLead && (
        <div className="mb-4 px-3 py-2 bg-neutral-50 dark:bg-neutral-900/20 rounded-xl w-fit flex items-center gap-2">
          <User className="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
          <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">{currentProjectLead.business_name}</span>
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <label className="relative min-w-[240px] flex-1 max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <input
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder={viewMode === "overview" ? "Cari nama proyek atau klien..." : "Cari card, proyek, klien, atau PIC..."}
            className="w-full rounded-xl border border-amber-100 bg-amber-50/40 py-2 pl-9 pr-3 text-sm outline-none focus:border-amber-300 focus:ring-2 focus:ring-amber-200 dark:border-amber-900/50 dark:bg-amber-950/10 dark:text-neutral-100"
          />
        </label>
        {viewMode === "board" && (
          <>
            <select
              value={filterAssignee}
              onChange={e => setFilterAssignee(e.target.value)}
              className="rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
            >
              <option value="">Semua PIC</option>
              {users.map(u => <option key={u.id} value={u.name}>{u.name}</option>)}
            </select>
            <select
              value={filterDue}
              onChange={e => setFilterDue(e.target.value)}
              className="rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
            >
              <option value="">Semua deadline</option>
              <option value="soon">Mendekati deadline</option>
              <option value="overdue">Terlambat</option>
            </select>
          </>
        )}
      </div>

      {/* Overview */}
      {viewMode === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredOverview.length === 0 && (
            <div className="col-span-full bg-white dark:bg-[var(--bg-canvas)] rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center">
              <p className="text-neutral-500">{overview.length === 0 ? "Belum ada proyek dengan board." : "Tidak ada proyek yang cocok."}</p>
              <p className="text-xs text-neutral-400 mt-1">{overview.length === 0 ? "Klik \"Proyek Baru\" untuk mulai." : "Coba ubah kata pencarian."}</p>
            </div>
          )}
          {filteredOverview.map(item => (
            <BoardOverviewCard
              key={item.project_id} item={item} projects={projects}
              onSelectProject={setSelectedProject}
              onArchiveProject={async (id: string, arch: boolean) => { try { await apiFetch(`/api/projects/${id}/archive`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_archived: arch }) }); if (arch) setToast({ message: "Proyek diarsipkan", type: "success" }); else setToast({ message: "Proyek dipulihkan", type: "success" }); await fetchOverview(showArchivedProjects); } catch { setToast({ message: "Gagal arsipkan proyek", type: "error" }); } }}
              onDeleteProject={deleteProjectFromBoard}
              onShowConfirm={showConfirm}
              onEditProject={p => { setEditProjectForm({ name: p.name, type: p.type as "FIXED"|"RETAINER", status: p.status, nominal: (p as any).nominal || 0, lead_id: p.lead_id, color: p.color || "gray" }); setEditProjectModal({ open: true, projectId: p.id }); }}
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
                key={column.id} column={column}
                COLUMN_COLORS={COLUMN_COLORS}
                BOARD_TOP_BORDER={BOARD_TOP_BORDER}
                leads={leads}
                draggedCard={draggedCard}
                dragOverColumn={dragOverColumn}
                showArchived={showArchived}
                filterAssignee={filterAssignee}
                filterDue={filterDue}
                searchQuery={searchQuery}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
                onDragOver={setDragOverColumn}
                onDragLeave={() => setDragOverColumn(null)}
                onDrop={handleDrop}
                onOpenEditCard={openEditCardModal}
                onOpenNewCard={openNewCardModal}
                onEditColumn={col => { const c = board?.columns.find((x: any) => x.id === col.id); setColumnModal({ open: true, column: c || { id: col.id, board_id: "", name: col.name, color: "gray", position: 0, cards: [] } }); setColumnName(col.name); setColumnColor("gray"); }}
                onDeleteColumn={(id, name) => showConfirm("Hapus Kolom", `Kolom "${name}" dan semua card di dalamnya akan dihapus permanen.`, () => deleteColumn(id))}
              />
            ))}
          </div>
        </div>
      )}

      {/* Modals */}
      <CardModal
        open={cardModal.open} card={cardModal.card} columnId={cardModal.columnId}
        cardForm={cardForm} setCardForm={setCardForm} saving={saving}
        currentProject={currentProject} currentProjectLead={currentProjectLead} leads={leads}
        users={users}
        onCreateCard={() => createCard(cardModal.columnId)}
        onUpdateCard={() => cardModal.card && updateCard(cardModal.card.id)}
        onArchiveCard={() => cardModal.card && archiveCard(cardModal.card.id, !cardModal.card.is_archived)}
        onDeleteCard={() => cardModal.card && showConfirm("Hapus Card", "Card ini akan dihapus permanen.", () => deleteCard(cardModal.card!.id))}
        onToggleLabel={() => {}}
        onClose={() => setCardModal({ open: false, card: null, columnId: "" })}
        onAddChecklist={(text) => cardModal.card && addChecklistItem(cardModal.card.id, text)}
        onToggleChecklist={(itemId, isDone) => cardModal.card && toggleChecklist(cardModal.card.id, itemId, isDone)}
        onAddComment={(content) => cardModal.card && addComment(cardModal.card.id, content)}
        onUploadAttachment={(file) => cardModal.card && uploadCardAttachment(cardModal.card.id, file)}
        formatDateTime={formatDateTime}
      />

      <ColumnModal
        open={columnModal.open} column={columnModal.column}
        columnName={columnName} setColumnName={setColumnName}
        columnColor={columnColor} setColumnColor={setColumnColor}
        onCreate={createColumn} onUpdate={() => columnModal.column && updateColumn(columnModal.column.id)}
        onClose={() => setColumnModal({ open: false, column: null })}
      />

      <ProjectModal
        open={projectModal} form={projectForm} setForm={setProjectForm}
        leads={leads} saving={saving}
        onCreate={createProject} onClose={() => setProjectModal(false)}
      />

      <EditProjectModal
        open={editProjectModal?.open || false} form={editProjectForm} setForm={setEditProjectForm}
        leads={leads} saving={saving}
        onSave={saveEditProject} onClose={() => setEditProjectModal(null)}
      />

      {confirmModal && (
        <ConfirmModal open={confirmModal.open} title={confirmModal.title} message={confirmModal.message}
          onConfirm={confirmModal.onConfirm} onClose={() => setConfirmModal(null)} />
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
