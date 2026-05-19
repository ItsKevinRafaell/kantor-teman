"use client";

import { useState, useEffect, useRef } from "react";
import { apiFetch } from "../../lib/api";

interface Job {
  type: "analysis" | "blast";
  batch_name: string;
  status: string;
  total: number;
  analyzed?: number;
  sent?: number;
  failed?: number;
  error?: string;
}

export default function TasksPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  async function fetchJobs() {
    try {
      const res = await apiFetch("/api/background-jobs");
      if (res.ok) setJobs(await res.json());
    } catch { /* silent */ }
    finally { setLoading(false); }
  }

  useEffect(() => {
    fetchJobs();
    intervalRef.current = setInterval(fetchJobs, 3000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, []);

  const running = jobs.filter(j => j.status === "running");
  const completed = jobs.filter(j => j.status === "done");
  const errored = jobs.filter(j => j.status === "error");

  function getProgress(job: Job) {
    if (job.type === "analysis") return { current: job.analyzed || 0, total: job.total };
    return { current: job.sent || 0, total: job.total };
  }

  function getLabel(job: Job) {
    if (job.type === "analysis") return "AI Analisa";
    return "WA Blast";
  }

  function getColor(job: Job) {
    if (job.type === "analysis") return { bg: "bg-amber-500", light: "bg-amber-100 dark:bg-amber-900/50", text: "text-amber-700 dark:text-amber-300", badge: "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300" };
    return { bg: "bg-blue-500", light: "bg-blue-100 dark:bg-blue-900/50", text: "text-blue-700 dark:text-blue-300", badge: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300" };
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Background Tasks</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Monitor semua proses yang berjalan di background (AI Analisa, WA Blast).</p>
      </div>

      {loading && (
        <div className="bg-white dark:bg-[#242423] rounded-2xl border border-gray-100 dark:border-gray-700 p-6">
          <div className="animate-pulse space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 dark:bg-gray-800 rounded-xl" />
            ))}
          </div>
        </div>
      )}

      {!loading && jobs.length === 0 && (
        <div className="bg-white dark:bg-[#242423] rounded-2xl border border-gray-100 dark:border-gray-700 p-8 text-center">
          <p className="text-sm text-gray-400">Tidak ada background task yang sedang berjalan atau tercatat.</p>
          <p className="text-xs text-gray-400 mt-1">Task akan muncul saat kamu menjalankan AI Analisa atau WA Blast.</p>
        </div>
      )}

      {running.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            Sedang Berjalan ({running.length})
          </h2>
          {running.map((job) => {
            const { current, total } = getProgress(job);
            const color = getColor(job);
            const pct = total > 0 ? Math.round((current / total) * 100) : 0;
            return (
              <div key={`${job.type}-${job.batch_name}`} className="bg-white dark:bg-[#242423] rounded-2xl border border-gray-100 dark:border-gray-700 p-4 sm:p-5">
                <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin text-amber-500 shrink-0" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${color.badge}`}>{getLabel(job)}</span>
                        <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{job.batch_name}</span>
                      </div>
                      <p className="text-xs text-neutral-400 mt-0.5">{current}/{total} selesai</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 sm:w-48">
                    <div className={`flex-1 h-2 ${color.light} rounded-full overflow-hidden`}>
                      <div className={`h-full ${color.bg} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
                    </div>
                    <span className={`text-xs font-bold ${color.text} whitespace-nowrap`}>{pct}%</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {completed.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300 flex items-center gap-2">
            <span className="text-emerald-500">&#10003;</span>
            Selesai ({completed.length})
          </h2>
          {completed.map((job) => {
            const { current, total } = getProgress(job);
            const color = getColor(job);
            return (
              <div key={`${job.type}-${job.batch_name}`} className="bg-white dark:bg-[#242423] rounded-2xl border border-gray-100 dark:border-gray-700 p-4 sm:p-5 opacity-80">
                <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span className="text-emerald-500 shrink-0">&#10003;</span>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${color.badge}`}>{getLabel(job)}</span>
                        <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 truncate">{job.batch_name}</span>
                      </div>
                    </div>
                  </div>
                  <span className="text-xs text-emerald-600 font-semibold whitespace-nowrap">{current}/{total} selesai</span>
                  {job.failed && job.failed > 0 && <span className="text-xs text-red-500 font-medium">{job.failed} gagal</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {errored.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300 flex items-center gap-2">
            <span className="text-red-500">&#10007;</span>
            Error ({errored.length})
          </h2>
          {errored.map((job) => {
            const color = getColor(job);
            return (
              <div key={`${job.type}-${job.batch_name}`} className="bg-white dark:bg-[#242423] rounded-2xl border border-red-200 dark:border-red-800 p-4 sm:p-5">
                <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span className="text-red-500 shrink-0">&#10007;</span>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${color.badge}`}>{getLabel(job)}</span>
                        <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 truncate">{job.batch_name}</span>
                      </div>
                      {job.error && <p className="text-xs text-red-500 mt-1 truncate">{job.error}</p>}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
