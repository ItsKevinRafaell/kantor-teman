"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";

interface TemplateRow {
  template_id: string;
  template_name: string;
  sent: number;
  delivered: number;
  read: number;
  replied: number;
  closed: number;
  reply_rate: number;
  conversion_rate: number;
}

interface Analytics {
  period_days: number;
  total: {
    sent: number;
    delivered: number;
    read: number;
    replied: number;
    closed: number;
    reply_rate: number;
    conversion_rate: number;
  };
  by_template: TemplateRow[];
  top_performer: { template_name: string; reply_rate: number } | null;
}

const PERIODS = [
  { label: "7 hari", days: 7 },
  { label: "30 hari", days: 30 },
  { label: "90 hari", days: 90 },
];

function FunnelBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <div className="w-24 text-xs text-gray-500 text-right shrink-0">{label}</div>
      <div className="flex-1 bg-gray-100 dark:bg-neutral-800 rounded-full h-6 overflow-hidden">
        <div className={`h-full ${color} rounded-full flex items-center px-3 transition-all duration-500`} style={{ width: `${Math.max(pct, 2)}%` }}>
          <span className="text-white text-xs font-bold whitespace-nowrap">{value.toLocaleString()}</span>
        </div>
      </div>
      <div className="w-12 text-xs text-gray-400 shrink-0">{pct}%</div>
    </div>
  );
}

export default function BlastAnalyticsPage() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<"reply_rate" | "conversion_rate" | "sent">("reply_rate");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/api/blast/analytics?days=${days}`);
      if (res.ok) setData(await res.json());
    } finally { setLoading(false); }
  }, [days]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const sorted = data ? [...data.by_template].sort((a, b) => b[sortBy] - a[sortBy]) : [];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Blast Analytics</h1>
          <p className="text-sm text-gray-500 mt-1">Performa template WA Blast — funnel Sent → Replied → Closed.</p>
        </div>
        <div className="flex gap-2">
          {PERIODS.map(p => (
            <button key={p.days} onClick={() => setDays(p.days)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${days === p.days ? "bg-amber-500 text-white" : "bg-gray-100 dark:bg-neutral-800 text-gray-600 dark:text-neutral-300 hover:bg-gray-200"}`}>
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-gray-400">Memuat...</p>
      ) : !data ? (
        <p className="text-sm text-gray-400">Gagal memuat data.</p>
      ) : (
        <>
          {/* Top performer insight */}
          {data.top_performer && data.total.sent > 0 && (
            <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-2xl p-4">
              <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                🏆 Top performer: <span className="font-black">{data.top_performer.template_name}</span> — {data.top_performer.reply_rate}% reply rate
              </p>
            </div>
          )}

          {/* Grand total stats */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {[
              { label: "Sent", value: data.total.sent, color: "text-gray-700 dark:text-gray-300" },
              { label: "Delivered", value: data.total.delivered, color: "text-blue-600" },
              { label: "Read", value: data.total.read, color: "text-purple-600" },
              { label: "Replied", value: data.total.replied, color: "text-amber-600" },
              { label: "Closed", value: data.total.closed, color: "text-green-600" },
            ].map(s => (
              <div key={s.label} className="bg-white dark:bg-neutral-900 border border-[var(--border-default)] rounded-xl p-3 text-center">
                <p className={`text-xl font-black ${s.color}`}>{s.value.toLocaleString()}</p>
                <p className="text-xs text-gray-500 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Funnel chart */}
          {data.total.sent > 0 && (
            <div className="bg-white dark:bg-neutral-900 border border-[var(--border-default)] rounded-2xl p-5">
              <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300 mb-4 uppercase tracking-wide">Funnel</h2>
              <div className="space-y-2">
                <FunnelBar label="Sent" value={data.total.sent} max={data.total.sent} color="bg-gray-400" />
                <FunnelBar label="Delivered" value={data.total.delivered} max={data.total.sent} color="bg-blue-500" />
                <FunnelBar label="Read" value={data.total.read} max={data.total.sent} color="bg-purple-500" />
                <FunnelBar label="Replied" value={data.total.replied} max={data.total.sent} color="bg-amber-500" />
                <FunnelBar label="Closed" value={data.total.closed} max={data.total.sent} color="bg-green-500" />
              </div>
              <div className="flex gap-4 mt-4 text-xs text-gray-500">
                <span>Reply rate: <strong className="text-amber-600">{data.total.reply_rate}%</strong></span>
                <span>Conversion: <strong className="text-green-600">{data.total.conversion_rate}%</strong></span>
              </div>
            </div>
          )}

          {/* Per-template table */}
          <div className="bg-white dark:bg-neutral-900 border border-[var(--border-default)] rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-[var(--border-default)]">
              <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300 uppercase tracking-wide">Per Template</h2>
              <div className="flex gap-2">
                {(["reply_rate", "conversion_rate", "sent"] as const).map(s => (
                  <button key={s} onClick={() => setSortBy(s)}
                    className={`px-2.5 py-1 text-[10px] font-bold rounded-lg transition-colors ${sortBy === s ? "bg-amber-500 text-white" : "bg-gray-100 dark:bg-neutral-800 text-gray-500 hover:bg-gray-200"}`}>
                    {s === "reply_rate" ? "Reply Rate" : s === "conversion_rate" ? "Conversion" : "Volume"}
                  </button>
                ))}
              </div>
            </div>
            {sorted.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-8">Belum ada data blast dalam periode ini.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-neutral-800">
                  <tr>
                    {["Template", "Sent", "Delivered", "Read", "Replied", "Closed", "Reply %", "Conv %"].map(h => (
                      <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]">
                  {sorted.map((row, i) => (
                    <tr key={row.template_id} className="hover:bg-gray-50 dark:hover:bg-neutral-800 transition-colors">
                      <td className="px-4 py-3 font-medium text-neutral-800 dark:text-neutral-200 max-w-[200px] truncate">
                        {i === 0 && <span className="mr-1">🏆</span>}{row.template_name}
                      </td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{row.sent}</td>
                      <td className="px-4 py-3 text-blue-600">{row.delivered}</td>
                      <td className="px-4 py-3 text-purple-600">{row.read}</td>
                      <td className="px-4 py-3 text-amber-600">{row.replied}</td>
                      <td className="px-4 py-3 text-green-600">{row.closed}</td>
                      <td className="px-4 py-3">
                        <span className={`font-bold ${row.reply_rate >= 20 ? "text-green-600" : row.reply_rate >= 10 ? "text-amber-600" : "text-gray-500"}`}>
                          {row.reply_rate}%
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`font-bold ${row.conversion_rate >= 5 ? "text-green-600" : "text-gray-500"}`}>
                          {row.conversion_rate}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
