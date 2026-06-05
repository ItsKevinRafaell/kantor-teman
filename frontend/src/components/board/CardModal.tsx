"use client";
import { Trash2, Archive, ArchiveRestore, User, CheckSquare, MessageSquare } from "lucide-react";
import { Modal } from "./SharedModal";
import { LABEL_COLORS, CARD_COLORS } from "./types";

const COLORS = {
  primary: "bg-amber-500 hover:bg-amber-600 text-white",
};

interface CardModalProps {
  open: boolean;
  card: any;
  columnId: string;
  cardForm: any;
  setCardForm: (f: any) => void;
  saving: boolean;
  currentProject: any;
  currentProjectLead: any;
  leads: any[];
  onCreateCard: () => void;
  onUpdateCard: () => void;
  onArchiveCard: () => void;
  onDeleteCard: () => void;
  onToggleLabel: (label: string) => void;
  onClose: () => void;
  onAddChecklist: (text: string) => void;
  onToggleChecklist: (itemId: string, isDone: boolean) => void;
  onAddComment: (content: string) => void;
  formatDateTime: (d: string) => string;
}

export function CardModal({
  open, card, cardForm, setCardForm, saving, currentProject, currentProjectLead, leads,
  onCreateCard, onUpdateCard, onArchiveCard, onDeleteCard, onToggleLabel, onClose,
  onAddChecklist, onToggleChecklist, onAddComment, formatDateTime,
}: CardModalProps) {
  function toggleLabel(label: string) {
    setCardForm((prev: any) => ({
      ...prev,
      labels: prev.labels.includes(label) ? prev.labels.filter((l: string) => l !== label) : [...prev.labels, label],
    }));
  }

  return (
    <Modal open={open} onClose={onClose} title={card ? "Edit Card" : "Card Baru"} size="lg">
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">
            Judul {card?.is_workspace_linked && <span className="ml-1 text-[10px] text-gray-400 normal-case">(read-only — diatur dari Workspace)</span>}
          </label>
          <input type="text" value={cardForm.title} onChange={e => setCardForm((p: any) => ({ ...p, title: e.target.value }))}
            readOnly={card?.is_workspace_linked}
            className={`w-full px-3 py-2 border-0 rounded-xl text-sm outline-none ${card?.is_workspace_linked ? "bg-gray-50 dark:bg-gray-900 text-gray-500 cursor-not-allowed" : "bg-gray-100 dark:bg-gray-800 focus:ring-2 focus:ring-yellow-400"}`}
            placeholder="Judul card..." />
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Deskripsi</label>
          <textarea value={cardForm.description} onChange={e => setCardForm((p: any) => ({ ...p, description: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none resize-none" rows={3}
            placeholder="Deskripsi..." />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Assignee</label>
            <input type="text" value={cardForm.assignee} onChange={e => setCardForm((p: any) => ({ ...p, assignee: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
              placeholder="Nama assignee..." />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Due Date</label>
            <input type="date" value={cardForm.due_date} onChange={e => setCardForm((p: any) => ({ ...p, due_date: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
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
              <button key={color} type="button" title={color} onClick={() => setCardForm((p: any) => ({ ...p, color }))}
                className={`w-8 h-8 rounded-xl ${CARD_COLORS[color].bg} ${CARD_COLORS[color].accent} transition-all ${cardForm.color === color ? "ring-2 ring-offset-1 ring-neutral-700 dark:ring-white scale-110" : "hover:scale-105"}`} />
            ))}
          </div>
        </div>
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
              <select value={cardForm.lead_id ?? ""} onChange={e => setCardForm((p: any) => ({ ...p, lead_id: e.target.value ? Number(e.target.value) : null }))}
                className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm">
                <option value="">— Tanpa client —</option>
                {leads.map((l: any) => <option key={l.id} value={l.id}>{l.business_name}</option>)}
              </select>
            )}
          </div>
        )}
        <div className="flex gap-2 pt-2">
          <button onClick={() => card ? onUpdateCard() : onCreateCard()} disabled={saving || !cardForm.title.trim()}
            className={`flex-1 px-4 py-2 text-sm rounded-xl font-medium ${COLORS.primary} disabled:opacity-50`}>
            {saving ? "Menyimpan..." : card ? "Simpan Perubahan" : "Buat Card"}
          </button>
          {card && (
            <>
              <button onClick={onArchiveCard}
                className={`px-3 py-2 text-sm rounded-xl ${card.is_archived ? "bg-green-100 text-green-600 hover:bg-green-200" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                title={card.is_archived ? "Pulihkan" : "Arsipkan"}>
                {card.is_archived ? <ArchiveRestore className="w-4 h-4" /> : <Archive className="w-4 h-4" />}
              </button>
              <button onClick={onDeleteCard} className="px-3 py-2 text-sm rounded-xl bg-red-100 text-red-600 hover:bg-red-200" title="Hapus">
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
        {card && (
          <>
            <hr className="border-gray-200 dark:border-gray-700 my-2" />
            <ChecklistSection card={card} onAdd={onAddChecklist} onToggle={onToggleChecklist} formatDateTime={formatDateTime} />
            <CommentsSection card={card} onAdd={onAddComment} formatDateTime={formatDateTime} />
          </>
        )}
      </div>
    </Modal>
  );
}

function ChecklistSection({ card, onAdd, onToggle, formatDateTime }: { card: any; onAdd: (text: string) => void; onToggle: (id: string, done: boolean) => void; formatDateTime: (d: string) => string }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 flex items-center gap-2">
        <CheckSquare className="w-4 h-4 text-amber-500" /> Checklist
        {(card.checklist?.length || 0) > 0 && <span className="text-xs text-neutral-400">{card.checklist.filter((i: any) => i.is_done).length}/{card.checklist.length}</span>}
      </h4>
      {(card.checklist?.length || 0) > 0 && (
        <div className="mb-2 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div className="h-full bg-yellow-400 rounded-full transition-all" style={{ width: `${(card.checklist.filter((i: any) => i.is_done).length / card.checklist.length) * 100}%` }} />
        </div>
      )}
      <div className="space-y-1.5 mb-2">
        {card.checklist?.map((item: any) => (
          <label key={item.id} className="flex items-center gap-2 text-sm cursor-pointer group">
            <input type="checkbox" checked={item.is_done} onChange={e => onToggle(item.id, e.target.checked)} className="rounded accent-amber-500" />
            <span className={`transition-all ${item.is_done ? "line-through text-neutral-400" : "text-neutral-700 dark:text-neutral-300"}`}>{item.text}</span>
          </label>
        ))}
      </div>
      <input type="text" placeholder="+ Tambah item checklist, Enter untuk simpan"
        className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
        onKeyDown={e => { if (e.key === "Enter") { onAdd((e.target as HTMLInputElement).value); (e.target as HTMLInputElement).value = ""; } }} />
    </div>
  );
}

function CommentsSection({ card, onAdd, formatDateTime }: { card: any; onAdd: (content: string) => void; formatDateTime: (d: string) => string }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 flex items-center gap-2">
        <MessageSquare className="w-4 h-4 text-blue-500" /> Komentar
        {(card.comments?.length || 0) > 0 && <span className="text-xs text-neutral-400">{card.comments.length}</span>}
      </h4>
      <div className="space-y-2 mb-2 max-h-36 overflow-y-auto">
        {card.comments?.map((c: any) => (
          <div key={c.id} className="bg-gray-100 dark:bg-gray-800 rounded-xl p-2.5 text-sm">
            <p className="text-neutral-800 dark:text-neutral-200">{c.content}</p>
            <p className="text-xs text-neutral-400 mt-1">{c.author} · {formatDateTime(c.created_at)}</p>
          </div>
        ))}
      </div>
      <input type="text" placeholder="Tulis komentar, Enter untuk kirim"
        className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
        onKeyDown={e => { if (e.key === "Enter") { onAdd((e.target as HTMLInputElement).value); (e.target as HTMLInputElement).value = ""; } }} />
    </div>
  );
}
