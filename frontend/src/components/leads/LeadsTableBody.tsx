"use client";
import { Star, Flame, Mail, Target, Pencil } from "lucide-react";
import { getScoreLabel, getScoreColor } from "../../lib/leadScore";

const STATUS_COLORS: Record<string, string> = {
  Scraped: "bg-gray-100 text-gray-700",
  Contacted: "bg-blue-100 text-blue-700",
  Replied: "bg-yellow-100 text-yellow-700",
  "Closed/Lost": "bg-red-100 text-red-700",
  "Closed/Client": "bg-green-100 text-green-700",
};
const STATUSES = ["Scraped", "Contacted", "Replied", "Closed/Lost", "Closed/Client"] as const;

interface Lead {
  id: number;
  business_name: string;
  phone_number: string;
  address: string | null;
  original_url: string | null;
  status: string;
  product_interest: string | null;
  batch_name: string | null;
  rating: number;
  is_archived: boolean;
  deleted_at: string | null;
  lead_score: number;
  action_recommendation?: string;
  is_ghost_viewer: boolean;
  website_url?: string | null;
  google_rating?: number | null;
  review_count?: number | null;
  sales_owner?: string | null;
  next_action_at?: string | null;
  loss_reason?: string | null;
  do_not_contact: boolean;
}

interface LeadsTableBodyProps {
  leads: Lead[];
  filters: { rating: number; score: string };
  searchQuery: string;
  blastCategories: { id: string; name: string }[];
  updating: number | null;
  onUpdateStatus: (id: number, status: string) => void;
  onUpdateProduct: (id: number, product: string) => void;
  onChatWA: (lead: Lead) => void;
  onFollowUp: (lead: Lead) => void;
  onStartSequence: (lead: Lead) => void;
  onOpenSales: (lead: Lead) => void;
  onConvert: (lead: Lead) => void;
  onEdit: (lead: Lead) => void;
  onArchive: (lead: Lead) => void;
  onRestore: (id: number) => void;
}

function getScoreBreakdown(lead: Lead): string[] {
  const parts: string[] = [];
  if (lead.google_rating != null) {
    if (lead.google_rating >= 4.5) parts.push("Rating ≥4.5 +15");
    else if (lead.google_rating >= 4.0) parts.push("Rating 4.0-4.4 +10");
    else if (lead.google_rating >= 3.5) parts.push("Rating 3.5-3.9 +5");
    else parts.push("Rating <3.5 -10");
  }
  const rc = lead.review_count || 0;
  if (rc > 100) parts.push("Reviews >100 +15");
  else if (rc >= 20) parts.push("Reviews 20-100 +10");
  const pi = (lead.product_interest || "").toLowerCase();
  if (lead.website_url) {
    if (pi.includes("seo") || pi.includes("maintenance")) parts.push("Has website (SEO) +5");
    else parts.push("Has website -5");
  } else if (pi.includes("web")) parts.push("No website (WebDev) +10");
  const bn = (lead.batch_name || "").toLowerCase();
  if (bn.includes("web form")) parts.push("Web Form +20");
  else if (bn.includes("·") || bn.includes("scrape")) parts.push("Maps scraper -5");
  if (lead.status === "Replied") parts.push("Replied +15");
  else if (lead.status === "Contacted") parts.push("Contacted -10");
  const addr = (lead.address || "").toLowerCase();
  if (["jakarta","surabaya","bandung","bali","denpasar"].some(c => addr.includes(c))) parts.push("Tier 1 city +5");
  const name = (lead.business_name || "").toUpperCase();
  if (["PT ","PT."," CV ","CV.","GROUP","GRUP"].some(k => name.includes(k))) parts.push("PT/CV/Group +10");
  return parts;
}

