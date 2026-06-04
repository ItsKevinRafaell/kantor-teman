"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../lib/api";
import type { Contact, ProjectData, TimelinePhase, ProposalRecord } from "../../types";

interface ClientDetailModalProps {
  contact: Contact | null;
  open: boolean;
  onClose: () => void;
  onCopyLink: (id: string) => void;
}

export default function ClientDetailModal({ contact, open, onClose, onCopyLink }: ClientDetailModalProps) {
  const [tab, setTab] = useState<"profil" | "aktivitas" | "proposal">("profil");
  const [proposals, setProposals] = useState<ProposalRecord[]>([]);
  const [timeline, setTimeline] = useState<{ type: string; icon: string; label: string; timestamp: string }[]>([]);
  const [loadingProposals, setLoadingProposals] = useState(false);
  const [loadingTimeline, setLoadingTimeline] = useState(false);

  useEffect(() => {
    if (!open || !contact) return;
    setTab("profil");
    setTimeline([]);
    setLoadingProposals(true);
    setLoadingTimeline(true);

    apiFetch(`/api/proposals/client/${contact.id}?source=contact`)
      .then(r => r.ok ? r.json() : [])
      .then(setProposals)
      .catch(() => setProposals([]))
      .finally(() => setLoadingProposals(false));

    apiFetch(`/api/clients/${contact.id}/activity-timeline`)
      .then(r => r.ok ? r.json() : [])
      .then(setTimeline)
      .catch(() => {})
      .finally(() => setLoadingTimeline(false));
  }, [open, contact]);

  if (!open || !contact) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-2xl max-h-[80vh] flex flex-col outline-none">
        <div className="px-6 py-4 border-b border-[var(--border-default)]">
          <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Detail Klien — {contact.business_name}</h3>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-[var(--border-default)] px-6">
          {(["profil", "aktivitas", "proposal"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-xs font-semibold uppercase tracking-wide border-b-2 transition-colors ${
                tab === t ? "border-brand-yellow text-brand-yellow" : "border-transparent text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              }`}>
              {t === "profil" ? "Profil Klien" : t === "aktivitas" ? "Riwayat Aktivitas" : "Riwayat Proposal"}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {tab === "profil" && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div><p className="text-xs text-gray-400 uppercase tracking-wide">Nama Bisnis</p><p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{contact.business_name}</p></div>
                <div><p className="text-xs text-gray-400 uppercase tracking-wide">Owner</p><p className="text-sm text-gray-700 dark:text-gray-300">{contact.owner_name || "—"}</p></div>
                <div><p className="text-xs text-gray-400 uppercase tracking-wide">Nomor WA</p><p className="text-sm font-mono text-gray-700 dark:text-gray-300">+{contact.phone_number}</p></div>
                <div><p className="text-xs text-gray-400 uppercase tracking-wide">Produk</p><p className="text-sm text-gray-700 dark:text-gray-300">{contact.purchased_product || "—"}</p></div>
              </div>
              {contact.notes && (
                <div><p className="text-xs text-gray-400 uppercase tracking-wide">Catatan</p><p className="text-sm text-gray-600 dark:text-neutral-400 mt-1">{contact.notes}</p></div>
              )}
            </div>
          )}

          {tab === "aktivitas" && (
            <div>
              {loadingTimeline ? (
                <div className="text-center py-8 text-gray-400 text-sm animate-pulse">Memuat aktivitas...</div>
              ) : timeline.length === 0 ? (
                <div className="text-center py-8 text-gray-400 text-sm">Belum ada aktivitas tercatat.</div>
              ) : (
                <div className="space-y-2">
                  {timeline.map((ev, i) => (
                    <div key={i} className="flex items-start gap-3 px-3 py-2.5 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-100 dark:border-neutral-700">
                      <span className="text-base shrink-0">{ev.icon}</span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-neutral-800 dark:text-neutral-200">{ev.label}</p>
                        <p className="text-[10px] text-neutral-400 mt-0.5">{ev.timestamp ? new Date(ev.timestamp).toLocaleString("id-ID") : "—"}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "proposal" && (
            <div>
              {loadingProposals ? (
                <div className="text-center py-8 text-gray-400 text-sm animate-pulse">Memuat proposal...</div>
              ) : proposals.length === 0 ? (
                <div className="text-center py-8 text-gray-400 text-sm">Belum ada proposal untuk klien ini.</div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-[var(--border-default)]">
                  <table className="w-full text-sm">
                    <thead className="bg-neutral-50 dark:bg-neutral-800">
                      <tr>
                        {["Tanggal", "Layanan", "Harga", "Status", "Aksi"].map((h) => (
                          <th key={h} className="text-left px-3 py-2 text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-subtle)]">
                      {proposals.map((p) => (
                        <tr key={p.id} className="hover:bg-[var(--bg-surface-hover)]">
                          <td className="px-3 py-2 text-xs text-gray-500">{p.created_at ? new Date(p.created_at).toLocaleDateString("id-ID") : "—"}</td>
                          <td className="px-3 py-2 text-xs font-medium text-neutral-800 dark:text-neutral-200">{p.services_detail.map((s) => s.name).join(", ")}</td>
                          <td className="px-3 py-2 text-xs text-gray-600 dark:text-gray-400">Rp {p.total_price.toLocaleString("id-ID")}</td>
                          <td className="px-3 py-2"><span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${p.status === "Accepted" ? "bg-green-100 text-green-700" : p.status === "Rejected" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>{p.status}</span></td>
                          <td className="px-3 py-2">
                            <button onClick={() => onCopyLink(p.id)} className="inline-flex items-center gap-1 text-xs text-brand-yellow hover:underline">
                              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /></svg> Link
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="px-6 py-3 border-t border-[var(--border-default)] flex justify-end">
          <button onClick={onClose}
            className="px-4 py-2 text-sm font-semibold text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">
            Tutup
          </button>
        </div>
      </div>
    </div>
  );
}