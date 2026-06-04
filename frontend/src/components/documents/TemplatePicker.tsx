"use client";
import { ChevronRight } from "lucide-react";

export default function TemplatePicker({ templates, selectedTemplate, selectTemplate, setStep }: any) {
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Pilih Template</h2>
      {templates.length === 0 && <p className="text-sm text-gray-400">Belum ada template. Buat di halaman Templates dulu.</p>}
      {templates.map((t: any) => (
        <button key={t.id} onClick={() => selectTemplate(t)}
          className={`w-full text-left p-4 rounded-xl border-2 transition-colors ${selectedTemplate?.id === t.id
            ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20"
            : "border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300"}`}>
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
        <button onClick={() => setStep(1)} disabled={!selectedTemplate}
          className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl disabled:opacity-50">
          Lanjut <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}