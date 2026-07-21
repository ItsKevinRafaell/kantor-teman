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

  // Riwayat state
  const [mainTab, setMainTab] = useState<"sheets" | "riwayat">("sheets");
  const [riwayat, setRiwayat] = useState<Array<{ id: string; project_id: string; timestamp: string; actor: string; category: string; content: string; attachments: string[] | null }>>([]);
  const [riwayatLoading, setRiwayatLoading] = useState(false);
  const [riwayatCategory, setRiwayatCategory] = useState("");
  const [newRiwayatCategory, setNewRiwayatCategory] = useState("NOTE");
  const [newRiwayatContent, setNewRiwayatContent] = useState("");
  const [riwayatSubmitting, setRiwayatSubmitting] = useState(false);
  const [riwayatError, setRiwayatError] = useState<string | null>(null);
  const [currentUserRole, setCurrentUserRole] = useState<string>("member");

  const fetchRiwayat = useCallback(async (category: string = "") => {
    setRiwayatLoading(true);
    setRiwayatError(null);
    try {
      const url = `/api/projects/${projectId}/riwayat${category ? `?category=${encodeURIComponent(category)}` : ""}`;
      const res = await apiFetch(url);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setRiwayatError(err.detail || "Gagal memuat riwayat.");
        setRiwayat([]);
        return;
      }
      const data = await res.json();
      setRiwayat(data || []);
    } catch (e: any) {
      setRiwayatError(e?.message || "Gagal memuat riwayat.");
    } finally {
      setRiwayatLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    try {
      const role = typeof window !== "undefined" ? localStorage.getItem("kt_role") : null;
      setCurrentUserRole(role || "member");
    } catch {}
  }, []);

  useEffect(() => {
    if (mainTab === "riwayat") fetchRiwayat(riwayatCategory);
  }, [mainTab, riwayatCategory, fetchRiwayat]);

  async function handleAddRiwayat() {
    if (!newRiwayatContent.trim()) return;
    setRiwayatSubmitting(true);
    try {
      const res = await apiFetch(`/api/projects/${projectId}/riwayat`, {
        method: "POST",
        body: JSON.stringify({
          category: newRiwayatCategory,
          content: newRiwayatContent.trim(),
          attachments: [],
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Gagal tambah riwayat", "error");
        return;
      }
      setNewRiwayatContent("");
      showToast("Riwayat ditambahkan", "success");
      await fetchRiwayat(riwayatCategory);
    } finally {
      setRiwayatSubmitting(false);
    }
  }

  async function handleDeleteRiwayat(id: string) {
    if (!confirm("Hapus item riwayat ini?")) return;
    const res = await apiFetch(`/api/projects/riwayat/${id}`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || "Gagal hapus riwayat", "error");
      return;
    }
    showToast("Riwayat dihapus", "success");
    await fetchRiwayat(riwayatCategory);
  }

  const RIWAYAT_CATEGORY_COLORS: Record<string, string> = {
    STATUS: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    INVOICE: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
    NOTE: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    FILE: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
    MILESTONE: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300",
    OTHER: "bg-gray-100 text-gray-700 dark:bg-gray-800/50 dark:text-gray-300",
  };

  function formatRiwayatDate(ts: string) {
    try {
      const d = new Date(ts);
      if (isNaN(d.getTime())) return ts;
      return d.toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });
    } catch {
      return ts;
    }
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
    <div className="mx-auto max-w-[1400px] space-y-4 rounded-2xl bg-amber-50/20 p-4 sm:p-6 dark:bg-amber-950/5">
      <Breadcrumb items={[
        { label: "Workspace Klien", href: "/workspace" },
        { label: workspace.project_name || "Project" },
      ]} showBack backHref="/workspace" />
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-bold text-neutral-800 dark:text-neutral-100">{workspace.project_name || "Workspace"}</h1>
          <p className="text-xs text-gray-500">
            {[getServiceLabel(workspace.service_type), "sheet retainer bulanan"].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={`/board?project_id=${projectId}`}
            className="rounded-lg border border-amber-100 bg-white px-3 py-1.5 text-xs font-semibold text-amber-800 hover:bg-amber-50 dark:border-amber-900/40 dark:bg-[var(--bg-surface)] dark:text-amber-200">
            Buka Board
          </Link>
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
        <button onClick={() => setMainTab("sheets")}
          className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${mainTab === "sheets" ? "bg-amber-500 text-white" : "bg-white text-gray-600 hover:bg-amber-50 dark:bg-[var(--bg-surface)] dark:text-neutral-300 dark:hover:bg-amber-950/20"}`}>
          Workspace
        </button>
        <button onClick={() => setMainTab("riwayat")}
          className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${mainTab === "riwayat" ? "bg-amber-500 text-white" : "bg-white text-gray-600 hover:bg-amber-50 dark:bg-[var(--bg-surface)] dark:text-neutral-300 dark:hover:bg-amber-950/20"}`}>
          Riwayat
        </button>
      </div>

      {mainTab === "riwayat" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-blue-100 bg-blue-50/60 px-4 py-3 text-xs text-blue-800 dark:border-blue-900/40 dark:bg-blue-950/20 dark:text-blue-200">
            <p className="font-semibold">Apa itu Riwayat?</p>
            <p className="mt-1 leading-relaxed opacity-90">
              Timeline project (catatan handover, status, invoice, file, milestone). Bukan sheet kerja — sheet untuk task/SOP; riwayat untuk jejak keputusan & komunikasi. Audit log sistem (Settings) terpisah.
            </p>
          </div>
          {/* Form tambah */}
          <div className="rounded-xl border border-amber-100 bg-white p-4 dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
            <h3 className="mb-3 text-sm font-bold text-neutral-800 dark:text-neutral-100">Tambah Riwayat</h3>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <select
                value={newRiwayatCategory}
                onChange={e => setNewRiwayatCategory(e.target.value)}
                className="rounded-lg border border-amber-100 bg-amber-50/40 px-2 py-1.5 text-xs text-gray-700 dark:border-amber-900/40 dark:bg-neutral-800/70 dark:text-gray-300">
                <option value="NOTE">Catatan</option>
                <option value="STATUS">Status</option>
                <option value="INVOICE">Invoice</option>
                <option value="FILE">File</option>
                <option value="MILESTONE">Milestone</option>
                <option value="OTHER">Lainnya</option>
              </select>
              <input
                value={newRiwayatContent}
                onChange={e => setNewRiwayatContent(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAddRiwayat(); } }}
                placeholder="Tulis catatan / update project..."
                className="flex-1 rounded-lg border border-amber-100 bg-amber-50/40 px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-amber-300 dark:border-amber-900/40 dark:bg-neutral-800/70" />
              <button
                onClick={handleAddRiwayat}
                disabled={riwayatSubmitting || !newRiwayatContent.trim()}
                className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-600 disabled:opacity-50">
                {riwayatSubmitting ? "..." : "Tambah"}
              </button>
            </div>
          </div>

          {/* Filter category */}
          <div className="flex gap-1 overflow-x-auto pb-1">
            <button onClick={() => setRiwayatCategory("")}
              className={`whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold transition-colors ${riwayatCategory === "" ? "bg-neutral-800 text-white dark:bg-neutral-200 dark:text-neutral-900" : "bg-white text-gray-600 hover:bg-amber-50 dark:bg-[var(--bg-surface)] dark:text-neutral-300"}`}>
              Semua
            </button>
            {["STATUS", "INVOICE", "NOTE", "FILE", "MILESTONE", "OTHER"].map(cat => (
              <button key={cat} onClick={() => setRiwayatCategory(cat)}
                className={`whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold transition-colors ${riwayatCategory === cat ? "bg-neutral-800 text-white dark:bg-neutral-200 dark:text-neutral-900" : "bg-white text-gray-600 hover:bg-amber-50 dark:bg-[var(--bg-surface)] dark:text-neutral-300"}`}>
                {cat}
              </button>
            ))}
          </div>

          {/* List */}
          {riwayatLoading ? (
            <div className="p-6 text-center text-sm text-gray-500">Memuat riwayat...</div>
          ) : riwayatError ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">
              {riwayatError}
            </div>
          ) : riwayat.length === 0 ? (
            <div className="rounded-xl border border-amber-100 bg-amber-50/40 p-6 text-center text-sm text-gray-500 dark:border-amber-900/40 dark:bg-amber-950/10">
              Belum ada riwayat untuk project ini.
            </div>
          ) : (
            <div className="space-y-2">
              {riwayat.map(item => (
                <div key={item.id} className="rounded-xl border border-amber-100 bg-white p-3 dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${RIWAYAT_CATEGORY_COLORS[item.category] || RIWAYAT_CATEGORY_COLORS.OTHER}`}>
                          {item.category}
                        </span>
                        <span className="text-[11px] text-gray-500">{formatRiwayatDate(item.timestamp)}</span>
                        <span className="text-[11px] text-gray-400">• {item.actor}</span>
                      </div>
                      <p className="whitespace-pre-wrap break-words text-sm text-neutral-800 dark:text-neutral-200">{item.content}</p>
                      {item.attachments && item.attachments.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {item.attachments.map((url, idx) => (
                            <a key={idx} href={url} target="_blank" rel="noopener noreferrer"
                              className="block truncate text-xs text-amber-700 hover:underline dark:text-amber-300">
                              📎 {url}
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                    {currentUserRole === "admin" && (
                      <button onClick={() => handleDeleteRiwayat(item.id)}
                        title="Hapus"
                        className="shrink-0 p-1 text-gray-400 hover:text-red-500">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {mainTab === "sheets" && (<>
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
      </>)}

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
