"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import Breadcrumb from "../../components/Breadcrumb";
import ScrapePanel from "../../components/leads/ScrapePanel";

const LeadsTable = dynamic(() => import("../../components/LeadsTable"), { ssr: false });
const LeadsMap = dynamic(() => import("../../components/leads/LeadsMap"), { ssr: false });

type Tab = "tabel" | "peta" | "scrape";

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  {
    key: "tabel",
    label: "Tabel",
    icon: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>,
  },
  {
    key: "peta",
    label: "Peta",
    icon: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" /></svg>,
  },
  {
    key: "scrape",
    label: "Scrape",
    icon: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>,
  },
];

function LeadsContent() {
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as Tab) || "tabel";
  const initialBatch = searchParams.get("batch") || undefined;

  const [tab, setTab] = useState<Tab>(initialTab);
  const [batch, setBatch] = useState<string | undefined>(initialBatch);

  function handleBatchSelect(batchName: string) {
    setBatch(batchName);
    setTab("tabel");
  }

  return (
    <div className="max-w-6xl space-y-4">
      <Breadcrumb items={[{ label: "Leads" }]} showBack backHref="/" />
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-neutral-50">Leads</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">Scrape, kelola, dan visualisasi semua leads.</p>
        </div>
      </div>

      <div className="flex items-center gap-1 bg-neutral-100 dark:bg-neutral-800 rounded-xl p-1 w-fit">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              tab === t.key
                ? "bg-white dark:bg-neutral-900 text-brand-yellow shadow-sm"
                : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {tab === "tabel" && (
        <LeadsTable initialBatch={batch} />
      )}

      {tab === "peta" && (
        <LeadsMap />
      )}

      {tab === "scrape" && (
        <ScrapePanel onBatchSelect={handleBatchSelect} />
      )}
    </div>
  );
}

export default function LeadsPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-neutral-400">Memuat...</div>}>
      <LeadsContent />
    </Suspense>
  );
}
