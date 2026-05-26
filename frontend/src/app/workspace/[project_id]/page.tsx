"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "../../../lib/api";
import WorkspaceSheet from "../../../components/workspace/WorkspaceSheet";
import Toast from "../../../components/Toast";

interface SheetData {
  id: string;
  sheet_index: number;
  sheet_label: string;
  month_number: number | null;
  columns: ColumnData[];
  rows: RowData[];
}

interface ColumnData {
  id: string;
  column_key: string;
  column_label: string;
  column_type: string;
  column_options: string[];
  column_order: number;
  is_system: boolean;
}

interface RowData {
  id: string;
  row_order: number;
  board_card_id: string | null;
  is_template: boolean;
  cells: Record<string, { id: string; value_text: string | null; value_bool: boolean | null; value_number: number | null; value_date: string | null }>;
}

interface WorkspaceData {
  project_id: string;
  service_type: string | null;
  sheets: SheetData[];
}

const SERVICE_LABELS: Record<string, string> = {
  web_dev: "Web Development",
  seo_gmaps: "SEO & Google Maps",
  sosmed: "Kelola Sosial Media",
  maintenance: "Maintenance Website",
  web_dev_bulanan: "Web Dev (Bulanan)",
  branding: "Desain Logo & Branding",
};

export default function WorkspaceDetailPage() {
  const params = useParams();
  const projectId = params.project_id as string;
  const [workspace, setWorkspace] = useState<WorkspaceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSheet, setActiveSheet] = useState(0);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Init form
  const [initMode, setInitMode] = useState(false);
  const [initService, setInitService] = useState("web_dev");
  const [initMonths, setInitMonths] = useState(2);
  const [initing, setIniting] = useState(false);

  const fetchWorkspace = useCallback(async () => {
    try {
      const res = await apiFetch(`/api/workspace/${projectId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.sheets && data.sheets.length > 0) {
          setWorkspace(data);
          setInitMode(false);
          return;
        }
      }
      // No workspace yet — check if project has service_type to auto-init
      const projRes = await apiFetch(`/api/projects/${projectId}`);
      if (projRes.ok) {
        const proj = await projRes.json();
        if (proj.service_type) {
          // Auto-init silently from project data
          const initRes = await apiFetch("/api/workspace/init", {
            method: "POST",
            body: JSON.stringify({
              project_id: projectId,
              service_type: proj.service_type,
              contract_months: proj.contract_months || 1,
            }),
          });
          if (initRes.ok) {
            const initData = await initRes.json();
            if (initData.sheets && initData.sheets.length > 0) {
              setWorkspace({ project_id: projectId, service_type: proj.service_type, sheets: initData.sheets });
              setInitMode(false);
              return;
            }
          }
        }
        // No service_type — show manual form with defaults from project
        setInitService(proj.service_type || "web_dev");
        setInitMonths(proj.contract_months || 2);
      }
      setInitMode(true);
    } finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => { fetchWorkspace(); }, [fetchWorkspace]);

  async function handleInit() {
    setIniting(true);
    try {
      const res = await apiFetch("/api/workspace/init", {
        method: "POST",
        body: JSON.stringify({ project_id: projectId, service_type: initService, contract_months: initMonths }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Gagal inisialisasi");
      }
      setToast({ message: "Workspace berhasil dibuat!", type: "success" });
      await fetchWorkspace();
    } catch (e: unknown) {
      setToast({ message: e instanceof Error ? e.message : "Gagal", type: "error" });
    } finally { setIniting(false); }
  }

  function showToast(msg: string, type: "success" | "error" = "success") {
    setToast({ message: msg, type });
  }

  if (loading) return <div className="p-8 text-sm text-gray-500">Memuat workspace...</div>;

  if (initMode || !workspace) {
    return (
      <div className="p-6 max-w-lg mx-auto space-y-6">
        <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Inisialisasi Workspace</h1>
        <p className="text-sm text-gray-500">Pilih jenis layanan dan durasi kontrak untuk generate template workspace.</p>
        <div className="space-y-4 bg-white dark:bg-neutral-900 border border-[var(--border-default)] rounded-2xl p-6">
          <div>
            <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Jenis Layanan</label>
            <select value={initService} onChange={e => { setInitService(e.target.value); setInitMonths(({ web_dev: 2, seo_gmaps: 6, sosmed: 3, maintenance: 1, web_dev_bulanan: 3, branding: 1 } as Record<string, number>)[e.target.value] || 1); }}
              className="mt-1 w-full px-3 py-2.5 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-800">
              {Object.entries(SERVICE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Durasi Kontrak (bulan)</label>
            <input type="number" min={1} max={24} value={initMonths} onChange={e => setInitMonths(Number(e.target.value))}
              className="mt-1 w-full px-3 py-2.5 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-800" />
          </div>
          <button onClick={handleInit} disabled={initing}
            className="w-full py-3 bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-xl disabled:opacity-50 transition-colors">
            {initing ? "Membuat..." : "Inisialisasi Workspace"}
          </button>
        </div>
        {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      </div>
    );
  }

  const sheets = workspace.sheets;
  const currentSheet = sheets[activeSheet] || sheets[0];

  return (
    <div className="p-4 sm:p-6 max-w-[1400px] mx-auto space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-bold text-neutral-800 dark:text-neutral-100">Workspace</h1>
          <p className="text-xs text-gray-500">{SERVICE_LABELS[workspace.service_type || ""] || workspace.service_type}</p>
        </div>
      </div>

      {/* Sheet tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {sheets.map((s, i) => (
          <button key={s.id} onClick={() => setActiveSheet(i)}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-colors ${i === activeSheet ? "bg-amber-500 text-white" : "bg-gray-100 dark:bg-neutral-800 text-gray-600 dark:text-neutral-300 hover:bg-gray-200"}`}>
            {s.sheet_label}
          </button>
        ))}
      </div>

      {/* Active sheet */}
      {currentSheet && (
        <WorkspaceSheet
          sheet={currentSheet}
          projectId={projectId}
          onRefresh={fetchWorkspace}
          onToast={showToast}
        />
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
