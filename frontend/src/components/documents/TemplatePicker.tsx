"use client";

import { Check, ChevronRight } from "lucide-react";

interface DocTemplate { id: string; name: string; type: string; variables: string[]; }

interface Props {
  templates: DocTemplate[];
  selectedTemplate: DocTemplate | null;
  onSelect: (t: DocTemplate) => void;
  onNext: () => void;
}

const STEPS = ["Pilih Template", "Pilih Target", "Isi Variabel", "Preview", "Selesai"];

export function TemplateStepper({ step }: { step: number }) {
  return (
    <div className="flex items-center gap-1">
      {STEPS.map((s, i) => (
        <div key={i} className="flex items-center gap-1">
          <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold transition-colors ${i < step ? "bg-green-500 text-white" : i === step ? "bg-amber-500 text-white" : "bg-gray-200 dark:bg-neutral-700 text-gray-500"}`}>
            {i < step ? <Check size={12} /> : i + 1}
          </div>
          <span className={`text-xs font-medium hidden sm:block ${i === step ? "text-amber-600" : "text-gray-400"}`}>{s}</span>
          {i < STEPS.length - 1 && <div className="w-4 h-px bg-gray-200 dark:bg-neutral-700 mx-1" />}
        </div>
      ))}
    </div>
  );
}

export function TemplatePicker({ templates, selectedTemplate, onSelect, onNext }: Props) {
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Pilih Template</h2>
      {templates.length === 0 && <p className="text-sm text-gray-400">Belum ada template. Buat di halaman Templates dulu.</p>}
      {templates.map(t => (
        <button key={t.id} onClick={() => onSelect(t)}
          className={`w-full text-left p-4 rounded-xl border-2 transition-colors ${selectedTemplate?.id === t.id ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20" : "border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300"}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{t.name}</p>
              <p className="text-xs text-gray-500 mt-0.5">Variabel: {t.variables.join(", ") || "—"}</p>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 font-bold uppercase">{t.type}</span>
          </div>
        </button>
      ))}
      <div className="flex justify-end pt-2">
        <button onClick={onNext} disabled={!selectedTemplate}
          className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl disabled:opacity-50">
          Lanjut <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}