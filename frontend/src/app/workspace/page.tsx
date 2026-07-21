"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../lib/api";
import { getServiceLabel } from "../../lib/serviceLabels";
import Link from "next/link";
import { Search } from "lucide-react";

interface WorkspaceProject {
  id: string;
  name: string;
  service_type: string | null;
  contract_months: number | null;
  lead_name: string | null;
  status: string;
  has_workspace: boolean;
  current_month: number | null;
  progress: number | null;
  updated_at: string | null;
}

export default function WorkspaceListPage() {
  const [projects, setProjects] = useState<WorkspaceProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchProjects = useCallback(async () => {
    try {
      const res = await apiFetch("/api/workspace-list");
      if (res.ok) {
        const data = await res.json();
        setProjects(Array.isArray(data) ? data : []);
      }
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const normalizedSearch = searchQuery.trim().toLowerCase();
  const visibleProjects = projects.filter(p => {
    if (!normalizedSearch) return true;
    return [p.name, p.lead_name || "", getServiceLabel(p.service_type) || ""]
      .some(v => v.toLowerCase().includes(normalizedSearch));
  });
  const withWorkspace = visibleProjects.filter(p => p.has_workspace);
  const withoutWorkspace = visibleProjects.filter(p => !p.has_workspace && p.status === "ACTIVE");

  return (
    <div className="mx-auto max-w-5xl space-y-6 rounded-2xl bg-amber-50/20 p-4 sm:p-6 dark:bg-amber-950/5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Workspace</h1>
          <p className="mt-1 text-sm text-gray-500">Sheet retainer / deliverable bulanan per layanan. Kanban harian ada di Board.</p>
        </div>
        <Link href="/board" className="rounded-xl border border-amber-200 bg-white px-3 py-2 text-xs font-semibold text-amber-800 hover:bg-amber-50 dark:border-amber-900/50 dark:bg-[var(--bg-surface)] dark:text-amber-200">
          Ke Board
        </Link>
      </div>
      <label className="relative block max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
        <input
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Cari nama proyek, klien, atau layanan..."
          className="w-full rounded-xl border border-amber-100 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-amber-300 focus:ring-2 focus:ring-amber-200 dark:border-amber-900/40 dark:bg-[var(--bg-surface)] dark:text-neutral-100"
        />
      </label>

      {loading ? <p className="text-sm text-gray-400">Memuat...</p> : (
        <>
          {withWorkspace.length > 0 && (
            <div className="space-y-2">
              <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wide">Workspace Aktif</h2>
              {withWorkspace.map(p => (
                <div key={p.id}
                  className="flex items-center justify-between rounded-xl border border-amber-100 bg-white p-4 shadow-sm transition-colors hover:border-amber-300 dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
                  <Link href={`/workspace/${p.id}`} className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100 truncate">{p.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {[p.lead_name, getServiceLabel(p.service_type), `${p.contract_months || 1} bulan`].filter(Boolean).join(" · ")}
                    </p>
                  </Link>
                  <div className="flex items-center gap-2 ml-3 shrink-0">
                    {p.progress !== null && (
                      <div className="text-right mr-1">
                        <span className="text-xs font-bold text-neutral-600 dark:text-neutral-300">{p.progress}%</span>
                        <div className="w-20 h-1.5 bg-gray-200 dark:bg-neutral-700 rounded-full mt-0.5">
                          <div className="h-full rounded-full bg-amber-500" style={{ width: `${p.progress}%` }} />
                        </div>
                      </div>
                    )}
                    <Link href={`/board?project_id=${p.id}`} className="rounded-lg border border-neutral-200 px-2 py-1 text-[11px] font-semibold text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300">Board</Link>
                    <Link href={`/workspace/${p.id}`} className="rounded-lg bg-amber-500 px-2 py-1 text-[11px] font-semibold text-white hover:bg-amber-600">Sheet</Link>
                  </div>
                </div>
              ))}
            </div>
          )}

          {withoutWorkspace.length > 0 && (
            <div className="space-y-2">
              <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wide">Belum Ada Workspace</h2>
              {withoutWorkspace.map(p => (
                <div key={p.id}
                  className="flex items-center justify-between rounded-xl border border-dashed border-amber-100 bg-white/80 p-4 opacity-80 transition-colors hover:border-amber-300 dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{p.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{p.lead_name || "—"}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-3">
                    <Link href={`/board?project_id=${p.id}`} className="rounded-lg border border-neutral-200 px-2 py-1 text-[11px] font-semibold text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300">Board</Link>
                    <Link href={`/workspace/${p.id}`} className="text-xs text-neutral-500 dark:text-neutral-300 font-bold">+ Inisialisasi</Link>
                  </div>
                </div>
              ))}
            </div>
          )}

          {visibleProjects.length === 0 && (
            <p className="py-12 text-center text-sm text-gray-400">{projects.length === 0 ? "Belum ada project. Buat project dulu di Buku Klien." : "Tidak ada workspace yang cocok dengan pencarian."}</p>
          )}
        </>
      )}
    </div>
  );
}
