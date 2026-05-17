"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "../../../lib/api";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";

interface AuditEntry {
  id: number;
  timestamp: string;
  actor: string;
  action: string;
  table_name: string;
  record_id: string;
  details: Record<string, unknown> | null;
}

const ACTION_COLORS: Record<string, string> = {
  CREATE: "text-emerald-400",
  UPDATE: "text-amber-400",
  DELETE: "text-red-400",
  RESTORE: "text-blue-400",
};

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchLogs = useCallback(async () => {
    try {
      const res = await apiFetch("/api/audit-logs?limit=200");
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs);
        setTotal(data.total);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs();
    intervalRef.current = setInterval(fetchLogs, 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchLogs]);

  function formatTime(ts: string) {
    const d = new Date(ts);
    return d.toLocaleString("id-ID", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/settings" className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-xl transition-colors">
            <ArrowLeft size={18} />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Audit Log</h1>
            <p className="text-sm text-gray-400 mt-0.5">Riwayat aktivitas sistem — realtime.</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">{total} total entries</span>
          <button onClick={fetchLogs} className="p-2 text-gray-400 hover:text-brand-yellow hover:bg-brand-yellow/10 rounded-xl transition-colors">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      <div className="bg-gray-950 dark:bg-gray-950 rounded-2xl border border-gray-800 shadow-lg overflow-hidden font-mono">
        <div className="px-4 py-2.5 border-b border-gray-800 flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="ml-3 text-xs text-gray-500">audit_log — kantor_teman</span>
        </div>

        <div className="max-h-[70vh] overflow-y-auto p-4 space-y-1">
          {loading && (
            <div className="text-gray-500 text-sm animate-pulse">Loading audit entries...</div>
          )}
          {!loading && logs.length === 0 && (
            <div className="text-gray-500 text-sm">Belum ada aktivitas tercatat.</div>
          )}
          {logs.map((log) => (
            <div key={log.id} className="flex items-start gap-3 text-xs leading-relaxed hover:bg-gray-900/50 px-2 py-1 rounded transition-colors">
              <span className="text-gray-600 shrink-0 w-[145px]">{formatTime(log.timestamp)}</span>
              <span className={`font-bold shrink-0 w-[70px] ${ACTION_COLORS[log.action] || "text-gray-400"}`}>{log.action}</span>
              <span className="text-amber-400 shrink-0 w-[100px]">{log.table_name}</span>
              <span className="text-cyan-400 shrink-0 w-[80px] truncate">#{log.record_id}</span>
              <span className="text-gray-400 shrink-0 w-[80px]">{log.actor}</span>
              <span className="text-gray-600 truncate flex-1">
                {log.details ? JSON.stringify(log.details) : "—"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
