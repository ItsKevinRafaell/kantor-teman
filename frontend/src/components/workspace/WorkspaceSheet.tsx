"use client";

import { useState, useRef } from "react";
import { apiFetch } from "../../lib/api";
import { Plus, Trash2, Upload, ExternalLink } from "lucide-react";

interface ColumnData {
  id: string;
  column_key: string;
  column_label: string;
  column_type: string;
  column_options: string[];
  column_order: number;
  is_system: boolean;
}

interface CellValue {
  id: string;
  value_text: string | null;
  value_bool: boolean | null;
  value_number: number | null;
  value_date: string | null;
}

interface RowData {
  id: string;
  row_order: number;
  board_card_id: string | null;
  is_template: boolean;
  cells: Record<string, CellValue>;
}

interface SheetData {
  id: string;
  sheet_index: number;
  sheet_label: string;
  month_number: number | null;
  columns: ColumnData[];
  rows: RowData[];
}

interface Props {
  sheet: SheetData;
  projectId: string;
  onRefresh: () => Promise<void>;
  onToast: (msg: string, type?: "success" | "error") => void;
}

const STATUS_COLORS: Record<string, string> = {
  "To Do": "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
  "In Progress": "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  "Done": "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  "Draft": "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  "Approved": "bg-blue-100 text-blue-700",
  "Posted": "bg-green-100 text-green-700",
  "Published": "bg-green-100 text-green-700",
  "Revision": "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  "Review": "bg-purple-100 text-purple-700",
};

const COL_WIDTHS: Record<string, string> = {
  text: "min-w-[180px]",
  textarea: "min-w-[200px]",
  status: "min-w-[130px]",
  checkbox: "w-12",
  date: "min-w-[130px]",
  url: "min-w-[160px]",
  number: "min-w-[100px]",
  select: "min-w-[140px]",
};

