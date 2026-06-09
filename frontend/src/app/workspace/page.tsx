"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../lib/api";
import { getServiceLabel } from "../../lib/serviceLabels";
import Link from "next/link";

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

  const withWorkspace = projects.filter(p => p.has_workspace);
  const withoutWorkspace = projects.filter(p => !p.has_workspace && p.status === "ACTIVE");

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Workspace Klien</h1>
        <p className="text-sm text-gray-500 mt-1">Kelola task per layanan per bulan — Notion-style spreadsheet.</p>
      </div>

      {loading ? <p className="text-sm text-gray-400">Memuat...</p> : (
        <>
          {withWorkspace.length > 0 && (
            <div className="space-y-2">
              <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wide">Workspace Aktif</h2>
              {withWorkspace.map(p => (
                <Link key={p.id} href={`/workspace/${p.id}`}
                  className="flex items-center justify-between p-4 bg-white dark:bg-neutral-900 border border-[var(--border-default)] rounded-xl hover:border-neutral-300 dark:hover:border-neutral-600 transition-colors">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100 truncate">{p.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {[p.lead_name, getServiceLabel(p.service_type), `${p.contract_months || 1} bulan`].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 ml-3">
                    {p.progress !== null && (
                      <div className="text-right">
                        <span className="text-xs font-bold text-neutral-600 dark:text-neutral-300">{p.progress}%</span>
                        <div className="w-20 h-1.5 bg-gray-200 dark:bg-neutral-700 rounded-full mt-0.5">
                          <div className="h-full bg-neutral-500 dark:bg-neutral-400 rounded-full" style={{ width: `${p.progress}%` }} />
                        </div>
                      </div>
                    )}
                    <span className="text-xs text-gray-400">→</span>
                  </div>
                </Link>
              ))}
            </div>
          )}

          {withoutWorkspace.length > 0 && (
            <div className="space-y-2">
              <h2 className="text-xs font-bold text-gray-500 uppercase tracking-wide">Belum Ada Workspace</h2>
              {withoutWorkspace.map(p => (
                <Link key={p.id} href={`/workspace/${p.id}`}
                  className="flex items-center justify-between p-4 bg-white dark:bg-neutral-900 border border-[var(--border-default)] rounded-xl hover:border-neutral-300 dark:hover:border-neutral-600 transition-colors opacity-70">
                  <div>
                    <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{p.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{p.lead_name || "—"}</p>
                  </div>
                  <span className="text-xs text-neutral-500 dark:text-neutral-300 font-bold">+ Inisialisasi</span>
                </Link>
              ))}
            </div>
          )}

          {projects.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-12">Belum ada project. Buat project dulu di Buku Klien.</p>
          )}
        </>
      )}
    </div>
  );
}
