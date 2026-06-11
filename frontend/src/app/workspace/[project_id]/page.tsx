"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
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
    <div className="mx-auto max-w-[1400px] space-y-4 rounded-2xl bg-amber-50/20 p-4 sm:p-6 dark:bg-amber-950/5">
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
            className="rounded-lg border border-amber-100 bg-white px-2 py-1.5 text-xs text-gray-700 dark:border-amber-900/40 dark:bg-[var(--bg-surface)] dark:text-gray-300">
            {Array.from({ length: workspace.sheets.filter(s => s.month_number !== null).length || 12 }, (_, i) => i + 1).map(m => (
              <option key={m} value={m}>Bulan {m}</option>
            ))}
          </select>
          <Link
            href={`/documents/reports?target_type=project&project_id=${projectId}&report_type=monthly&month=${reportMonth}`}
            className="flex items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-amber-600">
            Buat Laporan
          </Link>
        </div>
      </div>

      {/* Sheet tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1 items-center">
        {sheets.map((s, i) => (
          <div key={s.id} className="relative group flex items-center">
            <button onClick={() => setActiveSheet(i)}
              className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${i === activeSheet ? "bg-amber-500 text-white" : "bg-white text-gray-600 hover:bg-amber-50 dark:bg-[var(--bg-surface)] dark:text-neutral-300 dark:hover:bg-amber-950/20"}`}>
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
        <button onClick={() => setAddSheetModal(true)} className="whitespace-nowrap rounded-lg border border-dashed border-amber-200 px-3 py-1.5 text-xs font-semibold text-amber-700 hover:border-amber-400 hover:text-amber-900 dark:border-amber-900/50 dark:text-amber-300">
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
          <div className="relative w-full max-w-sm space-y-4 rounded-xl border border-amber-100 bg-white p-5 shadow-xl dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-100">Tambah Sheet</h3>
            <input value={newSheetLabel} onChange={e => setNewSheetLabel(e.target.value)} placeholder="Nama sheet..."
              className="w-full rounded-lg border border-amber-100 bg-amber-50/40 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-amber-900/40 dark:bg-neutral-800/70" autoFocus />
            <div className="flex justify-end gap-2">
              <button onClick={() => setAddSheetModal(false)} className="rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-600 dark:bg-neutral-800/70">Batal</button>
              <button onClick={handleAddSheet} disabled={addingSheet || !newSheetLabel.trim()} className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-600 disabled:opacity-50">
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
