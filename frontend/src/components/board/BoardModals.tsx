"use client";
import { Modal } from "./SharedModal";
import { COLUMN_COLORS } from "./types";

const COLORS = {
  primary: "bg-amber-500 hover:bg-amber-600 text-white",
  secondary: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700",
};

interface ColumnModalProps {
  open: boolean;
  column: any;
  columnName: string;
  setColumnName: (s: string) => void;
  columnColor: string;
  setColumnColor: (c: string) => void;
  onCreate: () => void;
  onUpdate: () => void;
  onClose: () => void;
}

export function ColumnModal({ open, column, columnName, setColumnName, columnColor, setColumnColor, onCreate, onUpdate, onClose }: ColumnModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={column ? "Edit Kolom" : "Kolom Baru"}>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Nama Kolom</label>
          <input type="text" value={columnName} onChange={e => setColumnName(e.target.value)}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
            placeholder="e.g., In Progress" />
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
        <button onClick={() => column ? onUpdate() : onCreate()} disabled={!columnName.trim()}
          className={`w-full px-4 py-2 text-sm rounded-xl font-medium ${COLORS.primary} disabled:opacity-50`}>
          {column ? "Update Kolom" : "Buat Kolom"}
        </button>
      </div>
    </Modal>
  );
}

interface ProjectModalProps {
  open: boolean;
  form: any;
  setForm: (f: any) => void;
  leads: any[];
  saving: boolean;
  onCreate: () => void;
  onClose: () => void;
}

export function ProjectModal({ open, form, setForm, leads, saving, onCreate, onClose }: ProjectModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="Buat Proyek Baru">
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Nama Proyek</label>
          <input type="text" value={form.name} onChange={e => setForm((p: any) => ({ ...p, name: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none"
            placeholder="Nama proyek..." />
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Tipe</label>
          <select value={form.type} onChange={e => setForm((p: any) => ({ ...p, type: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm">
            <option value="FIXED">Fixed</option>
            <option value="RETAINER">Retainer</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Client (opsional)</label>
          <select value={form.lead_id ?? ""} onChange={e => setForm((p: any) => ({ ...p, lead_id: e.target.value ? Number(e.target.value) : null }))}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm">
            <option value="">— Tanpa client —</option>
            {leads.map((l: any) => <option key={l.id} value={l.id}>{l.business_name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">Warna Proyek</label>
          <div className="flex gap-2 flex-wrap">
            {Object.keys(COLUMN_COLORS).map(color => (
              <button key={color} type="button" title={color} onClick={() => setForm((p: any) => ({ ...p, color }))}
                className={`w-8 h-8 rounded-xl ${COLUMN_COLORS[color].bg} border-2 transition-all ${form.color === color ? "border-neutral-900 dark:border-white scale-110" : `${COLUMN_COLORS[color].border} hover:scale-105`}`} />
            ))}
          </div>
        </div>
        <button onClick={onCreate} disabled={saving || !form.name.trim()}
          className={`w-full px-4 py-2 text-sm rounded-xl font-medium ${COLORS.primary} disabled:opacity-50`}>
          {saving ? "Membuat..." : "Buat Proyek"}
        </button>
      </div>
    </Modal>
  );
}

interface EditProjectModalProps {
  open: boolean;
  form: any;
  setForm: (f: any) => void;
  leads: any[];
  saving: boolean;
  onSave: () => void;
  onClose: () => void;
}

export function EditProjectModal({ open, form, setForm, leads, saving, onSave, onClose }: EditProjectModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="Edit Proyek">
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Nama Proyek</label>
          <input type="text" value={form.name} onChange={e => setForm((p: any) => ({ ...p, name: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Tipe</label>
          <select value={form.type} onChange={e => setForm((p: any) => ({ ...p, type: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm">
            <option value="FIXED">Fixed</option>
            <option value="RETAINER">Retainer</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Client (opsional)</label>
          <select value={form.lead_id ?? ""} onChange={e => setForm((p: any) => ({ ...p, lead_id: e.target.value ? Number(e.target.value) : null }))}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm">
            <option value="">— Tanpa client —</option>
            {leads.map((l: any) => <option key={l.id} value={l.id}>{l.business_name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">Warna</label>
          <div className="flex gap-2 flex-wrap">
            {Object.keys(COLUMN_COLORS).map(color => (
              <button key={color} type="button" onClick={() => setForm((p: any) => ({ ...p, color }))}
                className={`w-8 h-8 rounded-xl ${COLUMN_COLORS[color].bg} border-2 transition-all ${form.color === color ? "border-neutral-900 dark:border-white scale-110" : `${COLUMN_COLORS[color].border} hover:scale-105`}`} />
            ))}
          </div>
        </div>
        <button onClick={onSave} disabled={saving || !form.name.trim()}
          className={`w-full px-4 py-2 text-sm rounded-xl font-medium ${COLORS.primary} disabled:opacity-50`}>
          {saving ? "Menyimpan..." : "Simpan Perubahan"}
        </button>
      </div>
    </Modal>
  );
}