export default function LeadsTableBody({
  leads, filters, searchQuery, blastCategories, updating,
  onUpdateStatus, onUpdateProduct, onChatWA, onFollowUp, onStartSequence,
  onOpenSales, onConvert, onEdit, onArchive, onRestore,
}: LeadsTableBodyProps) {
  const filtered = leads.filter(l => {
    if (filters.rating !== 0 && l.rating < filters.rating) return false;
    if (searchQuery && !l.business_name.toLowerCase().includes(searchQuery.toLowerCase())
      && !(l.address || "").toLowerCase().includes(searchQuery.toLowerCase()) && !l.phone_number.includes(searchQuery)) return false;
    const s = l.lead_score ?? 0;
    if (filters.score === "hot" && s < 80) return false;
    if (filters.score === "warm" && (s < 50 || s >= 80)) return false;
    if (filters.score === "cold" && s >= 50) return false;
    return true;
  }).sort((a, b) => {
    const now = Date.now();
    const aOverdue = a.next_action_at && new Date(a.next_action_at).getTime() <= now ? 1 : 0;
    const bOverdue = b.next_action_at && new Date(b.next_action_at).getTime() <= now ? 1 : 0;
    return bOverdue - aOverdue || (b.lead_score ?? 0) - (a.lead_score ?? 0);
  });

  return (
    <>
      {filtered.map((lead, i) => (
        <tr key={lead.id}
          className={`hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${lead.is_archived ? "opacity-70" : ""} ${lead.is_ghost_viewer ? "bg-red-500/10 border-l-4 border-l-red-500 animate-pulse" : ""}`}>
          <td className="px-4 py-3 text-gray-400 text-xs">{i + 1}</td>
          <td className="px-4 py-3 font-medium text-gray-800 dark:text-neutral-50 max-w-[180px]">
            <div className="flex items-center gap-1.5">
              <span>{lead.business_name}{lead.is_archived ? " (Archived)" : ""}</span>
              {lead.is_ghost_viewer && (
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 whitespace-nowrap">GHOST VIEWER</span>
              )}
            </div>
            {lead.batch_name && <div className="text-[10px] text-gray-400 mt-0.5 truncate max-w-[160px]">{lead.batch_name}</div>}
          </td>
          <td className="px-4 py-3 text-gray-500 dark:text-gray-400 max-w-[180px] text-xs leading-relaxed">{lead.address ?? "—"}</td>
          <td className="px-4 py-3 font-mono text-gray-600 dark:text-gray-400 text-xs whitespace-nowrap">+{lead.phone_number}</td>
          <td className="px-4 py-3">
            <select value={lead.product_interest ?? ""} disabled={updating === lead.id || lead.is_archived}
              onChange={e => onUpdateProduct(lead.id, e.target.value)}
              className="text-xs border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 bg-white dark:bg-[var(--bg-surface)] text-gray-700 dark:text-neutral-50 cursor-pointer hover:border-amber-400 focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-50 transition-colors">
              <option value="">— pilih —</option>
              {blastCategories.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
            </select>
          </td>
          <td className="px-4 py-3 text-xs">
            {lead.website_url ? (
              <a href={lead.website_url} target="_blank" rel="noopener" className="text-blue-600 hover:underline truncate block max-w-[120px]" title={lead.website_url}>
                {lead.website_url.replace(/^https?:\/\//, "").replace(/\/$/, "").slice(0, 20)}...
              </a>
            ) : <span className="text-gray-300">—</span>}
          </td>
          <td className="px-4 py-3 text-xs">
            {lead.google_rating ? (
              <div className="flex items-center gap-1">
                <Star size={12} fill="currentColor" className="text-yellow-500" />
                <span className="font-medium">{lead.google_rating.toFixed(1)}</span>
                {lead.review_count && <span className="text-gray-400">({lead.review_count})</span>}
              </div>
            ) : <span className="text-gray-300">—</span>}
          </td>
          <td className="px-4 py-3 text-xs">
            {(() => {
              const score = lead.lead_score ?? 0;
              const color = getScoreColor(score);
              const tierLabel = getScoreLabel(score);
              const breakdown = getScoreBreakdown(lead);
              return (
                <div className="group relative w-28">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="font-bold tabular-nums">{score}</span>
                  </div>
                  <div className="text-[10px] text-gray-500 dark:text-gray-400 mb-1 truncate" title={tierLabel}>{tierLabel}</div>
                  <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div className={`h-full ${color} transition-all`} style={{ width: `${score}%` }}></div>
                  </div>
                  {lead.action_recommendation === "personal_wa" && (
                    <div className="mt-1 inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-bold bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"><Flame size={10} className="inline" /> Personal WA</div>
                  )}
                  {lead.action_recommendation === "blast_ready" && (
                    <div className="mt-1 inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"><Mail size={10} className="inline" /> Siap Blast</div>
                  )}
                  {breakdown.length > 0 && (
                    <div className="absolute left-0 top-full mt-1 z-20 hidden group-hover:block bg-gray-900 text-white text-[10px] rounded-lg px-3 py-2 shadow-xl whitespace-nowrap min-w-[180px]">
                      <div className="font-bold mb-1">Breakdown:</div>
                      {breakdown.map((b, i) => <div key={i}>• {b}</div>)}
                      <div className="mt-1 pt-1 border-t border-gray-700">Base: 50</div>
                    </div>
                  )}
                </div>
              );
            })()}
          </td>
          <td className="px-4 py-3 text-xs min-w-[145px]">
            {lead.next_action_at ? (
              <div className={new Date(lead.next_action_at).getTime() < Date.now() ? "text-red-600 font-semibold" : "text-neutral-600 dark:text-neutral-300"}>
                {new Date(lead.next_action_at).toLocaleString("id-ID", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
              </div>
            ) : <span className="text-gray-300">Belum diatur</span>}
            {lead.sales_owner && <div className="text-[10px] text-gray-400 mt-0.5">PIC: {lead.sales_owner}</div>}
            {lead.do_not_contact && <div className="text-[10px] text-red-500 font-bold mt-0.5">OPT-OUT</div>}
          </td>
          <td className="px-4 py-3">
            <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-semibold ${STATUS_COLORS[lead.status] || ""}`}>{lead.status}</span>
          </td>
          <td className="px-4 py-3">
            <div className="flex items-center gap-1 flex-wrap max-w-[220px]">
              {lead.is_archived ? (
                <button onClick={() => onRestore(lead.id)}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-[11px] font-semibold rounded-lg transition-all whitespace-nowrap">
                  Restore
                </button>
              ) : (
                <>
                  <button onClick={() => onChatWA(lead)} disabled={updating === lead.id || lead.do_not_contact} title={lead.do_not_contact ? "Diblokir: lead opt-out" : "Chat WhatsApp"}
                    className="p-1.5 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-all disabled:opacity-50">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" /></svg>
                  </button>
                  {(lead.status === "Contacted" || lead.status === "Replied") && (
                    <>
                      <button onClick={() => onFollowUp(lead)} disabled={updating === lead.id || lead.do_not_contact} title="Follow Up Manual"
                        className="p-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg transition-all disabled:opacity-50">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" /></svg>
                      </button>
                      <button onClick={() => onStartSequence(lead)} disabled={updating === lead.id || lead.do_not_contact} title="Start Auto Follow-up"
                        className="p-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all disabled:opacity-50">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
                      </button>
                    </>
                  )}
                  <button onClick={() => onOpenSales(lead)} title="Atur PIC dan next action"
                    className="p-1.5 text-neutral-400 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-all">
                    <Target size={12} />
                  </button>
                  <select value={lead.status} disabled={updating === lead.id}
                    onChange={e => onUpdateStatus(lead.id, e.target.value)}
                    className="text-[11px] border border-neutral-200 dark:border-neutral-700 rounded-lg px-1.5 py-1.5 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 cursor-pointer focus:outline-none focus:ring-1 focus:ring-amber-300 disabled:opacity-50 transition-colors w-[90px]">
                    {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                  {lead.status !== "Closed/Client" && (
                    <button onClick={() => onConvert(lead)} disabled={updating === lead.id} title="Jadikan Klien"
                      className="p-1.5 text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-all disabled:opacity-50">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                    </button>
                  )}
                  <button onClick={() => onEdit(lead)} disabled={updating === lead.id} title="Edit Lead"
                    className="p-1.5 text-neutral-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-all disabled:opacity-50">
                    <Pencil size={12} />
                  </button>
                  <button onClick={() => onArchive(lead)} disabled={updating === lead.id} title="Archive"
                    className="p-1.5 text-neutral-300 dark:text-neutral-600 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all disabled:opacity-50">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14H6L5 6" /><path d="M10 11v6" /><path d="M14 11v6" /><path d="M9 6V4h6v2" /></svg>
                  </button>
                </>
              )}
            </div>
          </td>
        </tr>
      ))}
    </>
  );
}
