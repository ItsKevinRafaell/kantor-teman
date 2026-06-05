"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";

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

function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
      <div className="relative bg-white dark:bg-[var(--bg-canvas)] rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 bg-white dark:bg-[var(--bg-canvas)] px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between rounded-t-2xl">
          <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-50">{title}</h2>
          <button onClick={onClose} className="p-1 text-neutral-400 hover:text-neutral-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">{children}</div>
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
}

interface DocFormProps {
  form: DocFormState;
  onChange: (f: DocFormState) => void;
  folders: DocumentFolder[];
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
}

export function DocForm({ form, onChange, folders, onSave, onCancel, saving }: DocFormProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Judul *</label>
        <input autoFocus value={form.title} onChange={e => onChange({ ...form, title: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
          placeholder="Judul dokumen..." />
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Link Eksternal</label>
        <input value={form.url} onChange={e => onChange({ ...form, url: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
          placeholder="https://..." />
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Catatan / Body</label>
        <textarea value={form.body} onChange={e => onChange({ ...form, body: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none resize-none" rows={4}
          placeholder="Tulis catatan di sini..." />
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Tags</label>
        <input value={form.tags} onChange={e => onChange({ ...form, tags: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
          placeholder="seo, panduan, internal (pisah dengan koma)" />
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Folder</label>
        <select value={form.folder_id} onChange={e => onChange({ ...form, folder_id: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none">
          <option value="">— Tanpa Folder —</option>
          {folders.map(f => <option key={f.id} value={f.id}>{f.parent_id ? `-- ${f.name}` : f.name}</option>)}
        </select>
      </div>
      <div className="flex justify-end gap-2 pt-1">
        <button onClick={onCancel} className="px-4 py-2 text-sm rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">Batal</button>
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
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
          placeholder="Nama folder..." onKeyDown={e => e.key === "Enter" && onSave()} />
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Parent Folder</label>
        <select value={form.parent_id} onChange={e => onChange({ ...form, parent_id: e.target.value })}
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none">
          <option value="">— Folder Utama —</option>
          {folders.filter(f => f.id !== editingId).map(f => <option key={f.id} value={f.id}>{f.parent_id ? `-- ${f.name}` : f.name}</option>)}
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
        <button onClick={onCancel} className="px-4 py-2 text-sm rounded-xl bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">Batal</button>
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