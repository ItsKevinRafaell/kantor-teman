"use client";
import { useState, useEffect } from "react";
import { apiFetch } from "../../lib/api";
import { User } from "lucide-react";
import Toast from "../../components/Toast";
import ConfirmModal from "../../components/ConfirmModal";
import { useAuth } from "../../contexts/AuthContext";
import { BoardColumnItem } from "../../components/board/BoardColumn";
import { BoardOverviewCard } from "../../components/board/BoardOverview";
import BoardHeader from "../../components/board/BoardHeader";
import { ColumnModal, ProjectModal, EditProjectModal } from "../../components/board/BoardModals";
import { CardModal } from "../../components/board/CardModal";
import type { Lead, Project, BoardCard, BoardColumn, Board, BoardOverview } from "../../components/board/types";

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

  const [confirmModal, setConfirmModal] = useState<{ open: boolean; title: string; message: string; onConfirm: () => void } | null>(null);
  function showConfirm(title: string, message: string, onConfirm: () => void) {
    setConfirmModal({ open: true, title, message, onConfirm });
  }

  const [showArchivedProjects, setShowArchivedProjects] = useState(false);
  const [editProjectModal, setEditProjectModal] = useState<{ open: boolean; projectId: string } | null>(null);
  const [editProjectForm, setEditProjectForm] = useState({ name: "", type: "FIXED" as "FIXED" | "RETAINER", status: "ACTIVE", nominal: 0, lead_id: null as number | null, color: "yellow" });

  // Data fetching
  async function fetchProjects() { try { const r = await apiFetch("/api/projects"); if (r.ok) setProjects(await r.json()); } catch {} }
  async function fetchOverview(archived = false) { try { const r = await apiFetch(`/api/boards/overview?show_archived=${archived}`); if (r.ok) setOverview(await r.json()); } catch {} finally { setLoading(false); } }
  async function fetchLeads() { try { const r = await apiFetch("/api/leads"); if (r.ok) setLeads(await r.json()); } catch {} }
  async function fetchBoard(projectId: string) { try { const r = await apiFetch(`/api/projects/${projectId}/board`); if (r.ok) setBoard(await r.json()); } catch {} }

  useEffect(() => { fetchProjects(); fetchOverview(false); fetchLeads(); }, []);
  useEffect(() => { fetchOverview(showArchivedProjects); }, [showArchivedProjects]);
  useEffect(() => { if (selectedProject) { fetchBoard(selectedProject); setViewMode("board"); } else { setBoard(null); setViewMode("overview"); } }, [selectedProject]);

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
      if (res.ok) { const newCard = await res.json(); setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => col.id === columnId ? { ...col, cards: [...(col.cards || []), newCard] } : col) } : prev); setCardForm({ title: "", description: "", due_date: "", labels: [], assignee: "", lead_id: null, color: "yellow" }); setCardModal({ open: false, card: null, columnId: "" }); setToast({ message: "Card dibuat", type: "success" }); }
    } catch { setToast({ message: "Gagal membuat card", type: "error" }); } finally { setSaving(false); }
  }

  async function updateCard(cardId: string) {
    const effectiveLeadId = currentProject?.lead_id ?? cardForm.lead_id;
    try { const res = await apiFetch(`/api/board-cards/${cardId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: cardForm.title, description: cardForm.description || null, due_date: cardForm.due_date || null, labels: cardForm.labels, assignee: cardForm.assignee || null, lead_id: effectiveLeadId, color: cardForm.color }) }); if (res.ok) { const updated = await res.json(); setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, ...updated } : c) })) } : prev); setCardModal({ open: false, card: null, columnId: "" }); setToast({ message: "Card diupdate", type: "success" }); } }
    catch { setToast({ message: "Gagal update card", type: "error" }); }
  }

  async function archiveCard(cardId: string, isArchived: boolean) {
    try { const res = await apiFetch(`/api/board-cards/${cardId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_archived: isArchived }) }); if (res.ok) { await fetchBoard(selectedProject); setCardModal({ open: false, card: null, columnId: "" }); setToast({ message: isArchived ? "Card diarsipkan" : "Card dipulihkan", type: "success" }); } }
    catch { setToast({ message: "Gagal arsipkan card", type: "error" }); }
  }

  async function deleteCard(cardId: string) {
    try { const res = await apiFetch(`/api/board-cards/${cardId}`, { method: "DELETE" }); if (res.ok) { setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).filter(c => c.id !== cardId) })) } : prev); setCardModal({ open: false, card: null, columnId: "" }); setToast({ message: "Card dihapus", type: "success" }); } }
    catch { setToast({ message: "Gagal hapus card", type: "error" }); }
  }

  async function moveCard(cardId: string, toColumnId: string, toPosition?: number) {
    try { const res = await apiFetch(`/api/board-cards/${cardId}/move`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ column_id: toColumnId, position: toPosition }) }); if (res.ok && selectedProject) fetchBoard(selectedProject); }
    catch { setToast({ message: "Gagal memindahkan card", type: "error" }); }
  }

  // Column CRUD
  async function createColumn() {
    if (!columnName.trim() || !board) return;
    try { const res = await apiFetch(`/api/boards/${board.id}/columns`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: columnName, color: columnColor }) }); if (res.ok) { const newCol = await res.json(); setBoard(prev => prev ? { ...prev, columns: [...prev.columns, { ...newCol, cards: [] }] } : prev); setColumnName(""); setColumnColor("yellow"); setColumnModal({ open: false, column: null }); setToast({ message: "Kolom dibuat", type: "success" }); } }
    catch { setToast({ message: "Gagal membuat kolom", type: "error" }); }
  }

  async function updateColumn(columnId: string) {
    try { const res = await apiFetch(`/api/board-columns/${columnId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: columnName, color: columnColor }) }); if (res.ok) { const updated = await res.json(); setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => col.id === columnId ? { ...col, ...updated } : col) } : prev); setColumnModal({ open: false, column: null }); setToast({ message: "Kolom diupdate", type: "success" }); } }
    catch { setToast({ message: "Gagal update kolom", type: "error" }); }
  }

  async function deleteColumn(columnId: string) {
    try { const res = await apiFetch(`/api/board-columns/${columnId}`, { method: "DELETE" }); if (res.ok) { setBoard(prev => prev ? { ...prev, columns: prev.columns.filter(col => col.id !== columnId) } : prev); setToast({ message: "Kolom dihapus", type: "success" }); } }
    catch { setToast({ message: "Gagal hapus kolom", type: "error" }); }
  }

  // Checklist & Comments
  async function addChecklistItem(cardId: string, text: string) {
    if (!text.trim()) return;
    try { const res = await apiFetch(`/api/board-cards/${cardId}/checklist`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) }); if (res.ok) { const item = await res.json(); setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, checklist: [...c.checklist, item] } : c) })) } : prev); setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, checklist: [...(prev.card!.checklist || []), item] } } : prev); refreshCardActivity(cardId); } else { setToast({ message: "Gagal tambah checklist", type: "error" }); } }
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
    try { const res = await apiFetch(`/api/board-cards/${cardId}/comments`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }) }); if (res.ok) { const comment = await res.json(); setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(c => c.id === cardId ? { ...c, comments: [...c.comments, comment] } : c) })) } : prev); setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, comments: [...(prev.card!.comments || []), comment] } } : prev); refreshCardActivity(cardId); } else { setToast({ message: "Gagal tambah komentar", type: "error" }); } }
    catch { setToast({ message: "Gagal tambah komentar", type: "error" }); }
  }

  async function refreshCardActivity(cardId: string) {
    try { const res = await apiFetch(`/api/board-cards/${cardId}`); if (res.ok) { const updated = await res.json(); setCardModal(prev => prev.card?.id === cardId ? { ...prev, card: { ...prev.card!, activity: updated.activity || [] } } : prev); } } catch {}
  }

  // Drag & Drop
  function handleDragStart(card: BoardCard, fromColumn: string) { setDraggedCard({ card, fromColumn }); }
  function handleDragEnd() { setDraggedCard(null); setDragOverColumn(null); }
  function handleDrop(toColumnId: string) { if (draggedCard && draggedCard.fromColumn !== toColumnId) moveCard(draggedCard.card.id, toColumnId); setDraggedCard(null); setDragOverColumn(null); }
  function formatDateTime(d: string) { return new Date(d).toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); }

  // Card modal helpers
  function openNewCardModal(columnId: string) {
    setCardModal({ open: true, card: null, columnId });
    setCardForm({ title: "", description: "", due_date: "", labels: [], assignee: localStorage.getItem("kt_name") || "", lead_id: null, color: "yellow" });
  }
  async function openEditCardModal(card: BoardCard, columnId: string) {
    setCardModal({ open: true, card, columnId });
    setCardForm({ title: card.title, description: card.description || "", due_date: card.due_date || "", labels: Array.isArray(card.labels) ? card.labels : [], assignee: card.assignee || "", lead_id: card.lead_id ?? null, color: card.color || "yellow" });
    try { const res = await apiFetch(`/api/board-cards/${card.id}`); if (res.ok) { const fresh = await res.json(); setCardModal(prev => prev.card?.id === card.id ? { ...prev, card: fresh } : prev); } } catch {}
  }

  if (loading) return <div className="p-6 animate-pulse space-y-4"><div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded" /><div className="h-64 bg-gray-100 dark:bg-gray-800 rounded-xl" /></div>;

  const currentProject = projects.find(p => p.id === selectedProject);
  const currentProjectLead = leads.find(l => l.id === currentProject?.lead_id);

  return (
    <div className="h-full flex flex-col p-6">
      <BoardHeader
        viewMode={viewMode} currentProject={currentProject} isAdmin={isAdmin}
        showArchivedProjects={showArchivedProjects} setShowArchivedProjects={setShowArchivedProjects}
        showArchived={showArchived} setShowArchived={setShowArchived}
        board={board}
        onNewProject={() => { setProjectModal(true); setProjectForm({ name: "", type: "FIXED", status: "ACTIVE", nominal: 0, lead_id: null, color: "yellow" }); }}
        onNewColumn={() => { setColumnModal({ open: true, column: null }); setColumnName(""); setColumnColor("yellow"); }}
        onBackToOverview={() => setSelectedProject("")}
      />

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
              key={item.project_id} item={item} projects={projects}
              onSelectProject={setSelectedProject}
              onArchiveProject={async (id: string, arch: boolean) => { try { await apiFetch(`/api/projects/${id}/archive`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_archived: arch }) }); if (arch) setToast({ message: "Proyek diarsipkan", type: "success" }); else setToast({ message: "Proyek dipulihkan", type: "success" }); await fetchOverview(showArchivedProjects); } catch { setToast({ message: "Gagal arsipkan proyek", type: "error" }); } }}
              onDeleteProject={deleteProjectFromBoard}
              onShowConfirm={showConfirm}
              onEditProject={p => { setEditProjectForm({ name: p.name, type: p.type as "FIXED"|"RETAINER", status: p.status, nominal: (p as any).nominal || 0, lead_id: p.lead_id, color: p.color || "yellow" }); setEditProjectModal({ open: true, projectId: p.id }); }}
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
                COLUMN_COLORS={{ yellow: { bg: "bg-yellow-400", border: "border-yellow-400" }, red: { bg: "bg-red-400", border: "border-red-400" }, blue: { bg: "bg-blue-400", border: "border-blue-400" }, green: { bg: "bg-green-400", border: "border-green-400" }, purple: { bg: "bg-purple-400", border: "border-purple-400" }, pink: { bg: "bg-pink-400", border: "border-pink-400" }, gray: { bg: "bg-gray-400", border: "border-gray-400" } } as any}
                BOARD_TOP_BORDER={{ yellow: "border-t-yellow-400", red: "border-t-red-400", blue: "border-t-blue-400", green: "border-t-green-400", purple: "border-t-purple-400", pink: "border-t-pink-400", gray: "border-t-gray-400" } as any}
                leads={leads}
                draggedCard={draggedCard}
                dragOverColumn={dragOverColumn}
                showArchived={showArchived}
                filterAssignee=""
                filterDue=""
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
                onDragOver={setDragOverColumn}
                onDragLeave={() => setDragOverColumn(null)}
                onDrop={handleDrop}
                onOpenEditCard={openEditCardModal}
                onOpenNewCard={openNewCardModal}
                onEditColumn={col => { const c = board?.columns.find((x: any) => x.id === col.id); setColumnModal({ open: true, column: c || { id: col.id, board_id: "", name: col.name, color: col.color, position: 0, cards: [] } }); setColumnName(col.name); setColumnColor(col.color || "yellow"); }}
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
        onCreateCard={() => createCard(cardModal.columnId)}
        onUpdateCard={() => cardModal.card && updateCard(cardModal.card.id)}
        onArchiveCard={() => cardModal.card && archiveCard(cardModal.card.id, !cardModal.card.is_archived)}
        onDeleteCard={() => cardModal.card && showConfirm("Hapus Card", "Card ini akan dihapus permanen.", () => deleteCard(cardModal.card!.id))}
        onToggleLabel={() => {}}
        onClose={() => setCardModal({ open: false, card: null, columnId: "" })}
        onAddChecklist={(text) => cardModal.card && addChecklistItem(cardModal.card.id, text)}
        onToggleChecklist={(itemId, isDone) => cardModal.card && toggleChecklist(cardModal.card.id, itemId, isDone)}
        onAddComment={(content) => cardModal.card && addComment(cardModal.card.id, content)}
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