"use client";

import { useState } from "react";
import { Upload, X } from "lucide-react";

interface DocumentFolder {
  id: string;
  name: string;
  parent_id: string | null;
  color: string;
  created_at: string;
}

const FOLDER_COLORS = [
  { hex: "#6B7280", label: "Gray" },
  { hex: "#3B82F6", label: "Blue" },
  { hex: "#22C55E", label: "Green" },
  { hex: "#EAB308", label: "Yellow" },
  { hex: "#EF4444", label: "Red" },
  { hex: "#A855F7", label: "Purple" },
];

function Modal({
  open,
  onClose,
  title,
  children,
  size = "md",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: "md" | "lg" | "xl";
}) {
  if (!open) return null;
  const width =
    size === "xl" ? "max-w-4xl" : size === "lg" ? "max-w-2xl" : "max-w-lg";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
      <div
        className={`relative flex max-h-[90vh] w-full ${width} flex-col overflow-hidden rounded-2xl border border-amber-100 bg-white shadow-2xl dark:border-amber-900/40 dark:bg-[var(--bg-surface)]`}
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex shrink-0 items-center justify-between rounded-t-2xl border-b border-amber-100 bg-white px-6 py-4 dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
          <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-50">{title}</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-neutral-400 transition-colors hover:bg-amber-50 hover:text-amber-700 dark:hover:bg-amber-950/20">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-6">{children}</div>
      </div>
    </div>
  );
}

// ─── Doc Form ───────────────────────────────────────────────────────────────

interface DocFormState {
  title: string;
  body: string;
  url: string;
  tags: string;
  folder_id: string;
  lead_id: string;
}

interface ClientOption {
  lead_id: number;
  business_name: string;
}

interface DocFormProps {
  form: DocFormState;
  onChange: (f: DocFormState) => void;
  folders: DocumentFolder[];
  clients?: ClientOption[];
  attachmentFile: File | null;
  onFileChange: (file: File | null) => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
}

function folderOptionLabel(folders: DocumentFolder[], folder: DocumentFolder): string {
  const parts: string[] = [folder.name];
  let current = folder.parent_id ? folders.find(f => f.id === folder.parent_id) : null;
  const seen = new Set<string>([folder.id]);
  while (current && !seen.has(current.id)) {
    parts.unshift(current.name);
    seen.add(current.id);
    current = current.parent_id ? folders.find(f => f.id === current!.parent_id) : null;
  }
  return parts.join(" / ");
}

