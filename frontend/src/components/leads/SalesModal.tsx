"use client";

import { useState } from "react";

interface SalesModalProps {
  lead: { id: number; business_name: string } | null;
  open: boolean;
  onClose: () => void;
  onSave: (data: { sales_owner: string; next_action_at: string; loss_reason: string; do_not_contact: boolean }) => void;
}

export default function SalesModal({ lead, open, onClose, onSave }: SalesModalProps) {
  const [form, setForm] = useState({ sales_owner: "", next_action_at: "", loss_reason: "", do_not_contact: false });

  if (!open || !lead) return null;

  function handleSave() {
    onSave({
      ...form,
      next_action_at: form.next_action_at ? new Date(form.next_action_at).toISOString() : "",
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 w-full max-w-md p-6 space-y-4">
        <div>
          <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Tindak Lanjut Sales</h3>
          <p className="text-xs text-gray-400 mt-1">{lead.business_name}</p>
        </div>
        <div>
          <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">PIC Sales</label>
          <input value={form.sales_owner} onChange={e => setForm(p => ({ ...p, sales_owner: e.target.value }))}
            className="w-full text-sm px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200" placeholder="Nama sales..." />
        </div>
        <div>
          <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Next Action</label>
          <input type="datetime-local" value={form.next_action_at} onChange={e => setForm(p => ({ ...p, next_action_at: e.target.value }))}
            className="w-full text-sm px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200" />
        </div>
        <div>
          <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Alasan Lost / Catatan</label>
          <textarea value={form.loss_reason} onChange={e => setForm(p => ({ ...p, loss_reason: e.target.value }))}
            rows={3} className="w-full text-sm px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200 resize-none" placeholder="Isi bila lead tidak dilanjutkan..." />
        </div>
        <label className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-300">
          <input type="checkbox" checked={form.do_not_contact} onChange={e => setForm(p => ({ ...p, do_not_contact: e.target.checked }))} />
          Jangan hubungi lagi nomor ini
        </label>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 rounded-xl">Batal</button>
          <button onClick={handleSave} className="px-4 py-2 text-xs font-bold bg-amber-500 hover:bg-amber-600 text-white rounded-xl">Simpan</button>
        </div>
      </div>
    </div>
  );
}