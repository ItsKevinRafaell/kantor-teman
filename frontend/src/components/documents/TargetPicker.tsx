"use client";

import { Search } from "lucide-react";

interface Lead { id: number; business_name: string; phone_number: string; product_interest: string | null; }
interface Contact { id: number; business_name: string; owner_name: string | null; phone_number: string; purchased_product: string | null; }
interface Project { id: string; lead_id: number | null; name: string; nominal: number; service_type: string | null; }

type TargetType = "empty" | "lead" | "contact" | "project";

interface Props {
  targetType: TargetType;
  targetSearch: string;
  leads: Lead[];
  contacts: Contact[];
  projects: Project[];
  selectedLead: Lead | null;
  selectedContact: Contact | null;
  selectedProject: Project | null;
  onTargetTypeChange: (t: TargetType) => void;
  onSearchChange: (s: string) => void;
  onPickLead: (l: Lead) => void;
  onPickContact: (c: Contact) => void;
  onPickProject: (p: Project) => void;
}

export function TargetPicker({
  targetType, targetSearch, leads, contacts, projects,
  selectedLead, selectedContact, selectedProject,
  onTargetTypeChange, onSearchChange, onPickLead, onPickContact, onPickProject
}: Props) {
  const filteredLeads = leads.filter(l => l.business_name.toLowerCase().includes(targetSearch.toLowerCase()));
  const filteredContacts = contacts.filter(c => c.business_name.toLowerCase().includes(targetSearch.toLowerCase()));
  const filteredProjects = projects.filter(p => p.name.toLowerCase().includes(targetSearch.toLowerCase()));

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Pilih Target (opsional)</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {(["empty", "lead", "contact", "project"] as const).map(type => (
          <button key={type} onClick={() => onTargetTypeChange(type)}
            className={`flex-1 p-3 rounded-xl border-2 text-sm font-semibold transition-colors ${targetType === type ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20 text-amber-700" : "border-[var(--border-default)] text-gray-600 hover:border-amber-300"}`}>
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
              onChange={e => onSearchChange(e.target.value)}
              placeholder={`Cari ${targetType === "lead" ? "lead" : targetType === "project" ? "proyek" : "klien"}...`}
              className="w-full pl-10 pr-3 py-2.5 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-800"
            />
          </div>

          {targetType === "lead" && (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {filteredLeads.length === 0 && <p className="text-sm text-gray-400 text-center py-4">Tidak ada lead.</p>}
              {filteredLeads.map(l => (
                <button key={l.id} onClick={() => onPickLead(l)}
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
              {filteredContacts.map(c => (
                <button key={c.id} onClick={() => onPickContact(c)}
                  className={`w-full text-left p-3 rounded-xl border transition-colors ${selectedContact?.id === c.id ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20" : "border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300"}`}>
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{c.business_name}</p>
                  <p className="text-xs text-gray-500">{c.owner_name || "—"} · {c.phone_number}</p>
                </button>
              ))}
            </div>
          )}

          {targetType === "project" && (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {filteredProjects.length === 0 && <p className="text-sm text-gray-400 text-center py-4">Tidak ada proyek.</p>}
              {filteredProjects.map(p => (
                <button key={p.id} onClick={() => onPickProject(p)}
                  className={`w-full text-left p-3 rounded-xl border transition-colors ${selectedProject?.id === p.id ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20" : "border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300"}`}>
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{p.name}</p>
                  <p className="text-xs text-gray-500">{p.service_type || "—"} · Rp {(p.nominal || 0).toLocaleString()}</p>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}