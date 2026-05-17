"use client";

import { useState, useEffect, useRef } from "react";
import { apiFetch } from "../lib/api";

interface JobStatus {
  status: string;
  analyzed?: number;
  sent?: number;
  failed?: number;
  total: number;
  batch_name?: string;
  error?: string;
}

export default function ProgressWidget() {
  const [analysisJob, setAnalysisJob] = useState<JobStatus | null>(null);
  const [blastJob, setBlastJob] = useState<JobStatus | null>(null);
  const analysisInterval = useRef<NodeJS.Timeout | null>(null);
  const blastInterval = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const analysisBatch = localStorage.getItem("analyze_batch");
    if (analysisBatch) {
      pollAnalysis(analysisBatch);
    }

    const blastBatch = localStorage.getItem("blast_batch");
    if (blastBatch) {
      pollBlast(blastBatch);
    }

    return () => {
      if (analysisInterval.current) clearInterval(analysisInterval.current);
      if (blastInterval.current) clearInterval(blastInterval.current);
    };
  }, []);

  function pollAnalysis(batchName: string) {
    setAnalysisJob({ status: "running", analyzed: 0, total: 0, batch_name: batchName });
    analysisInterval.current = setInterval(async () => {
      try {
        const res = await apiFetch(`/api/leads/analyze-status?batch_name=${encodeURIComponent(batchName)}`);
        if (res.ok) {
          const data: JobStatus = await res.json();
          setAnalysisJob(data);
          if (data.status === "done" || data.status === "idle") {
            clearInterval(analysisInterval.current!);
            localStorage.removeItem("analyze_batch");
            setTimeout(() => setAnalysisJob(null), 8000);
          }
        }
      } catch { /* silent */ }
    }, 3000);
  }

  function pollBlast(batchName: string) {
    setBlastJob({ status: "running", sent: 0, total: 0, batch_name: batchName });
    blastInterval.current = setInterval(async () => {
      try {
        const res = await apiFetch(`/api/campaign/blast-status?batch_name=${encodeURIComponent(batchName)}`);
        if (res.ok) {
          const data: JobStatus = await res.json();
          setBlastJob(data);
          if (data.status === "done" || data.status === "error" || data.status === "idle") {
            clearInterval(blastInterval.current!);
            localStorage.removeItem("blast_batch");
            setTimeout(() => setBlastJob(null), 8000);
          }
        }
      } catch { /* silent */ }
    }, 3000);
  }

  // Listen for new jobs started from other components
  useEffect(() => {
    function handleStorage(e: StorageEvent) {
      if (e.key === "analyze_batch" && e.newValue) {
        pollAnalysis(e.newValue);
      }
      if (e.key === "blast_batch" && e.newValue) {
        pollBlast(e.newValue);
      }
    }
    window.addEventListener("storage", handleStorage);

    // Also check periodically for same-tab localStorage changes
    const checkInterval = setInterval(() => {
      const ab = localStorage.getItem("analyze_batch");
      if (ab && !analysisInterval.current) pollAnalysis(ab);
      const bb = localStorage.getItem("blast_batch");
      if (bb && !blastInterval.current) pollBlast(bb);
    }, 2000);

    return () => {
      window.removeEventListener("storage", handleStorage);
      clearInterval(checkInterval);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!analysisJob && !blastJob) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm">
      {analysisJob && analysisJob.status !== "idle" && (
        <div className={`px-4 py-3 rounded-xl shadow-lg border ${analysisJob.status === "done" ? "bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800" : "bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800"}`}>
          <div className="flex items-center gap-2">
            {analysisJob.status === "running" && <div className="w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />}
            {analysisJob.status === "done" && <span className="text-emerald-500">✓</span>}
            <span className={`text-sm font-medium ${analysisJob.status === "done" ? "text-emerald-700 dark:text-emerald-300" : "text-amber-700 dark:text-amber-300"}`}>
              {analysisJob.status === "running"
                ? `AI Analisa: ${analysisJob.analyzed || 0}/${analysisJob.total} leads`
                : `Analisa selesai: ${analysisJob.analyzed || 0}/${analysisJob.total} leads`}
            </span>
          </div>
          {analysisJob.status === "running" && analysisJob.total > 0 && (
            <div className="w-full h-1.5 bg-amber-100 dark:bg-amber-900/50 rounded-full overflow-hidden mt-2">
              <div className="h-full bg-amber-500 rounded-full transition-all duration-500" style={{ width: `${((analysisJob.analyzed || 0) / analysisJob.total) * 100}%` }} />
            </div>
          )}
        </div>
      )}

      {blastJob && blastJob.status !== "idle" && (
        <div className={`px-4 py-3 rounded-xl shadow-lg border ${blastJob.status === "done" ? "bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800" : blastJob.status === "error" ? "bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800" : "bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800"}`}>
          <div className="flex items-center gap-2">
            {blastJob.status === "running" && <div className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />}
            {blastJob.status === "done" && <span className="text-emerald-500">✓</span>}
            {blastJob.status === "error" && <span className="text-red-500">✗</span>}
            <span className={`text-sm font-medium ${blastJob.status === "done" ? "text-emerald-700 dark:text-emerald-300" : blastJob.status === "error" ? "text-red-700 dark:text-red-300" : "text-blue-700 dark:text-blue-300"}`}>
              {blastJob.status === "running"
                ? `WA Blast: ${blastJob.sent || 0}/${blastJob.total} terkirim`
                : blastJob.status === "done"
                ? `Blast selesai: ${blastJob.sent || 0}/${blastJob.total} terkirim`
                : `Blast error: ${blastJob.error || "Unknown"}`}
            </span>
          </div>
          {blastJob.status === "running" && blastJob.total > 0 && (
            <div className="w-full h-1.5 bg-blue-100 dark:bg-blue-900/50 rounded-full overflow-hidden mt-2">
              <div className="h-full bg-blue-500 rounded-full transition-all duration-500" style={{ width: `${((blastJob.sent || 0) / blastJob.total) * 100}%` }} />
            </div>
          )}
          {blastJob.failed && blastJob.failed > 0 && (
            <p className="text-[10px] text-red-500 mt-1">{blastJob.failed} gagal kirim</p>
          )}
        </div>
      )}
    </div>
  );
}
