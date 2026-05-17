"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { apiFetch } from "../../lib/api";

interface Analytics {
  total_leads: number;
  total_clients: number;
  conversion_rate: number;
  leads_by_product: { product: string; count: number }[];
  leads_by_status: { status: string; count: number }[];
}

const STATUS_COLORS: Record<string, string> = {
  Scraped: "bg-gray-400",
  Contacted: "bg-blue-500",
  Replied: "bg-yellow-500",
  Closed: "bg-emerald-500",
  "Closed/Client": "bg-amber-500",
  "Contacted/Sent": "bg-teal-500",
};

export default function ReportsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchData = useCallback(() => {
    apiFetch("/api/analytics").then((r) => r.json()).then(setData).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchData();
    intervalRef.current = setInterval(fetchData, 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchData]);

  const maxProduct = data ? Math.max(...data.leads_by_product.map((p) => p.count), 1) : 1;
  const maxStatus = data ? Math.max(...data.leads_by_status.map((s) => s.count), 1) : 1;

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-[#fcfaf7]">Laporan & Analytics</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Data real-time dari database CRM.</p>
      </div>

      {loading && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white dark:bg-[#242423] rounded-2xl border border-[var(--border-default)] p-5 animate-pulse">
              <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded w-1/2 mb-2" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-3/4" />
            </div>
          ))}
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "Total Leads", value: data.total_leads, color: "text-amber-600", bg: "bg-amber-50" },
              { label: "Total Klien", value: data.total_clients, color: "text-emerald-600", bg: "bg-emerald-50" },
              { label: "Conversion Rate", value: `${data.conversion_rate}%`, color: "text-amber-600", bg: "bg-amber-50" },
              { label: "Kategori Aktif", value: data.leads_by_product.length, color: "text-amber-600", bg: "bg-amber-50" },
            ].map((card) => (
              <div key={card.label} className="bg-white dark:bg-[#242423] rounded-2xl border border-[var(--border-default)] shadow-sm p-5 hover:shadow-md hover:scale-[1.02] transition-all duration-200">
                <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">{card.label}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-[#242423] rounded-2xl border border-[var(--border-default)] shadow-sm p-6">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Layanan Paling Diminati</h2>
              {data.leads_by_product.length === 0 ? (
                <p className="text-xs text-gray-300 italic">Belum ada data.</p>
              ) : (
                <div className="space-y-3">
                  {data.leads_by_product.map((p) => (
                    <div key={p.product}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-medium text-gray-700 dark:text-gray-300">{p.product}</span>
                        <span className="text-gray-400">{p.count} leads</span>
                      </div>
                      <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-amber-500 to-yellow-500 rounded-full transition-all duration-500"
                          style={{ width: `${(p.count / maxProduct) * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-white dark:bg-[#242423] rounded-2xl border border-[var(--border-default)] shadow-sm p-6">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Distribusi Status Pipeline</h2>
              {data.leads_by_status.length === 0 ? (
                <p className="text-xs text-gray-300 italic">Belum ada data.</p>
              ) : (
                <div className="space-y-3">
                  {data.leads_by_status.map((s) => (
                    <div key={s.status}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-medium text-gray-700 dark:text-gray-300">{s.status}</span>
                        <span className="text-gray-400">{s.count}</span>
                      </div>
                      <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full transition-all duration-500 ${STATUS_COLORS[s.status] ?? "bg-gray-400"}`}
                          style={{ width: `${(s.count / maxStatus) * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Win/Loss Pattern Analysis */}
          <div className="bg-white dark:bg-[#242423] rounded-2xl border border-[var(--border-default)] shadow-sm p-6 col-span-full">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Conversion Pattern Analysis</h2>
            <PatternsSection />
          </div>
        </>
      )}
    </div>
  );
}

function PatternsSection() {
  const [patterns, setPatterns] = useState<{ by_category: { segment: string; total: number; converted: number; rate: number }[]; by_city: { segment: string; total: number; converted: number; rate: number }[]; by_rating: { segment: string; total: number; converted: number; rate: number }[]; recommendation: string } | null>(null);

  useEffect(() => {
    apiFetch("/api/analytics/patterns").then(r => r.json()).then(setPatterns).catch(() => {});
  }, []);

  if (!patterns) return <p className="text-xs text-gray-400 italic">Memuat data...</p>;

  return (
    <div className="space-y-4">
      {patterns.recommendation && (
        <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-xl p-3">
          <p className="text-xs text-amber-800 dark:text-amber-300 font-semibold">{patterns.recommendation}</p>
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wide font-bold mb-2">Per Kategori</p>
          <div className="space-y-1.5">
            {patterns.by_category.slice(0, 5).map(p => (
              <div key={p.segment} className="flex justify-between items-center text-xs">
                <span className="text-zinc-700 dark:text-zinc-300 truncate max-w-[120px]">{p.segment}</span>
                <span className={`font-bold ${p.rate > 10 ? "text-green-600" : p.rate > 0 ? "text-amber-600" : "text-zinc-400"}`}>{p.rate}%</span>
              </div>
            ))}
            {patterns.by_category.length === 0 && <p className="text-[10px] text-zinc-400 italic">Belum cukup data</p>}
          </div>
        </div>
        <div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wide font-bold mb-2">Per Kota</p>
          <div className="space-y-1.5">
            {patterns.by_city.slice(0, 5).map(p => (
              <div key={p.segment} className="flex justify-between items-center text-xs">
                <span className="text-zinc-700 dark:text-zinc-300 truncate max-w-[120px]">{p.segment}</span>
                <span className={`font-bold ${p.rate > 10 ? "text-green-600" : p.rate > 0 ? "text-amber-600" : "text-zinc-400"}`}>{p.rate}%</span>
              </div>
            ))}
            {patterns.by_city.length === 0 && <p className="text-[10px] text-zinc-400 italic">Belum cukup data</p>}
          </div>
        </div>
        <div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wide font-bold mb-2">Per Rating</p>
          <div className="space-y-1.5">
            {patterns.by_rating.map(p => (
              <div key={p.segment} className="flex justify-between items-center text-xs">
                <span className="text-zinc-700 dark:text-zinc-300">{p.segment}</span>
                <span className={`font-bold ${p.rate > 10 ? "text-green-600" : p.rate > 0 ? "text-amber-600" : "text-zinc-400"}`}>{p.rate}% <span className="text-zinc-400 font-normal">({p.converted}/{p.total})</span></span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