export function DocForm({ form, onChange, folders, clients = [], attachmentFile, onFileChange, onSave, onCancel, saving }: DocFormProps) {
  const sortedFolders = [...folders].sort((a, b) => folderOptionLabel(folders, a).localeCompare(folderOptionLabel(folders, b), "id"));
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Judul *</label>
        <input autoFocus value={form.title} onChange={e => onChange({ ...form, title: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-neutral-800/70 border-0 rounded-xl text-sm focus:ring-2 focus:ring-amber-300 outline-none"
          placeholder="Judul dokumen..." />
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Link Eksternal</label>
        <input value={form.url} onChange={e => onChange({ ...form, url: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-neutral-800/70 border-0 rounded-xl text-sm focus:ring-2 focus:ring-amber-300 outline-none"
          placeholder="https://..." />
        <p className="mt-1 text-[11px] text-neutral-400">Opsional. Kalau upload file dipilih, link dokumen akan otomatis memakai file tersebut.</p>
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Upload File</label>
        <label className="flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-amber-100 bg-amber-50/40 px-3 py-2 text-sm transition-colors hover:bg-amber-50 dark:border-amber-900/40 dark:bg-amber-950/10 dark:hover:bg-amber-950/20">
          <span className="flex min-w-0 items-center gap-2 text-neutral-600 dark:text-neutral-300">
            <Upload className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-300" />
            <span className="truncate">{attachmentFile ? attachmentFile.name : "Pilih file PDF, gambar, dokumen, atau spreadsheet"}</span>
          </span>
          <span className="shrink-0 text-xs font-semibold text-amber-700 dark:text-amber-300">Pilih</span>
          <input
            type="file"
            className="hidden"
            accept=".jpg,.jpeg,.png,.pdf,.webp,.doc,.docx,.xls,.xlsx,.csv,.txt"
            onChange={e => onFileChange(e.target.files?.[0] || null)}
          />
        </label>
        {attachmentFile && (
          <button type="button" onClick={() => onFileChange(null)} className="mt-1 text-[11px] font-semibold text-neutral-400 hover:text-red-500">
            Hapus file terpilih
          </button>
        )}
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Catatan / Body</label>
        <textarea value={form.body} onChange={e => onChange({ ...form, body: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-neutral-800/70 border-0 rounded-xl text-sm focus:ring-2 focus:ring-amber-300 outline-none resize-none" rows={4}
          placeholder="Tulis catatan di sini..." />
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Tags</label>
        <input value={form.tags} onChange={e => onChange({ ...form, tags: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-neutral-800/70 border-0 rounded-xl text-sm focus:ring-2 focus:ring-amber-300 outline-none"
          placeholder="seo, panduan, internal (pisah dengan koma)" />
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Folder</label>
        <select value={form.folder_id} onChange={e => onChange({ ...form, folder_id: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-neutral-800/70 border-0 rounded-xl text-sm focus:ring-2 focus:ring-amber-300 outline-none">
          <option value="">— Tanpa Folder —</option>
          {sortedFolders.map(f => (
            <option key={f.id} value={f.id}>{folderOptionLabel(folders, f)}</option>
          ))}
        </select>
        <p className="mt-1 text-[11px] text-neutral-400">Folder = organisasi arsip. Password/API key simpan di tab Kredensial klien, bukan di sini.</p>
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Terkait klien</label>
        <select value={form.lead_id} onChange={e => onChange({ ...form, lead_id: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-neutral-800/70 border-0 rounded-xl text-sm focus:ring-2 focus:ring-amber-300 outline-none">
          <option value="">— Tidak ditautkan —</option>
          {clients.map(c => (
            <option key={c.lead_id} value={String(c.lead_id)}>{c.business_name}</option>
          ))}
        </select>
        <p className="mt-1 text-[11px] text-neutral-400">Opsional. Dokumen terkait muncul di hub detail klien.</p>
      </div>
      <div className="flex justify-end gap-2 pt-1">
        <button onClick={onCancel} className="px-4 py-2 text-sm rounded-xl bg-gray-100 dark:bg-neutral-800/70 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">Batal</button>
        <button onClick={onSave} disabled={saving || !form.title.trim()}
          className="px-4 py-2 text-sm rounded-xl font-semibold bg-amber-500 hover:bg-amber-600 text-white transition-colors disabled:opacity-50">
          {saving ? "Menyimpan..." : "Simpan"}
        </button>
      </div>
    </div>
  );
}

// ─── Folder Form ─────────────────────────────────────────────────────────────

interface FolderFormState {
  name: string;
  color: string;
  parent_id: string;
}

interface FolderFormProps {
  form: FolderFormState;
  onChange: (f: FolderFormState) => void;
  folders: DocumentFolder[];
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
  editingId?: string | null;
}

export function FolderForm({ form, onChange, folders, onSave, onCancel, saving, editingId }: FolderFormProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Nama Folder</label>
        <input autoFocus value={form.name} onChange={e => onChange({ ...form, name: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-neutral-800/70 border-0 rounded-xl text-sm focus:ring-2 focus:ring-amber-300 outline-none"
          placeholder="Nama folder..." onKeyDown={e => e.key === "Enter" && onSave()} />
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Parent Folder</label>
        <select value={form.parent_id} onChange={e => onChange({ ...form, parent_id: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-neutral-800/70 border-0 rounded-xl text-sm focus:ring-2 focus:ring-amber-300 outline-none">
          <option value="">— Folder Utama —</option>
          {folders.filter(f => f.id !== editingId).map(f => (
            <option key={f.id} value={f.id}>{folderOptionLabel(folders, f)}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">Warna</label>
        <div className="flex gap-2 flex-wrap">
          {FOLDER_COLORS.map(c => (
            <button key={c.hex} type="button" title={c.label} onClick={() => onChange({ ...form, color: c.hex })}
              className={`w-8 h-8 rounded-full transition-all border-2 ${form.color === c.hex ? "border-neutral-800 dark:border-white scale-110" : "border-transparent hover:scale-105"}`}
              style={{ backgroundColor: c.hex }} />
          ))}
        </div>
      </div>
      <div className="flex justify-end gap-2 pt-1">
        <button onClick={onCancel} className="px-4 py-2 text-sm rounded-xl bg-gray-100 dark:bg-neutral-800/70 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">Batal</button>
        <button onClick={onSave} disabled={saving || !form.name.trim()}
          className="px-4 py-2 text-sm rounded-xl font-semibold bg-amber-500 hover:bg-amber-600 text-white transition-colors disabled:opacity-50">
          {saving ? "Menyimpan..." : "Simpan"}
        </button>
      </div>
    </div>
  );
}

// ─── Export modals ───────────────────────────────────────────────────────────

export { Modal };
