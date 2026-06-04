"use client";

import { useState, useEffect } from "react";
import { Search, Plus, Trash2, Save } from "lucide-react";

interface Props {
  fields: Record<string, string>;
  onChange: (key: string, value: string) => void;
  templateName: string;
}

const FIELD_HINTS: Record<string, string> = {
  klien: "Nama klien / bisnis penerima dokumen",
  nama: "Nama lengkap penerima",
  alamat: "Alamat lengkap klien",
  phone: "Contoh: 0812-3456-7890",
  email: "Contoh: klien@email.com",
  layanan: "Jenis layanan yang diberikan (mis. Pembuatan Website, SEO Bulanan)",
  pertaining: "Topik / judul surat",
  scope: "Rincian pekerjaan yang dikerjakan",
  terms: "Syarat & ketentuan",
  durasi: "Lama kontrak berlaku",
  nilai_kontrak: "Nilai total kontrak dalam Rupiah",
  tanggal_mulai: "Tanggal kontrak mulai berlaku",
  tanggal_akhir: "Tanggal kontrak berakhir",
  valid_until: "Batas akhir penawaran berlaku",
  due_date: "Tanggal jatuh tempo pembayaran",
  payment_info: "Rekening atau metode pembayaran",
  catatan: "Catatan tambahan",
  keterangan: "Keterangan pembayaran",
};

const FIELD_LABELS: Record<string, string> = {
  klien: "Nama Klien",
  layanan: "Layanan",
  items_rows: "Rincian Layanan",
  scope: "Lingkup Pekerjaan",
  terms: "Syarat dan Ketentuan",
  payment_info: "Informasi Pembayaran",
  payment_method: "Metode Pembayaran",
  nilai_kontrak: "Nilai Kontrak",
  tanggal_mulai: "Tanggal Mulai",
  tanggal_akhir: "Tanggal Selesai",
};

export function VariableInputForm({ fields, onChange, templateName }: Props) {
  const [savedValues, setSavedValues] = useState<Record<string, string[]>>({});
  const [showSuggestions, setShowSuggestions] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const saved: Record<string, string[]> = {};
    for (const key of Object.keys(fields)) {
      try {
        const stored = localStorage.getItem(`kt_field_templates_${key}`);
        if (stored) saved[key] = JSON.parse(stored);
      } catch {}
    }
    setSavedValues(saved);
  }, []);

  function handleSaveTemplate(key: string) {
    const value = fields[key]?.trim();
    if (!value) return;
    const existing = savedValues[key] || [];
    if (existing.includes(value)) return;
    const updated = [value, ...existing].slice(0, 10);
    localStorage.setItem(`kt_field_templates_${key}`, JSON.stringify(updated));
    setSavedValues(prev => ({ ...prev, [key]: updated }));
  }

  function getLabel(key: string): string {
    return FIELD_LABELS[key] || key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  }

  function getHint(key: string): string {
    return FIELD_HINTS[key] || `Masukkan nilai untuk ${key}`;
  }

  function isTextareaKey(key: string): boolean {
    const textareaPatterns = ["scope", "terms", "alamat", "catatan", "keterangan", "deskripsi", "description", "catatan"];
    return textareaPatterns.some(p => key.includes(p)) || key.length > 20;
  }

  function isDateKey(key: string): boolean {
    const datePatterns = ["tanggal", "date", "due", "expired", "mulai", "akhir", "valid"];
    return datePatterns.some(p => key.includes(p));
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-bold text-neutral-700 dark:text-neutral-200 mb-4">
        Isi Variabel untuk: <span className="text-amber-600">{templateName}</span>
      </h3>

      {Object.entries(fields).map(([key, value]) => (
        <div key={key} className="space-y-1">
          <label className="block text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
            {getLabel(key)}
          </label>
          <div className="relative">
            {isTextareaKey(key) ? (
              <textarea
                value={value}
                onChange={e => onChange(key, e.target.value)}
                placeholder={getHint(key)}
                rows={4}
                className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-amber-400 outline-none resize-none"
              />
            ) : isDateKey(key) ? (
              <input
                type="date"
                value={value}
                onChange={e => onChange(key, e.target.value)}
                className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-amber-400 outline-none"
              />
            ) : (
              <input
                type="text"
                value={value}
                onChange={e => onChange(key, e.target.value)}
                placeholder={getHint(key)}
                className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl text-sm focus:ring-2 focus:ring-amber-400 outline-none"
              />
            )}
            <button
              type="button"
              onClick={() => handleSaveTemplate(key)}
              title="Simpan sebagai template"
              className="absolute right-2 top-2 p-1.5 text-neutral-400 hover:text-amber-500 transition-colors"
            >
              <Save className="w-4 h-4" />
            </button>
          </div>

          {/* Saved values dropdown */}
          {savedValues[key]?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {savedValues[key].map((saved, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onChange(key, saved)}
                  className="text-xs px-2 py-1 bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 rounded-lg hover:bg-amber-100 transition-colors"
                >
                  {saved}
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}