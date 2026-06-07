"use client";

import { useState } from "react";
import { apiFetch } from "../../lib/api";
import { formatRupiah } from "../../utils/formatter";
import type { Contact, ProjectData } from "../../types";

interface ClientsTableRowProps {
  contact: Contact;
  projects: ProjectData[];
  contactLeadId?: number;
  index: number;
  isAdmin: boolean;
  onDetail: (c: Contact) => void;
  onNotes: (c: Contact) => void;
  onProject: (contactId: number) => void;
  onProposal: (c: Contact) => void;
  onEdit: (c: Contact) => void;
  onDelete: (c: Contact) => void;
}

export default function ClientsTableRow({
  contact,
  projects,
  contactLeadId,
  index,
  isAdmin,
  onDetail,
  onNotes,
  onProject,
  onProposal,
  onEdit,
  onDelete,
}: ClientsTableRowProps) {
  const clientProjects = projects.filter(p => contactLeadId != null ? p.lead_id === contactLeadId : false);
  const activeProjects = clientProjects.filter(p => p.status === "ACTIVE");
  const totalValue = activeProjects.reduce((sum, p) => sum + p.nominal, 0);
  const nearestEnd = activeProjects.filter(p => p.end_date).sort((a, b) => (a.end_date || "").localeCompare(b.end_date || ""))[0];
  const daysLeft = nearestEnd?.end_date ? Math.ceil((new Date(nearestEnd.end_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24)) : null;
  const totalDays = nearestEnd?.start_date && nearestEnd?.end_date ? Math.ceil((new Date(nearestEnd.end_date).getTime() - new Date(nearestEnd.start_date).getTime()) / (1000 * 60 * 60 * 24)) : null;
  const progress = totalDays && daysLeft !== null ? Math.max(0, Math.min(100, ((totalDays - daysLeft) / totalDays) * 100)) : 0;

  return (
    <tr className="hover:bg-[var(--bg-surface-hover)] transition-colors">
      <td className="px-4 py-3 text-gray-400 text-xs">{index + 1}</td>
      <td className="px-4 py-3 font-semibold text-neutral-800 dark:text-neutral-200">
        <a href={`/dashboard/clients/${contact.id}`} className="hover:text-brand-yellow transition-colors">{contact.business_name}</a>
      </td>
      <td className="px-4 py-3">
        <span className="text-gray-700 dark:text-gray-300">{contact.owner_name || <span className="text-gray-300 dark:text-gray-600 italic">—</span>}</span>
      </td>
      <td className="px-4 py-3 font-mono text-gray-600 dark:text-gray-400 text-xs whitespace-nowrap">
        <a href={`https://wa.me/${contact.phone_number}`} target="_blank" rel="noopener noreferrer" className="text-green-600 hover:underline">+{contact.phone_number}</a>
      </td>
      <td className="px-4 py-3 max-w-[280px]">
        <div className="flex items-center gap-1.5 flex-nowrap">
          {activeProjects.length > 0 ? (
            <>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-semibold whitespace-nowrap overflow-hidden text-ellipsis max-w-[200px] ${activeProjects[0].type === "RETAINER" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"}`} title={`${activeProjects[0].type === "RETAINER" ? "Retainer" : "Fixed"}: ${activeProjects[0].name}`}>
                {activeProjects[0].name}
              </span>
              {activeProjects.length > 1 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300 whitespace-nowrap cursor-default" title={activeProjects.slice(1).map(p => p.name).join("\n")}>
                  +{activeProjects.length - 1}
                </span>
              )}
            </>
          ) : (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500 whitespace-nowrap">Idle</span>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        {activeProjects.length > 0 ? (
          <div>
            <span className="text-xs font-bold text-neutral-800 dark:text-neutral-200">{formatRupiah(totalValue)}</span>
            <p className="text-[10px] text-gray-400">{activeProjects[0]?.type === "RETAINER" ? "/bulan (MRR)" : "Total (TCV)"}</p>
          </div>
        ) : <span className="text-gray-300 dark:text-gray-600 text-xs">—</span>}
      </td>
      <td className="px-4 py-3 min-w-[120px]">
        {daysLeft !== null ? (
          <div>
            <div className="w-full h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden mb-1">
              <div className={`h-full rounded-full transition-all ${daysLeft <= 7 ? "bg-red-500" : daysLeft <= 14 ? "bg-amber-500" : "bg-emerald-500"}`} style={{ width: `${progress}%` }} />
            </div>
            <span className={`text-[10px] font-semibold ${daysLeft <= 7 ? "text-red-600 dark:text-red-400" : daysLeft <= 14 ? "text-amber-600 dark:text-amber-400" : "text-neutral-500 dark:text-neutral-400"}`}>
              {daysLeft <= 0 ? "Expired" : daysLeft <= 7 ? `${daysLeft}d — Need Renewal` : `${daysLeft} hari lagi`}
            </span>
          </div>
        ) : <span className="text-gray-300 dark:text-gray-600 text-xs">—</span>}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5">
          <a href={`/dashboard/clients/${contact.id}`}
            className="inline-flex items-center gap-1 px-2 py-1.5 text-gray-500 hover:text-brand-yellow hover:bg-brand-yellow/10 text-xs font-medium rounded-lg transition-colors whitespace-nowrap">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg> Detail
          </a>
          <button onClick={() => onNotes(contact)}
            className="inline-flex items-center gap-1 px-2 py-1.5 text-gray-500 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 text-xs font-medium rounded-lg transition-colors whitespace-nowrap">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg> Notes
          </button>
          <button onClick={() => onProject(contact.id)}
            className="inline-flex items-center gap-1 px-2 py-1.5 text-gray-500 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 text-xs font-medium rounded-lg transition-colors whitespace-nowrap">
            + Project
          </button>
          <button onClick={() => onProposal(contact)}
            className="inline-flex items-center gap-1 px-2 py-1.5 bg-brand-yellow/10 hover:bg-brand-yellow/20 text-brand-yellow text-xs font-semibold rounded-lg transition-colors whitespace-nowrap">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg> Proposal
          </button>
          {isAdmin && <button onClick={() => onEdit(contact)}
            className="p-1.5 text-gray-400 hover:text-brand-yellow hover:bg-brand-yellow/10 rounded-lg transition-colors">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
          </button>}
          {isAdmin && <button onClick={() => onDelete(contact)}
            className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14H6L5 6" /><path d="M10 11v6" /><path d="M14 11v6" /><path d="M9 6V4h6v2" /></svg>
          </button>}
        </div>
      </td>
    </tr>
  );
}