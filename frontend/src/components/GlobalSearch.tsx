"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, FolderOpen, Search, User, Users, X } from "lucide-react";
import { apiFetch } from "../lib/api";

type ResultKind = "page" | "lead" | "contact" | "document" | "project";

interface SearchResult {
  id: string;
  kind: ResultKind;
  title: string;
  subtitle?: string;
  href: string;
}

const PAGES: SearchResult[] = [
  { id: "p-dashboard", kind: "page", title: "Dashboard", href: "/dashboard" },
  { id: "p-leads", kind: "page", title: "Prospek", href: "/leads" },
  { id: "p-clients", kind: "page", title: "Klien", href: "/clients" },
  { id: "p-board", kind: "page", title: "Board Proyek", href: "/board" },
  { id: "p-workspace", kind: "page", title: "Workspace Klien", href: "/workspace" },
  { id: "p-proposals", kind: "page", title: "Proposal", href: "/proposals" },
  { id: "p-finance", kind: "page", title: "Keuangan", href: "/finance" },
  { id: "p-docs", kind: "page", title: "Dokumen & Laporan", href: "/documents" },
  { id: "p-generator", kind: "page", title: "Dokumen Resmi", href: "/documents/generator" },
  { id: "p-reports", kind: "page", title: "Laporan Klien", href: "/documents/reports" },
  { id: "p-calendar", kind: "page", title: "Kalender Konten", href: "/marketing/calendar" },
  { id: "p-blast", kind: "page", title: "Analitik Pesan", href: "/marketing/blast-analytics" },
  { id: "p-campaigns", kind: "page", title: "Campaign & Kuota", href: "/marketing/campaigns" },
  { id: "p-content", kind: "page", title: "Generator Konten", href: "/content-generator" },
  { id: "p-settings", kind: "page", title: "Pengaturan", href: "/settings" },
  { id: "p-tasks", kind: "page", title: "Antrean Tugas", href: "/tasks" },
  { id: "p-brand", kind: "page", title: "Brand Kit", href: "/master/brand-kit" },
];

function kindIcon(kind: ResultKind) {
  switch (kind) {
    case "lead":
      return <Users size={14} className="text-amber-600" />;
    case "contact":
      return <User size={14} className="text-blue-600" />;
    case "document":
      return <FileText size={14} className="text-emerald-600" />;
    case "project":
      return <FolderOpen size={14} className="text-purple-600" />;
    default:
      return <Search size={14} className="text-neutral-400" />;
  }
}

function kindLabel(kind: ResultKind) {
  switch (kind) {
    case "lead":
      return "Prospek";
    case "contact":
      return "Kontak";
    case "document":
      return "Dokumen";
    case "project":
      return "Proyek";
    default:
      return "Halaman";
  }
}