export default function WorkspaceSheet({ sheet, projectId, onRefresh, onToast }: Props) {
  const [rows, setRows] = useState<RowData[]>(sheet.rows);
  const [saving, setSaving] = useState<string | null>(null);
  const [expandedCell, setExpandedCell] = useState<{ rowId: string; colId: string; value: string } | null>(null);
  const [addingRow, setAddingRow] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadTarget, setUploadTarget] = useState<{ rowId: string; colId: string } | null>(null);

  const colById = Object.fromEntries(sheet.columns.map(c => [c.id, c]));

  function getCellValue(row: RowData, col: ColumnData): CellValue | null {
    return row.cells[col.id] || null;
  }

  function getDisplayValue(row: RowData, col: ColumnData): string | boolean | number | null {
    const cell = getCellValue(row, col);
    if (!cell) return null;
    if (col.column_type === "checkbox") return cell.value_bool ?? false;
    if (col.column_type === "number") return cell.value_number ?? null;
    if (col.column_type === "date") return cell.value_date ?? null;
    return cell.value_text ?? null;
  }

  async function patchCell(rowId: string, colId: string, payload: Record<string, unknown>) {
    setSaving(`${rowId}-${colId}`);
    try {
      const res = await apiFetch(`/api/workspace/cell/${rowId}/${colId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error();
      setRows(prev => prev.map(r => {
        if (r.id !== rowId) return r;
        const existing = r.cells[colId] || { id: "", value_text: null, value_bool: null, value_number: null, value_date: null };
        return { ...r, cells: { ...r.cells, [colId]: { ...existing, ...payload } } };
      }));
    } catch {
      onToast("Gagal simpan", "error");
    } finally { setSaving(null); }
  }

  async function addRow() {
    setAddingRow(true);
    try {
      const res = await apiFetch(`/api/workspace/sheet/${sheet.id}/row`, {
        method: "POST",
        body: JSON.stringify({ cells: { task_name: "Task baru" } }),
      });
      if (!res.ok) throw new Error();
      const newRow = await res.json();
      setRows(prev => [...prev, newRow]);
    } catch { onToast("Gagal tambah row", "error"); }
    finally { setAddingRow(false); }
  }

  async function deleteRow(rowId: string, isTemplate: boolean) {
    if (isTemplate) { onToast("Row template tidak dapat dihapus", "error"); return; }
    if (!confirm("Hapus row ini?")) return;
    const res = await apiFetch(`/api/workspace/row/${rowId}`, { method: "DELETE" });
    if (res.ok || res.status === 204) {
      setRows(prev => prev.filter(r => r.id !== rowId));
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    if (!uploadTarget || !e.target.files?.[0]) return;
    const file = e.target.files[0];
    const fd = new FormData();
    fd.append("file", file);
    fd.append("column_id", uploadTarget.colId);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/workspace/row/${uploadTarget.rowId}/attachment`, {
        method: "POST",
        body: fd,
        headers: { Authorization: `Bearer ${document.cookie.split("kt_token=")[1]?.split(";")[0] || ""}` },
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setRows(prev => prev.map(r => {
        if (r.id !== uploadTarget.rowId) return r;
        const existing = r.cells[uploadTarget.colId] || { id: "", value_text: null, value_bool: null, value_number: null, value_date: null };
        return { ...r, cells: { ...r.cells, [uploadTarget.colId]: { ...existing, value_text: data.file_url } } };
      }));
      onToast("File diupload");
    } catch { onToast("Upload gagal", "error"); }
    setUploadTarget(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const totalTasks = rows.length;
  const doneTasks = rows.filter(r => {
    const doneCol = sheet.columns.find(c => c.column_key === "done");
    if (!doneCol) return false;
    return r.cells[doneCol.id]?.value_bool === true;
  }).length;
  const pct = totalTasks > 0 ? Math.round(doneTasks / totalTasks * 100) : 0;

  return (
    <div className="space-y-3">
      {/* Progress summary */}
      <div className="flex items-center gap-3 text-sm">
        <span className="text-gray-500">{doneTasks}/{totalTasks} selesai</span>
        <div className="flex-1 max-w-xs h-2 bg-gray-200 dark:bg-neutral-700 rounded-full overflow-hidden">
          <div className="h-full bg-amber-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
        </div>
        <span className="font-bold text-amber-600">{pct}%</span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-[var(--border-default)] bg-white dark:bg-neutral-900">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-gray-50 dark:bg-neutral-800 border-b border-[var(--border-default)]">
              <th className="w-8 px-2 py-2.5" />
              {sheet.columns.map(col => (
                <th key={col.id} className={`text-left px-3 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap ${COL_WIDTHS[col.column_type] || "min-w-[120px]"}`}>
                  {col.column_label}
                </th>
              ))}
              <th className="w-8 px-2 py-2.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-subtle)]">
            {rows.map(row => (
              <tr key={row.id} className="group hover:bg-gray-50 dark:hover:bg-neutral-800 transition-colors">
                <td className="px-2 py-2 text-gray-300 text-xs text-center">{row.row_order + 1}</td>
                {sheet.columns.map(col => {
                  const val = getDisplayValue(row, col);
                  const isSaving = saving === `${row.id}-${col.id}`;
                  return (
                    <td key={col.id} className="px-2 py-1.5 align-middle">
                      {col.column_type === "checkbox" ? (
                        <input type="checkbox" checked={!!val}
                          onChange={e => patchCell(row.id, col.id, { value_bool: e.target.checked })}
                          className="w-4 h-4 accent-amber-500 cursor-pointer" />
                      ) : col.column_type === "status" ? (
                        <select value={(val as string) || ""}
                          onChange={e => patchCell(row.id, col.id, { value_text: e.target.value })}
                          className={`text-xs font-semibold px-2 py-1 rounded-full border-0 cursor-pointer focus:outline-none focus:ring-2 focus:ring-amber-300 ${STATUS_COLORS[(val as string) || ""] || "bg-gray-100 text-gray-600"}`}>
                          <option value="">—</option>
                          {col.column_options.map(o => <option key={o} value={o}>{o}</option>)}
                        </select>
                      ) : col.column_type === "select" ? (
                        <select value={(val as string) || ""}
                          onChange={e => patchCell(row.id, col.id, { value_text: e.target.value })}
                          className="text-xs px-2 py-1 rounded-lg border border-gray-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-amber-300">
                          <option value="">—</option>
                          {col.column_options.map(o => <option key={o} value={o}>{o}</option>)}
                        </select>
                      ) : col.column_type === "date" ? (
                        <input type="date" value={(val as string) || ""}
                          onChange={e => patchCell(row.id, col.id, { value_date: e.target.value })}
                          className="text-xs px-2 py-1 rounded-lg border border-gray-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-amber-300" />
                      ) : col.column_type === "number" ? (
                        <input type="number" defaultValue={(val as number) ?? ""}
                          onBlur={e => patchCell(row.id, col.id, { value_number: e.target.value ? Number(e.target.value) : null })}
                          className="text-xs px-2 py-1 rounded-lg border border-gray-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 w-20 focus:outline-none focus:ring-2 focus:ring-amber-300" />
                      ) : col.column_type === "url" ? (
                        <div className="flex items-center gap-1">
                          <input type="text" defaultValue={(val as string) || ""}
                            onBlur={e => patchCell(row.id, col.id, { value_text: e.target.value || null })}
                            placeholder="https://..."
                            className="text-xs px-2 py-1 rounded-lg border border-gray-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 w-32 focus:outline-none focus:ring-2 focus:ring-amber-300" />
                          {val && <a href={val as string} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700"><ExternalLink size={12} /></a>}
                          <button onClick={() => { setUploadTarget({ rowId: row.id, colId: col.id }); fileInputRef.current?.click(); }}
                            className="text-gray-400 hover:text-amber-500 transition-colors"><Upload size={12} /></button>
                        </div>
                      ) : col.column_type === "textarea" ? (
                        <button onClick={() => setExpandedCell({ rowId: row.id, colId: col.id, value: (val as string) || "" })}
                          className="text-xs text-left text-gray-600 dark:text-gray-400 max-w-[180px] truncate hover:text-amber-600 transition-colors">
                          {(val as string) || <span className="text-gray-300 italic">Klik untuk edit...</span>}
                        </button>
                      ) : (
                        <input type="text" defaultValue={(val as string) || ""}
                          onBlur={e => { if (e.target.value !== (val || "")) patchCell(row.id, col.id, { value_text: e.target.value || null }); }}
                          className={`text-xs px-2 py-1 rounded-lg border border-transparent hover:border-gray-200 dark:hover:border-neutral-700 bg-transparent focus:bg-white dark:focus:bg-neutral-800 focus:border-amber-400 focus:outline-none w-full transition-colors ${isSaving ? "opacity-50" : ""}`} />
                      )}
                    </td>
                  );
                })}
                <td className="px-2 py-1.5">
                  <button onClick={() => deleteRow(row.id, row.is_template)}
                    title={row.is_template ? "Row template" : "Hapus row"}
                    className={`opacity-0 group-hover:opacity-100 p-1 rounded transition-all ${row.is_template ? "text-gray-300 cursor-not-allowed" : "text-red-400 hover:text-red-600"}`}>
                    <Trash2 size={13} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <button onClick={addRow} disabled={addingRow}
          className="flex items-center gap-2 w-full px-4 py-2.5 text-xs text-gray-400 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950/20 transition-colors border-t border-[var(--border-subtle)]">
          <Plus size={13} /> {addingRow ? "Menambah..." : "Add Row"}
        </button>
      </div>

      {/* Textarea expand modal */}
      {expandedCell && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-neutral-900 rounded-2xl p-5 w-full max-w-lg shadow-xl">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-100 mb-3">
              {colById[expandedCell.colId]?.column_label || "Catatan"}
            </h3>
            <textarea
              defaultValue={expandedCell.value}
              rows={6}
              autoFocus
              className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-800 resize-y focus:outline-none focus:ring-2 focus:ring-amber-300"
              onBlur={e => {
                if (e.target.value !== expandedCell.value) {
                  patchCell(expandedCell.rowId, expandedCell.colId, { value_text: e.target.value || null });
                }
              }}
            />
            <div className="flex justify-end mt-3">
              <button onClick={() => setExpandedCell(null)}
                className="px-4 py-2 text-sm font-semibold bg-amber-500 hover:bg-amber-600 text-white rounded-xl">
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}

      <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileUpload} />
    </div>
  );
}
