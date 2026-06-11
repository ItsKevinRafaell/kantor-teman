"use client";

import { Plus, Calendar, User, MessageSquare, CheckSquare } from "lucide-react";
import { CARD_COLORS, LABEL_COLORS } from "./types";
import type { BoardCard, Lead } from "./types";
import type { DragEvent, PointerEvent as ReactPointerEvent } from "react";
import { useRef } from "react";

interface Props {
  card: BoardCard;
  leads: Lead[];
  draggedCardId: string | null;
  showArchived: boolean;
  onDragStart: (card: BoardCard) => void;
  onDragEnd: () => void;
  onPointerDragOver: (columnId: string | null) => void;
  onPointerDrop: (columnId: string) => void;
  onOpenEdit: (card: BoardCard) => void;
}

function columnIdFromPoint(x: number, y: number) {
  const target = document.elementFromPoint(x, y) as HTMLElement | null;
  return target?.closest<HTMLElement>("[data-board-column-id]")?.dataset.boardColumnId || null;
}

export function BoardCardItem({
  card, leads, draggedCardId, showArchived, onDragStart, onDragEnd, onPointerDragOver, onPointerDrop, onOpenEdit,
}: Props) {
  const cc = CARD_COLORS[card.color || "gray"] || CARD_COLORS.gray;
  const isDragging = draggedCardId === card.id;
  const leadName = card.lead?.business_name || leads.find(l => l.id === card.lead_id)?.business_name;
  const suppressClickRef = useRef(false);

  function formatDate(d: string | null) {
    if (!d) return "";
    return new Date(d).toLocaleDateString("id-ID", { day: "numeric", month: "short" });
  }

  function handlePointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    if ((event.target as HTMLElement).closest("button,input,textarea,select,a")) return;

    const startX = event.clientX;
    const startY = event.clientY;
    let dragging = false;
    let lastColumnId: string | null = null;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;

    const cleanup = () => {
      document.removeEventListener("pointermove", handleMove);
      document.removeEventListener("pointerup", handleUp);
      document.removeEventListener("pointercancel", handleCancel);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
    };

    const startDrag = () => {
      if (dragging) return;
      dragging = true;
      suppressClickRef.current = true;
      document.body.style.cursor = "grabbing";
      document.body.style.userSelect = "none";
      onDragStart(card);
    };

    const handleMove = (moveEvent: PointerEvent) => {
      const dx = moveEvent.clientX - startX;
      const dy = moveEvent.clientY - startY;
      if (!dragging && Math.hypot(dx, dy) >= 8) startDrag();
      if (!dragging) return;

      moveEvent.preventDefault();
      const columnId = columnIdFromPoint(moveEvent.clientX, moveEvent.clientY);
      if (columnId !== lastColumnId) {
        lastColumnId = columnId;
        onPointerDragOver(columnId);
      }
    };

    const handleUp = (upEvent: PointerEvent) => {
      cleanup();
      if (!dragging) return;
      upEvent.preventDefault();
      const columnId = columnIdFromPoint(upEvent.clientX, upEvent.clientY);
      if (columnId) onPointerDrop(columnId);
      else onDragEnd();
      window.setTimeout(() => {
        suppressClickRef.current = false;
      }, 150);
    };

    const handleCancel = () => {
      cleanup();
      if (dragging) onDragEnd();
      window.setTimeout(() => {
        suppressClickRef.current = false;
      }, 150);
    };

    document.addEventListener("pointermove", handleMove, { passive: false });
    document.addEventListener("pointerup", handleUp);
    document.addEventListener("pointercancel", handleCancel);
  }

  return (
    <div
      data-board-card-id={card.id}
      onPointerDown={handlePointerDown}
      onClick={() => {
        if (suppressClickRef.current) return;
        onOpenEdit(card);
      }}
      className={`rounded-xl p-3 shadow-sm cursor-pointer select-none transition-all duration-150
        ${cc.bg} ${cc.accent}
        ${card.is_archived ? "opacity-50" : ""}
        ${isDragging ? "opacity-40 scale-95 rotate-1 shadow-xl" : "hover:shadow-md hover:-translate-y-0.5"}`}
    >
      {Array.isArray(card.labels) && card.labels.length > 0 && (
        <div className="flex gap-1 mb-2">
          {card.labels.map(label => <span key={label} className={`h-1.5 w-8 rounded-full ${LABEL_COLORS[label]}`} />)}
        </div>
      )}
      <div className="flex items-start gap-1">
        <h4 className="font-medium text-neutral-800 dark:text-neutral-200 text-sm leading-snug flex-1">{card.title}</h4>
        {card.is_workspace_linked && (
          <span title="Nama diatur dari Workspace" className="shrink-0 mt-0.5">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
          </span>
        )}
      </div>
      {leadName && (
        <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">{leadName}</p>
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
}

interface ColumnProps {
  column: { id: string; name: string; color?: string; cards: BoardCard[] };
  COLUMN_COLORS: Record<string, { bg: string; border: string; text: string }>;
  BOARD_TOP_BORDER: Record<string, string>;
  leads: Lead[];
  draggedCard: { card: BoardCard; fromColumn: string } | null;
  dragOverColumn: string | null;
  showArchived: boolean;
  filterAssignee: string;
  filterDue: string;
  searchQuery: string;
  onDragStart: (card: BoardCard, fromColumn: string) => void;
  onDragEnd: () => void;
  onDragOver: (columnId: string) => void;
  onDragLeave: () => void;
  onDrop: (toColumnId: string, event?: DragEvent<HTMLDivElement>) => void;
  onOpenEditCard: (card: BoardCard, columnId: string) => void;
  onOpenNewCard: (columnId: string) => void;
  onEditColumn: (column: { id: string; name: string; color?: string }) => void;
  onDeleteColumn: (columnId: string, name: string) => void;
}

export function BoardColumnItem({
  column, COLUMN_COLORS, BOARD_TOP_BORDER, leads, draggedCard, dragOverColumn,
  showArchived, filterAssignee, filterDue, searchQuery, onDragStart, onDragEnd, onDragOver, onDragLeave, onDrop,
  onOpenEditCard, onOpenNewCard, onEditColumn, onDeleteColumn,
}: ColumnProps) {
  const colColor = COLUMN_COLORS[column.color || "gray"] || COLUMN_COLORS.gray;
  const isDropTarget = dragOverColumn === column.id && draggedCard !== null;
  const colTopBorder = BOARD_TOP_BORDER[column.color || "gray"] || BOARD_TOP_BORDER.gray;

  let cards = Array.isArray(column.cards) ? column.cards : [];
  cards = cards.filter(c => showArchived ? c.is_archived : !c.is_archived);
  if (filterAssignee) cards = cards.filter(c => c.assignee === filterAssignee);
  if (filterDue === "overdue") cards = cards.filter(c => c.due_date && new Date(c.due_date) < new Date());
  if (filterDue === "soon") cards = cards.filter(c => c.due_date && new Date(c.due_date) <= new Date(Date.now() + 3 * 24 * 60 * 60 * 1000));
  const normalizedSearch = searchQuery.trim().toLowerCase();
  if (normalizedSearch) {
    cards = cards.filter(c => {
      const leadName = c.lead?.business_name || leads.find(l => l.id === c.lead_id)?.business_name || "";
      return [c.title, c.description || "", c.assignee || "", leadName]
        .some(v => v.toLowerCase().includes(normalizedSearch));
    });
  }

  return (
    <div
      data-board-column-id={column.id}
      className={`w-72 shrink-0 rounded-xl flex flex-col transition-all ${colColor.bg} ${colTopBorder} ${isDropTarget ? "ring-2 ring-neutral-300 dark:ring-neutral-600 ring-inset shadow-lg" : ""}`}
      onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; onDragOver(column.id); }}
      onDragLeave={onDragLeave}
      onDrop={event => {
        event.preventDefault();
        event.stopPropagation();
        onDrop(column.id, event);
      }}
    >
      <div className={`p-3 border-b ${colColor.border} flex items-center justify-between`}>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${colColor.border.replace("border-", "bg-").split(" ")[0]}`} />
          <h3 className={`font-semibold text-sm ${colColor.text}`}>{column.name}</h3>
          <span className="text-xs text-neutral-400 bg-white/60 dark:bg-black/20 px-1.5 py-0.5 rounded-full">{cards.length}</span>
        </div>
        <div className="flex items-center gap-0.5">
          <button onClick={() => onEditColumn(column)} className="p-1 text-neutral-400 hover:text-neutral-500 rounded text-xs">Ubah</button>
          <button onClick={() => onDeleteColumn(column.id, column.name)} className="p-1 text-neutral-400 hover:text-red-500 rounded">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>
      </div>

      <div className={`flex-1 overflow-y-auto p-2 space-y-2 min-h-[80px] transition-colors ${isDropTarget ? "bg-neutral-50/50 dark:bg-neutral-900/20" : ""}`}>
        {cards.map(card => (
          <BoardCardItem
            key={card.id}
            card={card}
            leads={leads}
            draggedCardId={draggedCard?.card.id ?? null}
            showArchived={showArchived}
            onDragStart={c => {
              onDragStart(c, column.id);
            }}
            onDragEnd={onDragEnd}
            onPointerDragOver={columnId => columnId ? onDragOver(columnId) : onDragLeave()}
            onPointerDrop={toColumnId => onDrop(toColumnId)}
            onOpenEdit={c => onOpenEditCard(c, column.id)}
          />
        ))}

        {isDropTarget && (
          <div className="h-12 rounded-xl border-2 border-dashed border-neutral-300 dark:border-neutral-600 bg-neutral-50/50 dark:bg-neutral-900/20 flex items-center justify-center">
            <span className="text-xs text-neutral-500 dark:text-neutral-400">Lepas di sini</span>
          </div>
        )}

        {!showArchived && (
          <button onClick={() => onOpenNewCard(column.id)}
            className="w-full p-2 text-sm text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-white/60 dark:hover:bg-black/20 rounded-xl flex items-center justify-center gap-1 transition-colors">
            <Plus className="w-4 h-4" /> Tambah Card
          </button>
        )}
      </div>
    </div>
  );
}
