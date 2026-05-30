"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import CampaignsPanel from "../../../components/marketing/CampaignsPanel";
import QuotaPanel from "../../../components/marketing/QuotaPanel";

type Tab = "campaigns" | "quota";

const TABS: { key: Tab; label: string }[] = [
  { key: "campaigns", label: "Campaigns" },
  { key: "quota", label: "Provider & Kuota" },
];

function CampaignsContent() {
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as Tab) || "campaigns";
  const [tab, setTab] = useState<Tab>(initialTab);

  return (
    <div className="max-w-6xl space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Campaigns & Kuota</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">Pantau iklan berbayar, biaya operasional, dan sisa kuota provider.</p>
      </div>

      <div className="flex items-center gap-1 bg-neutral-100 dark:bg-neutral-800 rounded-xl p-1 w-fit">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              tab === t.key
                ? "bg-white dark:bg-neutral-900 text-brand-yellow shadow-sm"
                : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "campaigns" && <CampaignsPanel />}
      {tab === "quota" && <QuotaPanel />}
    </div>
  );
}

export default function CampaignsPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-neutral-400">Memuat...</div>}>
      <CampaignsContent />
    </Suspense>
  );
}
