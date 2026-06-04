"use client";

import { useState } from "react";

interface Template { id: string; name: string; content: string; category_id: string | null; }
interface Lead { id: number; business_name: string; product_interest: string | null; }

interface WaPreviewModalProps {
  lead: Lead | null;
  open: boolean;
  message: string;
  templates: Template[];
  onClose: () => void;
  onMessageChange: (msg: string) => void;
  onSend: () => void;
  onSelectTemplate: (template: Template) => void;
}

export default function WaPreviewModal({ lead, open, message, templates, onClose, onMessageChange, onSend, onSelectTemplate }: WaPreviewModalProps) {
  if (!open || !lead) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 w-full max-w-md p-6 space-y-4">
        <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Chat WA: {lead.business_name}</h3>
        {templates.length > 0 && (
          <div>
            <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Pilih Template</label>
            <select onChange={(e) => {
              const t = templates.find(t => t.id === e.target.value);
              if (t) onSelectTemplate(t);
            }} className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200 outline-none focus:ring-1 focus:ring-green-300">
              <option value="">— Pilih template lain —</option>
              {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
        )}
        <div>
          <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Pesan</label>
          <textarea value={message} onChange={(e) => onMessageChange(e.target.value)}
            rows={7} className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200 outline-none focus:ring-1 focus:ring-green-300 resize-none" />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
          <button onClick={onSend} className="px-4 py-2 text-xs font-bold bg-green-500 hover:bg-green-600 text-white rounded-xl transition-colors">Kirim via WA</button>
        </div>
      </div>
    </div>
  );
}