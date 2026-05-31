"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import FinancePanel from "../../components/finance/FinancePanel";
import SubscriptionsPanel from "../../components/finance/SubscriptionsPanel";
import PaymentMethodsPanel from "../../components/finance/PaymentMethodsPanel";

type Tab = "keuangan" | "langganan" | "pembayaran";

const TABS: { key: Tab; label: string }[] = [
  { key: "keuangan", label: "Keuangan" },
  { key: "langganan", label: "Langganan" },
  { key: "pembayaran", label: "Metode Pembayaran" },
];

function FinanceContent() {
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as Tab) || "keuangan";
  const [tab, setTab] = useState<Tab>(initialTab);

  return (
    <div className="max-w-6xl space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Keuangan & Langganan</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">Kelola dompet, transaksi, dan langganan rutin bisnis dalam satu tempat.</p>
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

      {tab === "keuangan" && <FinancePanel />}
      {tab === "langganan" && <SubscriptionsPanel />}
      {tab === "pembayaran" && <PaymentMethodsPanel />}
    </div>
  );
}

export default function FinancePage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-neutral-400">Memuat...</div>}>
      <FinanceContent />
    </Suspense>
  );
}