export default function GlobalSearch({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [remote, setRemote] = useState<SearchResult[]>([]);
  const [activeIdx, setActiveIdx] = useState(0);

  useEffect(() => {
    if (!open) return;
    setQ("");
    setRemote([]);
    setActiveIdx(0);
    const t = setTimeout(() => inputRef.current?.focus(), 30);
    return () => clearTimeout(t);
  }, [open]);

  const pageHits = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return PAGES.slice(0, 8);
    return PAGES.filter(p => p.title.toLowerCase().includes(term)).slice(0, 8);
  }, [q]);

  const runRemote = useCallback(async (term: string) => {
    if (term.length < 2) {
      setRemote([]);
      return;
    }
    setLoading(true);
    try {
      const [leadsRes, contactsRes, docsRes, projectsRes] = await Promise.all([
        apiFetch(`/api/leads?limit=20`).then(r => (r.ok ? r.json() : [])).catch(() => []),
        apiFetch(`/api/contacts`).then(r => (r.ok ? r.json() : [])).catch(() => []),
        apiFetch(`/api/archive?search=${encodeURIComponent(term)}&limit=20`).then(r => (r.ok ? r.json() : [])).catch(() => []),
        apiFetch(`/api/projects`).then(r => (r.ok ? r.json() : [])).catch(() => []),
      ]);
      const t = term.toLowerCase();
      const leads = (Array.isArray(leadsRes) ? leadsRes : [])
        .filter((l: any) =>
          String(l.business_name || "").toLowerCase().includes(t)
          || String(l.phone_number || "").includes(t)
          || String(l.address || "").toLowerCase().includes(t)
        )
        .slice(0, 8)
        .map((l: any) => ({
          id: `lead-${l.id}`,
          kind: "lead" as const,
          title: l.business_name || `Lead #${l.id}`,
          subtitle: [l.phone_number, l.status, l.product_interest].filter(Boolean).join(" · "),
          href: `/leads?q=${encodeURIComponent(l.business_name || "")}`,
        }));
      const contacts = (Array.isArray(contactsRes) ? contactsRes : [])
        .filter((c: any) =>
          String(c.business_name || "").toLowerCase().includes(t)
          || String(c.phone_number || "").includes(t)
        )
        .slice(0, 6)
        .map((c: any) => ({
          id: `contact-${c.id}`,
          kind: "contact" as const,
          title: c.business_name || `Kontak #${c.id}`,
          subtitle: [c.phone_number, c.purchased_product].filter(Boolean).join(" · "),
          href: `/clients`,
        }));
      const docs = (Array.isArray(docsRes) ? docsRes : [])
        .slice(0, 6)
        .map((d: any) => ({
          id: `doc-${d.id}`,
          kind: "document" as const,
          title: d.title || "Dokumen",
          subtitle: d.url || (d.body ? String(d.body).slice(0, 60) : "Arsip"),
          href: `/documents?search=${encodeURIComponent(d.title || "")}&all=1`,
        }));
      const projects = (Array.isArray(projectsRes) ? projectsRes : [])
        .filter((p: any) => String(p.name || "").toLowerCase().includes(t))
        .slice(0, 6)
        .map((p: any) => ({
          id: `proj-${p.id}`,
          kind: "project" as const,
          title: p.name || `Proyek ${p.id}`,
          subtitle: [p.service_type, p.type].filter(Boolean).join(" · "),
          href: `/workspace?project_id=${p.id}`,
        }));
      setRemote([...leads, ...contacts, ...docs, ...projects]);
      setActiveIdx(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    const handle = setTimeout(() => runRemote(q.trim()), 250);
    return () => clearTimeout(handle);
  }, [q, open, runRemote]);

  const results = useMemo(() => [...pageHits, ...remote], [pageHits, remote]);

  function go(item: SearchResult) {
    onClose();
    router.push(item.href);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx(i => Math.min(i + 1, Math.max(results.length - 1, 0)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx(i => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = results[activeIdx];
      if (item) go(item);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[80] flex items-start justify-center bg-black/40 p-4 pt-[12vh] backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-xl overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-2xl dark:border-neutral-700 dark:bg-neutral-900"
        onClick={e => e.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        <div className="flex items-center gap-2 border-b border-neutral-100 px-4 py-3 dark:border-neutral-800">
          <Search size={16} className="text-neutral-400" />
          <input
            ref={inputRef}
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Cari halaman, prospek, klien, dokumen…"
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-neutral-400"
          />
          {loading && <span className="text-[10px] text-neutral-400">…</span>}
          <kbd className="hidden rounded border border-neutral-200 px-1.5 py-0.5 text-[10px] text-neutral-400 sm:inline dark:border-neutral-700">ESC</kbd>
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800">
            <X size={16} />
          </button>
        </div>
        <div className="max-h-[50vh] overflow-y-auto p-2">
          {results.length === 0 ? (
            <p className="px-3 py-8 text-center text-xs text-neutral-400">
              {q.trim().length < 2 ? "Ketik minimal 2 huruf untuk cari data." : "Tidak ada hasil."}
            </p>
          ) : (
            results.map((item, idx) => (
              <button
                key={item.id}
                type="button"
                onClick={() => go(item)}
                onMouseEnter={() => setActiveIdx(idx)}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors ${idx === activeIdx ? "bg-amber-50 dark:bg-amber-950/30" : "hover:bg-neutral-50 dark:hover:bg-neutral-800"}`}
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-neutral-100 dark:bg-neutral-800">
                  {kindIcon(item.kind)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-neutral-800 dark:text-neutral-100">{item.title}</span>
                  <span className="block truncate text-[11px] text-neutral-400">
                    {kindLabel(item.kind)}{item.subtitle ? ` · ${item.subtitle}` : ""}
                  </span>
                </span>
              </button>
            ))
          )}
        </div>
        <div className="border-t border-neutral-100 px-4 py-2 text-[10px] text-neutral-400 dark:border-neutral-800">
          ↑↓ pilih · Enter buka · Esc tutup · ⌘K / Ctrl+K
        </div>
      </div>
    </div>
  );
}
