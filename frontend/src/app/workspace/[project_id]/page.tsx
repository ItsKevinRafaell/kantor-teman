"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Modal from "../../../components/Modal";
import { apiFetch } from "../../../lib/api";
import WorkspaceSheet from "../../../components/workspace/WorkspaceSheet";
import Toast from "../../../components/Toast";
import { getServiceLabel } from "../../../lib/serviceLabels";
import Breadcrumb from "../../../components/Breadcrumb";

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
  project_name?: string;
  service_type: string | null;
  sheets: SheetData[];
}

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
  const [deleteSheetId, setDeleteSheetId] = useState<string | null>(null);
  const [reportMonth, setReportMonth] = useState(1);
  const [generatingReport, setGeneratingReport] = useState(false);

  async function handleGenerateReport() {
    setGeneratingReport(true);
    try {
      const res = await apiFetch(`/api/workspace/${projectId}/generate-monthly-report?month=${reportMonth}`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
        window.open(`${API_BASE}${data.file_url}`, "_blank");
        showToast(`Laporan bulan ${reportMonth} berhasil dibuat.`);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Gagal generate laporan", "error");
      }
    } catch { showToast("Gagal generate laporan", "error"); }
    finally { setGeneratingReport(false); }
  }

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

  async function handleDeleteSheet(sheetId: string) {
    const res = await apiFetch(`/api/workspace/sheet/${sheetId}`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || "Gagal hapus sheet", "error");
      return;
    }
    setActiveSheet(0);
    await fetchWorkspace();
  }

  if (loading) return <div className="p-8 text-sm text-gray-500">Memuat workspace...</div>;

  if (errorMsg || !workspace) {
    return (
      <div className="p-6 max-w-lg mx-auto space-y-4">
        <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Workspace</h1>
        <div className="bg-neutral-50 dark:bg-neutral-900/40 border border-neutral-200 dark:border-neutral-700 rounded-xl p-4">
          <p className="text-sm text-neutral-700 dark:text-neutral-200">{errorMsg || "Workspace belum tersedia."}</p>
        </div>
        {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      </div>
    );
  }

  const sheets = workspace.sheets;
  const currentSheet = sheets[activeSheet] || sheets[0];

  return (
    <div className="p-4 sm:p-6 max-w-[1400px] mx-auto space-y-4">
      <Breadcrumb items={[
        { label: "Workspace Klien", href: "/workspace" },
        { label: workspace.project_name || "Project" },
      ]} showBack backHref="/workspace" />
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-bold text-neutral-800 dark:text-neutral-100">{workspace.project_name || "Workspace"}</h1>
          {getServiceLabel(workspace.service_type) && (
            <p className="text-xs text-gray-500">{getServiceLabel(workspace.service_type)}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <select
            value={reportMonth}
            onChange={e => setReportMonth(Number(e.target.value))}
            className="px-2 py-1.5 text-xs border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-gray-700 dark:text-gray-300">
            {Array.from({ length: workspace.sheets.filter(s => s.month_number !== null).length || 12 }, (_, i) => i + 1).map(m => (
              <option key={m} value={m}>Bulan {m}</option>
            ))}
          </select>
          <button
            onClick={handleGenerateReport}
            disabled={generatingReport}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-neutral-800 hover:bg-neutral-700 dark:bg-neutral-200 dark:hover:bg-white text-white dark:text-neutral-900 rounded-lg disabled:opacity-50 transition-colors">
            {generatingReport ? "Membuat..." : "Generate Laporan"}
          </button>
        </div>
      </div>

      {/* Sheet tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1 items-center">
        {sheets.map((s, i) => (
          <div key={s.id} className="relative group flex items-center">
            <button onClick={() => setActiveSheet(i)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-colors ${i === activeSheet ? "bg-neutral-800 text-white dark:bg-neutral-200 dark:text-neutral-900" : "bg-gray-100 dark:bg-neutral-800 text-gray-600 dark:text-neutral-300 hover:bg-gray-200"}`}>
              {s.sheet_label}
            </button>
            {s.month_number === null && (
              <button onClick={() => handleDeleteSheet(s.id)} title="Hapus sheet"
                className="ml-0.5 opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-opacity">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            )}
          </div>
        ))}
        <button onClick={() => setAddSheetModal(true)} className="px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap border border-dashed border-gray-300 dark:border-neutral-700 text-gray-500 hover:border-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200">
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
              <button onClick={handleAddSheet} disabled={addingSheet || !newSheetLabel.trim()} className="px-3 py-1.5 text-xs font-semibold bg-neutral-800 hover:bg-neutral-700 dark:bg-neutral-200 dark:hover:bg-white text-white dark:text-neutral-900 rounded-lg disabled:opacity-50">
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
