"use client";
import { formatRupiah } from "../../utils/formatter";
import { Search, ChevronRight, ChevronLeft } from "lucide-react";

export default function GeneratorSteps({ currentStep: step, setStep, selectedTemplate, targetType, setTargetType, leads, contacts, projects, filteredLeads, filteredContacts, filteredProjects, targetSearch, setTargetSearch, selectedLead, selectedContact, selectedProject, pickLead, pickContact, pickProject, fetchAndApplyDefaults }: any) {
  return (
    <div className="space-y-4">
      <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Pilih Target (opsional)</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {(["empty", "lead", "contact", "project"] as const).map(type => (
          <button key={type} onClick={() => {
            setTargetType(type);
            if (type === "empty") {
              // Clear selections
            }
          }}
            className={`flex-1 p-3 rounded-xl border-2 text-sm font-semibold transition-colors ${targetType === type
              ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20 text-amber-700"
              : "border-[var(--border-default)] text-gray-600 hover:border-amber-300"}`}>
            {type === "empty" ? "Tanpa Target" : type === "lead" ? "Dari Lead" : type === "contact" ? "Dari Klien" : "Dari Proyek"}
          </button>
        ))}
      </div>

      {(targetType === "lead" || targetType === "contact" || targetType === "project") && (
        <>
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={targetSearch}
              onChange={e => setTargetSearch(e.target.value)}
              placeholder={`Cari ${targetType === "lead" ? "lead" : targetType === "project" ? "proyek" : "klien"} berdasarkan nama atau layanan...`}
              className="w-full pl-10 pr-3 py-2.5 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-800"
            />
          </div>

          {targetType === "lead" && (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {filteredLeads.length === 0 && <p className="text-sm text-gray-400 text-center py-4">Tidak ada lead.</p>}
              {filteredLeads.map((l: any) => (
                <button key={l.id} onClick={() => pickLead(l)}
                  className={`w-full text-left p-3 rounded-xl border transition-colors ${selectedLead?.id === l.id ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20" : "border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300"}`}>
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{l.business_name}</p>
                  <p className="text-xs text-gray-500">{l.product_interest || "—"} · {l.phone_number}</p>
                </button>
              ))}
            </div>
          )}

          {targetType === "contact" && (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {filteredContacts.length === 0 && <p className="text-sm text-gray-400 text-center py-4">Tidak ada klien.</p>}
              {filteredContacts.map((c: any) => (
                <button key={c.id} onClick={() => pickContact(c)}
                  className={`w-full text-left p-3 rounded-xl border transition-colors ${selectedContact?.id === c.id ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20" : "border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300"}`}>
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{c.business_name}</p>
                  <p className="text-xs text-gray-500">{c.purchased_product || "—"} · {c.phone_number}</p>
                </button>
              ))}
            </div>
          )}

          {targetType === "project" && (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {filteredProjects.length === 0 && <p className="text-sm text-gray-400 text-center py-4">Tidak ada proyek.</p>}
              {filteredProjects.map((project: any) => (
                <button key={project.id} onClick={() => pickProject(project)}
                  className={`w-full text-left p-3 rounded-xl border transition-colors ${selectedProject?.id === project.id ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20" : "border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300"}`}>
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{project.name}</p>
                  <p className="text-xs text-gray-500">{project.service_type || "Layanan umum"} · {formatRupiah(project.nominal || 0)}</p>
                </button>
              ))}
            </div>
          )}
        </>
      )}

      <div className="flex justify-between pt-2">
        <button onClick={() => setStep(0)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-xl">
          <ChevronLeft size={16} /> Kembali
        </button>
        <button onClick={() => {
            if (selectedTemplate) {
              const ttype = selectedProject ? "project" : selectedLead ? "lead" : selectedContact ? "contact" : "empty";
              const tid = selectedProject?.id ?? selectedLead?.id ?? selectedContact?.id ?? null;
              fetchAndApplyDefaults(selectedTemplate, ttype, tid);
            }
            setStep(2);
          }}
          className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl">
          Lanjut <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}