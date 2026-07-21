"use client";
import { useMemo } from "react";
import { Modal } from "./SharedModal";
import { SearchableSelect } from "../ui/SearchableSelect";

const COLORS = {
  primary: "bg-amber-500 hover:bg-amber-600 text-white",
  secondary: "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700",
};

function leadOptions(leads: any[]) {
  return (leads || []).map((l: any) => ({
    value: String(l.id),
    label: l.business_name || `Lead #${l.id}`,
    sub: [l.phone_number, l.status, l.product_interest].filter(Boolean).join(" · "),
  }));
}

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

export function ColumnModal({ open, column, columnName, setColumnName, onCreate, onUpdate, onClose }: ColumnModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={column ? "Edit Kolom" : "Kolom Baru"}>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Nama Kolom</label>
          <input type="text" value={columnName} onChange={e => setColumnName(e.target.value)}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-amber-300 dark:focus:ring-amber-700 outline-none"
            placeholder="Contoh: Sedang Dikerjakan" />
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
  const options = useMemo(() => leadOptions(leads), [leads]);
  return (
    <Modal open={open} onClose={onClose} title="Buat Proyek Baru">
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Nama Proyek</label>
          <input type="text" value={form.name} onChange={e => setForm((p: any) => ({ ...p, name: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none"
            placeholder="Nama proyek..." />
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Tipe proyek</label>
          <select value={form.type} onChange={e => setForm((p: any) => ({ ...p, type: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm">
            <option value="FIXED">Fixed</option>
            <option value="RETAINER">Retainer</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Klien (opsional)</label>
          <SearchableSelect
            options={options}
            value={form.lead_id != null ? String(form.lead_id) : ""}
            onChange={(v) => setForm((p: any) => ({ ...p, lead_id: v ? Number(v) : null }))}
            placeholder="Cari klien / prospek…"
            searchPlaceholder="Ketik nama, telepon, status…"
            maxDisplay={80}
          />
          <p className="mt-1 text-[11px] text-neutral-400">Ketik untuk filter — cocok kalau daftar panjang.</p>
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
  const options = useMemo(() => leadOptions(leads), [leads]);
  return (
    <Modal open={open} onClose={onClose} title="Edit Proyek">
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Nama Proyek</label>
          <input type="text" value={form.name} onChange={e => setForm((p: any) => ({ ...p, name: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none" />
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Tipe proyek</label>
          <select value={form.type} onChange={e => setForm((p: any) => ({ ...p, type: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm">
            <option value="FIXED">Fixed</option>
            <option value="RETAINER">Retainer</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">Klien (opsional)</label>
          <SearchableSelect
            options={options}
            value={form.lead_id != null ? String(form.lead_id) : ""}
            onChange={(v) => setForm((p: any) => ({ ...p, lead_id: v ? Number(v) : null }))}
            placeholder="Cari klien / prospek…"
            searchPlaceholder="Ketik nama, telepon, status…"
            maxDisplay={80}
          />
        </div>
        <button onClick={onSave} disabled={saving || !form.name.trim()}
          className={`w-full px-4 py-2 text-sm rounded-xl font-medium ${COLORS.primary} disabled:opacity-50`}>
          {saving ? "Menyimpan..." : "Simpan Perubahan"}
        </button>
      </div>
    </Modal>
  );
}
