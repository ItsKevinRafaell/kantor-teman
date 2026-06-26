import { useState } from "react";
import { X, RotateCcw, Clock, FileText } from "lucide-react";

interface Version {
  id: string;
  version_number: number;
  variables_json: Record<string, string>;
  html_content: string | null;
  change_summary: string;
  created_at: string;
  created_by: string | null;
}

interface VersionHistoryPanelProps {
  open: boolean;
  versions: Version[];
  loading: boolean;
  onRollback: (versionId: string) => Promise<void>;
  onClose: () => void;
}

export default function VersionHistoryPanel({ open, versions, loading, onRollback, onClose }: VersionHistoryPanelProps) {
  const [rollingBack, setRollingBack] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  async function handleRollback(versionId: string) {
    setRollingBack(versionId);
    try {
      await onRollback(versionId);
      setToast({ message: "Berhasil rollback ke versi sebelumnya", type: "success" });
    } catch (e: unknown) {
      setToast({ message: e instanceof Error ? e.message : "Gagal rollback", type: "error" });
    } finally {
      setRollingBack(null);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end bg-black/40" onClick={onClose}>
      <div className="w-full max-w-md h-full bg-white dark:bg-neutral-900 shadow-xl overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-neutral-800 p-4 sticky top-0 bg-white dark:bg-neutral-900 z-10">
          <div className="flex items-center gap-2">
            <Clock size={18} className="text-amber-600" />
            <h2 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">Riwayat Versi</h2>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-lg">
            <X size={16} />
          </button>
        </div>

        <div className="p-4 space-y-3">
          {loading ? (
            <p className="text-sm text-gray-400 text-center py-8">Memuat riwayat versi...</p>
          ) : versions.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <FileText size={32} className="mx-auto mb-2 opacity-40" />
              <p className="text-sm">Belum ada versi tersimpan</p>
            </div>
          ) : (
            versions.map(v => (
              <div key={v.id} className={`rounded-xl border p-4 transition-colors ${v.version_number === 0 ? "border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/20" : "border-gray-200 dark:border-neutral-700 bg-white dark:bg-neutral-800"}`}>
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      {v.version_number === 0 ? (
                        <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">Asli</span>
                      ) : (
                        <span className="text-xs font-bold text-amber-600 dark:text-amber-400">v{v.version_number}</span>
                      )}
                      <span className="text-xs text-gray-400">—</span>
                      <span className="text-xs text-gray-500 truncate">{v.change_summary}</span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(v.created_at).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                      {v.created_by && ` oleh ${v.created_by}`}
                    </p>
                  </div>
                  {v.version_number > 0 && (
                    <button onClick={() => handleRollback(v.id)} disabled={rollingBack === v.id}
                      className="flex items-center gap-1 px-2 py-1 text-xs font-semibold text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors disabled:opacity-50 ml-2 shrink-0">
                      <RotateCcw size={12} /> Rollback
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {toast && (
          <div className={`mx-4 mb-4 rounded-xl p-3 text-sm font-medium ${toast.type === "success" ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300" : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300"}`}>
            {toast.message}
          </div>
        )}
      </div>
    </div>
  );
}
