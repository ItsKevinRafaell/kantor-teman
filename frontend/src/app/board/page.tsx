"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "../../lib/api";
import { Plus, Trash2, Calendar, User, MessageSquare, CheckSquare, X, AlertTriangle } from "lucide-react";
import Toast from "../../components/Toast";

const COLORS = {
  primary: "bg-yellow-500 hover:bg-yellow-600 text-white",
  danger: "bg-red-500 hover:bg-red-600 text-white",
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
};

const LABEL_COLORS: Record<string, string> = {
  red: "bg-red-500", orange: "bg-orange-500", yellow: "bg-yellow-500",
  green: "bg-green-500", blue: "bg-blue-500", purple: "bg-purple-500", pink: "bg-pink-500",
};

interface Project { id: string; name: string; status: string; lead_id: number; lead?: { id: number; business_name: string; phone_number: string }; }
interface BoardCard { id: string; column_id: string; title: string; description: string | null; assignee: string | null; due_date: string | null; labels: string[]; position: number; is_archived: boolean; lead_id?: number | null; created_at: string; updated_at: string | null; comments: { id: string; content: string; author: string; created_at: string }[]; checklist: { id: string; text: string; is_done: boolean }[]; }
interface BoardColumn { id: string; board_id: string; name: string; position: number; color?: string; cards: BoardCard[]; }
interface Board { id: string; project_id: string; created_at: string; columns: BoardColumn[]; project?: Project; }
interface BoardOverview { project_id: string; project_name: string; board_id: string; cards_count: number; columns_count: number; client_name?: string; }

