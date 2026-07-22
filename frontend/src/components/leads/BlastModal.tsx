"use client";
import NativeSelect from "../ui/NativeSelect";

import { useState } from "react";

interface Category { id: string; name: string }
interface Template { id: string; name: string; content: string; category_id: string | null }

interface BlastModalProps {
  open: boolean;
  batches: string[];
  categories: Category[];
  templates: Template[];
  blastBatch: string;
  blastCategoryId: string;
  blastMinRating: number;
  blastTemplateId: string;
  blastSendMode: "instant" | "scheduled";
  blastScheduledFor: string;
  leadCount: number;
  onClose: () => void;
  onBatchChange: (batch: string) => void;
  onCategoryChange: (id: string) => void;
  onMinRatingChange: (rating: number) => void;
  onTemplateChange: (id: string) => void;
  onSendModeChange: (mode: "instant" | "scheduled") => void;
  onScheduledForChange: (dt: string) => void;
  onStart: () => void;
  blasting: boolean;
}

export default function BlastModal({
  open, batches, categories, templates,
  blastBatch, blastCategoryId, blastMinRating, blastTemplateId,
  blastSendMode, blastScheduledFor, leadCount,
  onClose, onBatchChange, onCategoryChange, onMinRatingChange,
  onTemplateChange, onSendModeChange, onScheduledForChange, onStart, blasting
}: BlastModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 w-full max-w-md p-5 space-y-3 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-gray-900 dark:text-gray-100">Eksekusi WA Blast</h3>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>

        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-2.5">
          <p className="text-sm font-semibold text-amber-700 dark:text-amber-300">
            Target: {leadCount} Leads akan menerima pesan.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Batch</label>
            <NativeSelect value={blastBatch} onChange={onBatchChange} placeholder="Pilih batch" searchPlaceholder="Cari batch…" options={batches.filter(Boolean).map((b: string) => ({ value: b, label: b }))} />
          </div>
          <div>
            <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Kategori</label>
            <NativeSelect value={blastCategoryId} onChange={v => { onCategoryChange(v); onTemplateChange(""); }} placeholder="Kategori" options={categories.map((c: any) => ({ value: String(c.id), label: c.name }))} />
          </div>
          <div>
            <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Min. Rating</label>
            <NativeSelect value={String(blastMinRating)} onChange={v => onMinRatingChange(Number(v || 0))} clearable={false} options={[{value:"0",label:"Semua rating"},{value:"4",label:"Min 4★"},{value:"5",label:"5★"}]} />
          </div>
          <div>
            <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Template</label>
            <NativeSelect value={blastTemplateId} onChange={onTemplateChange} placeholder="Template" options={templates.map((t: any) => ({ value: t.id, label: t.name }))} />
          </div>
        </div>

        {templates.length === 0 && (
          <p className="text-[11px] text-amber-500">Belum ada template WA Blast. <a href="/master/templates" className="underline">Buat di Master Data</a>.</p>
        )}

        <p className="text-xs text-gray-400">Hanya lead Scraped tanpa opt-out yang masuk antrean. Delay 5 detik antar pesan.</p>

        <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
          <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Waktu Pengiriman</label>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="radio" checked={blastSendMode === "instant"} onChange={() => onSendModeChange("instant")}
                className="w-4 h-4 text-amber-600 focus:ring-amber-500" />
              <span className="text-sm text-neutral-700 dark:text-neutral-300">Kirim Sekarang</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="radio" checked={blastSendMode === "scheduled"} onChange={() => onSendModeChange("scheduled")}
                className="w-4 h-4 text-amber-600 focus:ring-amber-500" />
              <span className="text-sm text-neutral-700 dark:text-neutral-300">Jadwalkan</span>
            </label>
          </div>
          {blastSendMode === "scheduled" && (
            <div className="mt-2">
              <input type="datetime-local" value={blastScheduledFor} onChange={e => onScheduledForChange(e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
          <button onClick={onStart} disabled={blasting || !blastTemplateId}
            className="px-4 py-2 text-sm font-semibold bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-xl transition-all disabled:opacity-50">
            {blasting ? "Mengirim..." : "Mulai Kirim Blast"}
          </button>
        </div>
      </div>
    </div>
  );
}