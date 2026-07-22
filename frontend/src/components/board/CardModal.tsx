"use client";
import { useMemo, useRef } from "react";
import { Trash2, Archive, ArchiveRestore, User, CheckSquare, MessageSquare, History, Paperclip, Upload } from "lucide-react";
import { Modal } from "./SharedModal";
import { SearchableSelect } from "../ui/SearchableSelect";
import { LABEL_COLORS } from "./types";
import type { BoardUser } from "./types";

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
  users: BoardUser[];
  onCreateCard: () => void;
  onUpdateCard: () => void;
  onArchiveCard: () => void;
  onDeleteCard: () => void;
  onToggleLabel: (label: string) => void;
  onClose: () => void;
  onAddChecklist: (text: string) => void;
  onToggleChecklist: (itemId: string, isDone: boolean) => void;
  onAddComment: (content: string) => void;
  onUploadAttachment: (file: File) => void;
  formatDateTime: (d: string) => string;
}

export function CardModal({
  open, card, cardForm, setCardForm, saving, currentProject, currentProjectLead, leads, users,
  onCreateCard, onUpdateCard, onArchiveCard, onDeleteCard, onToggleLabel, onClose,
  onAddChecklist, onToggleChecklist, onAddComment, onUploadAttachment, formatDateTime,
}: CardModalProps) {
  function toggleLabel(label: string) {
    setCardForm((prev: any) => ({
      ...prev,
      labels: prev.labels.includes(label) ? prev.labels.filter((l: string) => l !== label) : [...prev.labels, label],
    }));
  }

  return (
    <Modal open={open} onClose={onClose} title={card ? "Ubah Card" : "Card Baru"} size="lg">
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">
            Judul {card?.is_workspace_linked && <span className="ml-1 text-[10px] text-gray-400 normal-case">(hanya dibaca, diatur dari Workspace)</span>}
          </label>
          <input type="text" value={cardForm.title} onChange={e => setCardForm((p: any) => ({ ...p, title: e.target.value }))}
            readOnly={card?.is_workspace_linked}
            className={`w-full px-3 py-2 border-0 rounded-xl text-sm outline-none ${card?.is_workspace_linked ? "bg-gray-50 dark:bg-gray-900 text-gray-500 cursor-not-allowed" : "bg-gray-100 dark:bg-gray-800 focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600"}`}
            placeholder="Judul card..." />
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Deskripsi</label>
          <textarea value={cardForm.description} onChange={e => setCardForm((p: any) => ({ ...p, description: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none resize-none" rows={3}
            placeholder="Deskripsi..." />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">PIC</label>
            <input type="text" value={cardForm.assignee || ""} onChange={e => setCardForm((p: any) => ({ ...p, assignee: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none"
              placeholder="Nama PIC..." list="kt-assignee-suggestions" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Deadline</label>
            <input type="date" value={cardForm.due_date} onChange={e => setCardForm((p: any) => ({ ...p, due_date: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none" />
          </div>
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">Label</label>
          <div className="flex gap-2 flex-wrap">
            {Object.keys(LABEL_COLORS).map(label => (
              <button key={label} type="button" title={label} onClick={() => toggleLabel(label)}
                className={`h-6 w-10 rounded-md ${LABEL_COLORS[label]} transition-all ${cardForm.labels.includes(label) ? "ring-2 ring-offset-2 ring-neutral-700 dark:ring-white" : "opacity-40 hover:opacity-70"}`} />
            ))}
          </div>
        </div>
        {currentProject && (
          <div>
            <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Klien</label>
            {currentProject.lead_id ? (
              <div className="px-3 py-2 bg-neutral-100 dark:bg-neutral-800 rounded-xl text-sm flex items-center gap-2">
                <User className="w-4 h-4 text-neutral-500" />
                <span className="font-medium text-neutral-700 dark:text-neutral-300">{currentProjectLead?.business_name || "Klien tidak ditemukan"}</span>
                <span className="text-neutral-400 text-xs">(dari proyek)</span>
              </div>
            ) : (
              <SearchableSelect
                options={(leads || []).map((l: any) => ({
                  value: String(l.id),
                  label: l.business_name || `Lead #${l.id}`,
                  sub: [l.phone_number, l.status].filter(Boolean).join(" · "),
                }))}
                value={cardForm.lead_id != null ? String(cardForm.lead_id) : ""}
                onChange={(v) => setCardForm((p: any) => ({ ...p, lead_id: v ? Number(v) : null }))}
                placeholder="Cari klien…"
                searchPlaceholder="Nama / telepon…"
                maxDisplay={80}
              />
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
                className={`px-3 py-2 text-sm rounded-xl ${card.is_archived ? "bg-neutral-200 text-neutral-600 hover:bg-neutral-300" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
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
            <AttachmentsSection card={card} onUpload={onUploadAttachment} formatDateTime={formatDateTime} />
            <ChecklistSection card={card} onAdd={onAddChecklist} onToggle={onToggleChecklist} formatDateTime={formatDateTime} />
            <CommentsSection card={card} onAdd={onAddComment} formatDateTime={formatDateTime} />
            <ActivitySection card={card} formatDateTime={formatDateTime} />
          </>
        )}
      </div>
    </Modal>
  );
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function AttachmentsSection({ card, onUpload, formatDateTime }: { card: any; onUpload: (file: File) => void; formatDateTime: (d: string) => string }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const attachments = [...(card.attachments || [])].sort((a: any, b: any) => new Date(b.uploaded_at || 0).getTime() - new Date(a.uploaded_at || 0).getTime());
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h4 className="flex items-center gap-2 text-sm font-semibold text-neutral-700 dark:text-neutral-300">
          <Paperclip className="w-4 h-4 text-neutral-500" /> File
          {attachments.length > 0 && <span className="text-xs text-neutral-400">{attachments.length}</span>}
        </h4>
        <button type="button" onClick={() => inputRef.current?.click()}
          className="inline-flex items-center gap-1 rounded-lg bg-amber-50 px-2.5 py-1.5 text-xs font-semibold text-amber-700 hover:bg-amber-100 dark:bg-amber-950/20 dark:text-amber-300">
          <Upload className="h-3.5 w-3.5" /> Upload
        </button>
        <input ref={inputRef} type="file" className="hidden"
          onChange={e => {
            const file = e.target.files?.[0];
            if (file) onUpload(file);
            e.currentTarget.value = "";
          }} />
      </div>
      {attachments.length === 0 ? (
        <p className="text-xs text-neutral-400">Belum ada file di card ini.</p>
      ) : (
        <div className="space-y-2">
          {attachments.map((att: any) => (
            <a key={att.id} href={`${API_BASE}${att.file_path}`} target="_blank" rel="noopener noreferrer"
              className="block rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm hover:border-amber-200 hover:bg-amber-50/40 dark:border-neutral-700 dark:bg-neutral-900 dark:hover:border-amber-900/60 dark:hover:bg-amber-950/10">
              <span className="block truncate font-medium text-neutral-700 dark:text-neutral-200">{att.file_name}</span>
              <span className="mt-0.5 block text-xs text-neutral-400">{att.uploaded_by || "Admin"} · {formatDateTime(att.uploaded_at)}</span>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

function ChecklistSection({ card, onAdd, onToggle, formatDateTime }: { card: any; onAdd: (text: string) => void; onToggle: (id: string, done: boolean) => void; formatDateTime: (d: string) => string }) {
  const checklist = [...(card.checklist || [])].sort((a: any, b: any) => (b.position ?? 0) - (a.position ?? 0));
  return (
    <div>
      <h4 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 flex items-center gap-2">
        <CheckSquare className="w-4 h-4 text-neutral-500" /> Checklist
        {(card.checklist?.length || 0) > 0 && <span className="text-xs text-neutral-400">{(card.checklist || []).filter((i: any) => i.is_done).length}/{card.checklist.length}</span>}
      </h4>
      {(card.checklist?.length || 0) > 0 && (
        <div className="mb-2 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div className="h-full bg-amber-400 dark:bg-amber-600 rounded-full transition-all" style={{ width: `${((card.checklist || []).filter((i: any) => i.is_done).length / card.checklist.length) * 100}%` }} />
        </div>
      )}
      <div className="space-y-1.5 mb-2">
        {checklist.map((item: any) => (
          <label key={item.id} className="flex items-center gap-2 text-sm cursor-pointer group">
            <input type="checkbox" checked={item.is_done} onChange={e => onToggle(item.id, e.target.checked)} className="rounded accent-amber-500" />
            <span className={`transition-all ${item.is_done ? "line-through text-neutral-400" : "text-neutral-700 dark:text-neutral-300"}`}>{item.text}</span>
          </label>
        ))}
      </div>
      <input type="text" placeholder="+ Tambah item checklist, Enter untuk simpan"
        className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none"
        onKeyDown={e => { if (e.key === "Enter") { onAdd((e.target as HTMLInputElement).value); (e.target as HTMLInputElement).value = ""; } }} />
    </div>
  );
}

function CommentsSection({ card, onAdd, formatDateTime }: { card: any; onAdd: (content: string) => void; formatDateTime: (d: string) => string }) {
  const comments = [...(card.comments || [])].sort((a: any, b: any) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
  return (
    <div>
      <h4 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 flex items-center gap-2">
        <MessageSquare className="w-4 h-4 text-neutral-500" /> Komentar
        {(card.comments?.length || 0) > 0 && <span className="text-xs text-neutral-400">{card.comments.length}</span>}
      </h4>
      <div className="space-y-2 mb-2 max-h-36 overflow-y-auto">
        {comments.map((c: any) => (
          <div key={c.id} className="bg-gray-100 dark:bg-gray-800 rounded-xl p-2.5 text-sm">
            <p className="text-neutral-800 dark:text-neutral-200">{c.content}</p>
            <p className="text-xs text-neutral-400 mt-1">{c.author} · {formatDateTime(c.created_at)}</p>
          </div>
        ))}
      </div>
      <input type="text" placeholder="Tulis komentar, Enter untuk kirim"
        className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none"
        onKeyDown={e => { if (e.key === "Enter") { onAdd((e.target as HTMLInputElement).value); (e.target as HTMLInputElement).value = ""; } }} />
    </div>
  );
}

function ActivitySection({ card, formatDateTime }: { card: any; formatDateTime: (d: string) => string }) {
  const activity = [...(card.activity || [])].sort((a: any, b: any) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
  return (
    <div>
      <h4 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2 flex items-center gap-2">
        <History className="w-4 h-4 text-amber-500" /> Log Aktivitas
        {activity.length > 0 && <span className="text-xs text-neutral-400">{activity.length}</span>}
      </h4>
      {activity.length === 0 ? (
        <p className="text-xs text-neutral-400">Belum ada aktivitas di card ini.</p>
      ) : (
        <div className="space-y-2 max-h-36 overflow-y-auto">
          {activity.map((a: any) => (
            <div key={a.id} className="rounded-xl border border-amber-100 bg-amber-50/40 p-2.5 text-sm dark:border-amber-900/50 dark:bg-amber-950/10">
              <p className="text-neutral-700 dark:text-neutral-200">{a.description || a.action}</p>
              <p className="mt-1 text-xs text-neutral-400">{a.actor || "Sistem"} · {formatDateTime(a.created_at)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
