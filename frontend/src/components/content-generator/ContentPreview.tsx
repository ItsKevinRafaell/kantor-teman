"use client";

import { useState } from "react";
import { copyToClipboard, markdownToHtml } from "./types";
import { exportToDocx } from "./types";
import { publishArticleToCms } from "./cmsUtils";
import type { ContentGenResult } from "./types";

interface Props {
  result: ContentGenResult | null;
  showToast: (m: string, t?: "success" | "error" | "info") => void;
  onClose: () => void;
}

export default function ContentPreview({ result, showToast, onClose }: Props) {
  const [exporting, setExporting] = useState(false);
  const [publishing, setPublishing] = useState(false);

  if (!result) return null;
  const r = result;

  async function handleExport() {
    setExporting(true);
    try {
      await exportToDocx(r);
      showToast("DOCX berhasil diexport!");
    } catch {
      showToast("Gagal export DOCX", "error");
    } finally {
      setExporting(false);
    }
  }

  async function handlePublish() {
    setPublishing(true);
    try {
      await publishArticleToCms(r);
      showToast("Artikel terkirim ke CMS sebagai draft!");
    } catch (e: unknown) {
      showToast(`Gagal kirim ke CMS: ${e instanceof Error ? e.message : "Error tidak diketahui"}`, "error");
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div className="rounded-2xl border border-amber-100 bg-white p-5 shadow-sm dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 text-base">{result.title}</h3>
        <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600">&times;</button>
      </div>
      {result.focus_keyword && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-950/30 dark:text-amber-300">{result.focus_keyword}</span>
          {result.secondary_keywords?.map((k, i) => (
            <span key={i} className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs text-neutral-700 dark:bg-neutral-800/50 dark:text-neutral-300">{k}</span>
          ))}
        </div>
      )}
      <div className="max-h-96 overflow-y-auto rounded-xl bg-white p-4 ring-1 ring-amber-100 dark:bg-neutral-800/60 dark:ring-amber-900/30">
        <div className="prose-content" dangerouslySetInnerHTML={{ __html: markdownToHtml(result.body) }} />
      </div>
      <div className="flex gap-2 flex-wrap mt-4">
        <button onClick={() => copyToClipboard(`# ${result.title}\n\n${result.body}`)}
          className="flex-1 py-2 text-xs rounded-lg bg-gray-100 dark:bg-gray-800 text-neutral-600 hover:bg-gray-200 dark:hover:bg-gray-700">Copy Markdown</button>
        <button onClick={() => copyToClipboard(result.meta_description)}
          className="flex-1 py-2 text-xs rounded-lg bg-neutral-50 dark:bg-neutral-800/20 text-neutral-700 hover:bg-neutral-100">Copy Meta</button>
        <button onClick={handleExport} disabled={exporting}
          className="flex-1 py-2 text-xs rounded-lg bg-neutral-50 dark:bg-neutral-800/20 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 disabled:opacity-50 flex items-center justify-center gap-1">
          {exporting ? <><div className="w-3 h-3 border-2 border-neutral-500 border-t-transparent rounded-full animate-spin" />Exporting...</> : "Export DOCX"}
        </button>
        <button onClick={handlePublish} disabled={publishing}
          className="flex-1 py-2 text-xs rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 disabled:opacity-50 flex items-center justify-center gap-1">
          {publishing ? <><div className="w-3 h-3 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />Mengirim...</> : "Kirim ke CMS"}
        </button>
      </div>
    </div>
  );
}