function Modal({ open, onClose, title, children, size = "md" }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode; size?: "sm" | "md" | "lg" }) {
  if (!open) return null;
  const sizeClass = size === "sm" ? "max-w-sm" : size === "lg" ? "max-w-2xl" : "max-w-lg";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="fixed inset-0 bg-black/50" />
      <div className={`relative bg-white dark:bg-[#242423] rounded-2xl shadow-2xl ${sizeClass} w-full max-h-[90vh] overflow-y-auto`} onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 bg-white dark:bg-[#242423] px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">{title}</h2>
          <button onClick={onClose} className="p-1 text-neutral-400 hover:text-neutral-600"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

export default function BoardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [board, setBoard] = useState<Board | null>(null);
  const [overview, setOverview] = useState<BoardOverview[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"overview" | "board">("overview");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Card modal
  const [cardModal, setCardModal] = useState<{ open: boolean; card: BoardCard | null; columnId: string }>({ open: false, card: null, columnId: "" });
  const [cardForm, setCardForm] = useState({ title: "", description: "", due_date: "", labels: [] as string[] });
  const [saving, setSaving] = useState(false);

  // Column modal
  const [columnModal, setColumnModal] = useState<{ open: boolean; column: BoardColumn | null }>({ open: false, column: null });
  const [columnName, setColumnName] = useState("");
  const [columnColor, setColumnColor] = useState("yellow");

  // Drag state
  const [draggedCard, setDraggedCard] = useState<{ card: BoardCard; fromColumn: string } | null>(null);

  useEffect(() => {
    fetchProjects();
    fetchOverview();
  }, []);

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

  async function fetchBoard(projectId: string) {
    try { const res = await apiFetch(`/api/projects/${projectId}/board`); if (res.ok) setBoard(await res.json()); }
    catch (e) { console.error(e); }
  }

  async function createCard(columnId: string) {
    if (!cardForm.title.trim()) return;
    setSaving(true);
    try {
      const res = await apiFetch(`/api/board-columns/${columnId}/cards`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: cardForm.title, description: cardForm.description || null, due_date: cardForm.due_date || null, labels: cardForm.labels }),
      });
      if (res.ok) {
        const newCard = await res.json();
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => col.id === columnId ? { ...col, cards: [...(col.cards || []), newCard] } : col) } : prev);
        setCardForm({ title: "", description: "", due_date: "", labels: [] });
        setCardModal({ open: false, card: null, columnId: "" });
        setToast({ message: "Card dibuat", type: "success" });
      }
    } catch (e) { setToast({ message: "Gagal membuat card", type: "error" }); } finally { setSaving(false); }
  }

  async function updateCard(cardId: string) {
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: cardForm.title, description: cardForm.description || null, due_date: cardForm.due_date || null, labels: cardForm.labels }),
      });
      if (res.ok) {
        const updated = await res.json();
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(card => card.id === cardId ? { ...card, ...updated } : card) })) } : prev);
        setCardModal({ open: false, card: null, columnId: "" });
        setToast({ message: "Card diupdate", type: "success" });
      }
    } catch (e) { setToast({ message: "Gagal update card", type: "error" }); }
  }

  async function deleteCard(cardId: string) {
    if (!confirm("Yakin hapus card ini?")) return;
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}`, { method: "DELETE" });
      if (res.ok) {
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).filter(card => card.id !== cardId) })) } : prev);
        setCardModal({ open: false, card: null, columnId: "" });
        setToast({ message: "Card dihapus", type: "success" });
      }
    } catch (e) { setToast({ message: "Gagal hapus card", type: "error" }); }
  }

  async function moveCard(cardId: string, toColumnId: string) {
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}/move`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ column_id: toColumnId }) });
      if (res.ok) { if (selectedProject) fetchBoard(selectedProject); setToast({ message: "Card dipindahkan", type: "success" }); }
    } catch (e) { setToast({ message: "Gagal memindahkan card", type: "error" }); }
  }

  async function createColumn() {
    if (!columnName.trim() || !board) return;
    try {
      const res = await apiFetch(`/api/boards/${board.id}/columns`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: columnName, color: columnColor }) });
      if (res.ok) {
        const newCol = await res.json();
        setBoard(prev => prev ? { ...prev, columns: [...prev.columns, { ...newCol, cards: [] }] } : prev);
        setColumnName("");
        setColumnColor("yellow");
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
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(card => card.id === cardId ? { ...card, checklist: [...card.checklist, item] } : card) })) } : prev);
      }
    } catch (e) { setToast({ message: "Gagal tambah checklist", type: "error" }); }
  }

  async function toggleChecklist(cardId: string, itemId: string, isDone: boolean) {
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}/checklist/${itemId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_done: isDone }) });
      if (res.ok) {
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(card => card.id === cardId ? { ...card, checklist: card.checklist.map(item => item.id === itemId ? { ...item, is_done: isDone } : item) } : card) })) } : prev);
      }
    } catch (e) { setToast({ message: "Gagal update checklist", type: "error" }); }
  }

  async function addComment(cardId: string, content: string) {
    if (!content.trim()) return;
    try {
      const res = await apiFetch(`/api/board-cards/${cardId}/comments`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }) });
      if (res.ok) {
        const comment = await res.json();
        setBoard(prev => prev ? { ...prev, columns: prev.columns.map(col => ({ ...col, cards: (col.cards || []).map(card => card.id === cardId ? { ...card, comments: [...card.comments, comment] } : card) })) } : prev);
      }
    } catch (e) { setToast({ message: "Gagal tambah komentar", type: "error" }); }
  }

  function handleDragStart(card: BoardCard, fromColumn: string) { setDraggedCard({ card, fromColumn }); }
  function handleDragOver(e: React.DragEvent) { e.preventDefault(); }
  function handleDrop(toColumnId: string) {
    if (draggedCard && draggedCard.fromColumn !== toColumnId) moveCard(draggedCard.card.id, toColumnId);
    setDraggedCard(null);
  }

  function formatDate(date: string | null) { if (!date) return ""; return new Date(date).toLocaleDateString("id-ID", { day: "numeric", month: "short" }); }
  function toggleLabel(label: string) { setCardForm(prev => ({ ...prev, labels: prev.labels.includes(label) ? prev.labels.filter(l => l !== label) : [...prev.labels, label] })); }

  if (loading) return <div className="p-6 animate-pulse space-y-4"><div className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded" /><div className="h-64 bg-gray-100 dark:bg-gray-800 rounded-xl" /></div>;

  const projectOptions = projects.map(p => ({ id: p.id, name: p.name }));
  const currentProject = projects.find(p => p.id === selectedProject);

  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Project Board</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Kelola task proyek dengan Trello-like board</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={selectedProject} onChange={e => setSelectedProject(e.target.value)} className="px-3 py-2 bg-white dark:bg-[#242423] border border-gray-200 dark:border-gray-700 rounded-lg text-sm">
            <option value="">Semua Proyek (Overview)</option>
            {projectOptions.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          {board && (
            <button onClick={() => { setColumnModal({ open: true, column: null }); setColumnName(""); setColumnColor("yellow"); }} className={`px-3 py-2 text-sm rounded-lg flex items-center gap-1 ${COLORS.primary}`}>
              <Plus className="w-4 h-4" /> Kolom
            </button>
          )}
        </div>
      </div>

      {currentProject?.lead && (
        <div className="mb-4 flex items-center gap-2 px-3 py-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg w-fit">
          <span className="text-sm font-medium text-yellow-700 dark:text-yellow-300">{currentProject.lead.business_name}</span>
        </div>
      )}

      {viewMode === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {overview.length === 0 && (
            <div className="col-span-full bg-white dark:bg-[#242423] rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center">
              <p className="text-neutral-500">Belum ada proyek dengan board.</p>
            </div>
          )}
          {overview.map(item => (
            <div key={item.project_id} onClick={() => setSelectedProject(item.project_id)} className="bg-white dark:bg-[#242423] rounded-xl border border-gray-200 dark:border-gray-700 p-4 cursor-pointer hover:border-yellow-400 transition-colors">
              <h3 className="font-semibold text-neutral-800 dark:text-neutral-200">{item.project_name}</h3>
              {item.client_name && <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">{item.client_name}</p>}
              <p className="text-sm text-neutral-500 mt-1">{item.cards_count} cards • {item.columns_count} kolom</p>
            </div>
          ))}
        </div>
      )}

      {viewMode === "board" && board && (
        <div className="flex-1 overflow-x-auto">
          <div className="flex gap-4 h-full min-w-max pb-4">
            {board.columns.map(column => {
              const colColor = COLUMN_COLORS[column.color || "yellow"] || COLUMN_COLORS.yellow;
              return (
                <div key={column.id} className="w-72 shrink-0 bg-gray-100 dark:bg-[#1a1a19] rounded-xl flex flex-col" onDragOver={handleDragOver} onDrop={() => handleDrop(column.id)}>
                  <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                    <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 text-sm">{column.name}</h3>
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-neutral-500 bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded">{column.cards?.length || 0}</span>
                      <button onClick={() => { setColumnModal({ open: true, column }); setColumnName(column.name); setColumnColor(column.color || "yellow"); }} className="p-1 text-neutral-400 hover:text-yellow-500 text-xs">Edit</button>
                      <button onClick={() => deleteColumn(column.id)} className="p-1 text-neutral-400 hover:text-red-500"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto p-2 space-y-2">
                    {Array.isArray(column.cards) && column.cards.map(card => (
                      <div key={card.id} draggable onDragStart={() => handleDragStart(card, column.id)} onClick={() => {
                        setCardModal({ open: true, card, columnId: column.id });
                        setCardForm({ title: card.title, description: card.description || "", due_date: card.due_date || "", labels: Array.isArray(card.labels) ? card.labels : [] });
                      }} className="bg-white dark:bg-[#242423] rounded-lg p-3 shadow-sm border border-gray-200 dark:border-gray-700 cursor-pointer hover:border-yellow-400 transition-colors">
                        {Array.isArray(card.labels) && card.labels.length > 0 && (
                          <div className="flex gap-1 mb-2">{card.labels.map(label => <span key={label} className={`w-6 h-2 rounded ${LABEL_COLORS[label]}`} />)}</div>
                        )}
                        <h4 className="font-medium text-neutral-800 dark:text-neutral-200 text-sm">{card.title}</h4>
                        <div className="flex items-center gap-3 mt-2 text-xs text-neutral-500">
                          {card.due_date && <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{formatDate(card.due_date)}</span>}
                          {card.assignee && <span className="flex items-center gap-1"><User className="w-3 h-3" />{card.assignee}</span>}
                          {card.comments?.length > 0 && <span className="flex items-center gap-1"><MessageSquare className="w-3 h-3" />{card.comments.length}</span>}
                          {card.checklist?.length > 0 && <span className="flex items-center gap-1"><CheckSquare className="w-3 h-3" />{card.checklist.filter(c => c.is_done).length}/{card.checklist.length}</span>}
                        </div>
                      </div>
                    ))}
                    <button onClick={() => { setCardModal({ open: true, card: null, columnId: column.id }); setCardForm({ title: "", description: "", due_date: "", labels: [] }); }} className="w-full p-2 text-sm text-neutral-500 hover:text-neutral-700 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-lg flex items-center justify-center gap-1">
                      <Plus className="w-4 h-4" /> Add Card
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Card Modal */}
      <Modal open={cardModal.open} onClose={() => setCardModal({ open: false, card: null, columnId: "" })} title={cardModal.card ? "Edit Card" : "New Card"} size="lg">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">Title</label>
            <input type="text" value={cardForm.title} onChange={e => setCardForm(prev => ({ ...prev, title: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm" placeholder="Card title..." />
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">Description</label>
            <textarea value={cardForm.description} onChange={e => setCardForm(prev => ({ ...prev, description: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm" rows={3} placeholder="Description..." />
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">Due Date</label>
            <input type="date" value={cardForm.due_date} onChange={e => setCardForm(prev => ({ ...prev, due_date: e.target.value }))} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">Labels</label>
            <div className="flex gap-2 flex-wrap">{Object.keys(LABEL_COLORS).map(label => (
              <button key={label} type="button" onClick={() => toggleLabel(label)} className={`w-6 h-6 rounded ${LABEL_COLORS[label]} ${cardForm.labels.includes(label) ? "ring-2 ring-offset-2 ring-yellow-500" : "opacity-40"}`} />
            ))}</div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => cardModal.card ? updateCard(cardModal.card.id) : createCard(cardModal.columnId)} disabled={saving || !cardForm.title.trim()} className={`flex-1 px-4 py-2 text-sm rounded-lg ${COLORS.primary} disabled:opacity-50`}>
              {saving ? "Menyimpan..." : cardModal.card ? "Update" : "Create"}
            </button>
            {cardModal.card && (
              <button onClick={() => deleteCard(cardModal.card!.id)} className="px-4 py-2 text-sm rounded-lg bg-red-100 text-red-600 hover:bg-red-200">
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>

          {cardModal.card && (
            <>
              <hr className="border-gray-200 dark:border-gray-700" />
              <div>
                <h4 className="text-sm font-semibold mb-2 flex items-center gap-2"><CheckSquare className="w-4 h-4" /> Checklist</h4>
                <div className="space-y-2">
                  {cardModal.card.checklist?.map(item => (
                    <label key={item.id} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={item.is_done} onChange={e => toggleChecklist(cardModal.card!.id, item.id, e.target.checked)} className="rounded" />
                      <span className={item.is_done ? "line-through text-neutral-400" : ""}>{item.text}</span>
                    </label>
                  ))}
                  <div className="flex gap-2">
                    <input type="text" placeholder="Add item..." className="flex-1 px-2 py-1 bg-gray-100 dark:bg-gray-800 border-0 rounded text-sm" onKeyDown={e => { if (e.key === "Enter" && (e.target as HTMLInputElement).value) { addChecklistItem(cardModal.card!.id, (e.target as HTMLInputElement).value); (e.target as HTMLInputElement).value = ""; } }} />
                  </div>
                </div>
              </div>
              <div>
                <h4 className="text-sm font-semibold mb-2 flex items-center gap-2"><MessageSquare className="w-4 h-4" /> Comments</h4>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {cardModal.card.comments?.map(c => (
                    <div key={c.id} className="bg-gray-100 dark:bg-gray-800 rounded p-2 text-sm">
                      <p>{c.content}</p>
                      <p className="text-xs text-neutral-400 mt-1">{c.author} • {new Date(c.created_at).toLocaleDateString("id-ID")}</p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2 mt-2">
                  <input type="text" placeholder="Add comment..." className="flex-1 px-2 py-1 bg-gray-100 dark:bg-gray-800 border-0 rounded text-sm" onKeyDown={e => { if (e.key === "Enter" && (e.target as HTMLInputElement).value) { addComment(cardModal.card!.id, (e.target as HTMLInputElement).value); (e.target as HTMLInputElement).value = ""; } }} />
                </div>
              </div>
            </>
          )}
        </div>
      </Modal>

      {/* Column Modal */}
      <Modal open={columnModal.open} onClose={() => setColumnModal({ open: false, column: null })} title={columnModal.column ? "Edit Column" : "New Column"}>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">Column Name</label>
            <input type="text" value={columnName} onChange={e => setColumnName(e.target.value)} className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm" placeholder="e.g., In Progress" />
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Color</label>
            <div className="flex gap-2 flex-wrap">
              {Object.keys(COLUMN_COLORS).map(color => (
                <button key={color} type="button" onClick={() => setColumnColor(color)} className={`w-8 h-8 rounded-lg ${COLUMN_COLORS[color].bg} border-2 ${columnColor === color ? "border-neutral-900 dark:border-white" : COLUMN_COLORS[color].border}`} />
              ))}
            </div>
          </div>
          <button onClick={() => columnModal.column ? updateColumn(columnModal.column.id) : createColumn()} disabled={!columnName.trim()} className={`w-full px-4 py-2 text-sm rounded-lg ${COLORS.primary} disabled:opacity-50`}>
            {columnModal.column ? "Update" : "Create"} Column
          </button>
        </div>
      </Modal>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
