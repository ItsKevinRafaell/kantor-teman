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
  general: "General",
};

export default function WorkspaceDetailPage() {
  const params = useParams();
  const projectId = params.project_id as string;
  const [workspace, setWorkspace] = useState<WorkspaceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSheet, setActiveSheet] = useState(0);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchWorkspace = useCallback(async () => {
    setErrorMsg(null);
    try {
      const res = await apiFetch(`/api/workspace/${projectId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.sheets && data.sheets.length > 0) {
          setWorkspace(data);
          return;
        }
      }
      // No workspace yet — auto-init from project.service_type
      const projRes = await apiFetch(`/api/projects/${projectId}`);
      if (!projRes.ok) {
        setErrorMsg("Project tidak ditemukan.");
        return;
      }
      const proj = await projRes.json();
      const svcType = proj.service_type || "general";
      const months = proj.contract_months || 1;
      let contractDays: number | null = null;
      if (proj.start_date && proj.end_date) {
        const diff = (new Date(proj.end_date).getTime() - new Date(proj.start_date).getTime()) / (1000 * 60 * 60 * 24);
        if (diff > 0 && diff < 30) contractDays = Math.round(diff);
      }
      const initRes = await apiFetch("/api/workspace/init", {
        method: "POST",
        body: JSON.stringify({
          project_id: projectId,
          service_type: svcType,
          contract_months: months,
          ...(contractDays ? { contract_days: contractDays } : {}),
        }),
      });
      if (!initRes.ok) {
        const err = await initRes.json().catch(() => ({}));
        setErrorMsg(err.detail || "Gagal inisialisasi workspace.");
        return;
      }
      const initData = await initRes.json();
      if (initData.sheets && initData.sheets.length > 0) {
        setWorkspace({ project_id: projectId, service_type: svcType, sheets: initData.sheets });
      } else {
        setErrorMsg("Inisialisasi tidak menghasilkan sheet apa pun.");
      }
    } finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => { fetchWorkspace(); }, [fetchWorkspace]);

  function showToast(msg: string, type: "success" | "error" = "success") {
    setToast({ message: msg, type });
  }

  const [addSheetModal, setAddSheetModal] = useState(false);
  const [newSheetLabel, setNewSheetLabel] = useState("");
  const [addingSheet, setAddingSheet] = useState(false);

  async function handleAddSheet() {
    if (!newSheetLabel.trim()) return;
    setAddingSheet(true);
    try {
      const res = await apiFetch(`/api/workspace/${projectId}/sheets`, {
        method: "POST",
        body: JSON.stringify({ label: newSheetLabel.trim() }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Gagal tambah sheet", "error");
        return;
      }
      setNewSheetLabel("");
      setAddSheetModal(false);
      await fetchWorkspace();
    } finally { setAddingSheet(false); }
  }

  if (loading) return <div className="p-8 text-sm text-gray-500">Memuat workspace...</div>;

  if (errorMsg || !workspace) {
    return (
      <div className="p-6 max-w-lg mx-auto space-y-4">
        <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Workspace</h1>
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded-xl p-4">
          <p className="text-sm text-amber-800 dark:text-amber-200">{errorMsg || "Workspace belum tersedia."}</p>
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
      <div className="flex gap-1 overflow-x-auto pb-1 items-center">
        {sheets.map((s, i) => (
          <button key={s.id} onClick={() => setActiveSheet(i)}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-colors ${i === activeSheet ? "bg-amber-500 text-white" : "bg-gray-100 dark:bg-neutral-800 text-gray-600 dark:text-neutral-300 hover:bg-gray-200"}`}>
            {s.sheet_label}
          </button>
        ))}
        <button onClick={() => setAddSheetModal(true)} className="px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap border border-dashed border-gray-300 dark:border-neutral-700 text-gray-500 hover:border-amber-400 hover:text-amber-600">
          + Sheet
        </button>
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

      {addSheetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40" onClick={() => setAddSheetModal(false)} />
          <div className="relative bg-white dark:bg-neutral-900 rounded-xl shadow-xl border border-gray-200 dark:border-neutral-700 w-full max-w-sm p-5 space-y-4">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-100">Tambah Sheet</h3>
            <input value={newSheetLabel} onChange={e => setNewSheetLabel(e.target.value)} placeholder="Nama sheet..."
              className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" autoFocus />
            <div className="flex justify-end gap-2">
              <button onClick={() => setAddSheetModal(false)} className="px-3 py-1.5 text-xs font-semibold text-gray-600 bg-gray-100 dark:bg-neutral-800 rounded-lg">Batal</button>
              <button onClick={handleAddSheet} disabled={addingSheet || !newSheetLabel.trim()} className="px-3 py-1.5 text-xs font-semibold bg-amber-500 text-white rounded-lg disabled:opacity-50">
                {addingSheet ? "..." : "Tambah"}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
