"use client";

import { X } from "lucide-react";

interface TemplateForm {
  name: string;
  type: string;
  html_template: string;
  variables: string;
}

const TYPES = [
  { value: "invoice", label: "Invoice" },
  { value: "receipt", label: "Receipt / Bukti Pembayaran" },
  { value: "proposal_pdf", label: "Proposal PDF" },
  { value: "surat_penawaran", label: "Surat Penawaran" },
  { value: "kontrak", label: "Kontrak / MoU" },
  { value: "custom", label: "Custom" },
];

interface TemplateModalProps {
  open: boolean;
  editing: any | null;
  form: TemplateForm;
  onChange: (f: TemplateForm) => void;
  onTypeChange: (type: string) => void;
  onSave: () => void;
  onClose: () => void;
  onResetToStarter: () => void;
  starterTemplates: Record<string, string>;
  saving: boolean;
}

export function TemplateModal({
  open, editing, form, onChange, onTypeChange, onSave, onClose, onResetToStarter, starterTemplates, saving
}: TemplateModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-neutral-900 rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-xl">
        <div className="flex items-center justify-between p-5 border-b border-[var(--border-default)]">
          <h3 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">{editing ? "Edit Template" : "Buat Template"}</h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-lg"><X size={18} /></button>
        </div>
        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Nama Template</label>
              <input type="text" value={form.name} onChange={e => onChange({ ...form, name: e.target.value })}
                className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" />
            </div>
            <div>
              <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Type</label>
              <select value={form.type} onChange={e => onTypeChange(e.target.value)}
                className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800">
                {TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Variables (comma-separated)</label>
            <input type="text" value={form.variables} onChange={e => onChange({ ...form, variables: e.target.value })}
              placeholder="klien, tanggal, total, items_rows"
              className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 font-mono" />
          </div>
          <div>
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">HTML Template</label>
              {starterTemplates[form.type] && (
                <button type="button" onClick={onResetToStarter}
                  className="text-[11px] text-amber-600 hover:text-amber-700 font-semibold">Reset ke Starter Template</button>
              )}
            </div>
            <textarea value={form.html_template} onChange={e => onChange({ ...form, html_template: e.target.value })}
              rows={16}
              className="mt-1 w-full px-3 py-2 text-xs border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 font-mono resize-y" />
          </div>
        </div>
        <div className="flex justify-end gap-3 p-5 border-t border-[var(--border-default)]">
          <button onClick={onClose} className="px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-lg">Batal</button>
          <button onClick={onSave} disabled={saving || !form.name.trim() || !form.html_template.trim()}
            className="px-4 py-2 text-sm font-bold bg-amber-500 hover:bg-amber-600 text-white rounded-lg disabled:opacity-50">
            {saving ? "Menyimpan..." : "Simpan"}
          </button>
        </div>
      </div>
    </div>
  );
}

export { TYPES };