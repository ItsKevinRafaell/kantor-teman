"use client";

import Link from "next/link";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { BarChart3, LayoutDashboard, Flame } from "lucide-react";
import { useDashboardData } from "../../hooks/useDashboard";
import { getScoreColor, getScoreLabel } from "../../lib/leadScore";
import { apiFetch } from "../../lib/api";
import { useAuth } from "../../contexts/AuthContext";
import { getLeadStatusLabel } from "../../types/lead";

const STATUS_COLORS: Record<string, string> = {
  Scraped: "bg-gray-400",
  Contacted: "bg-blue-500",
  Replied: "bg-yellow-500",
  Closed: "bg-emerald-500",
  "Closed/Client": "bg-emerald-500",
  "Closed/Lost": "bg-red-400",
  "Contacted/Sent": "bg-teal-500",
};

const QUICK_ACTIONS = [
  { href: "/leads?tab=scrape", title: "Mulai Scrape Maps", desc: "Cari bisnis baru dari Google Places", bg: "bg-amber-500",
    icon: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg> },
  { href: "/leads", title: "Pipeline Prospek", desc: "Kelola status leads → proposal", bg: "bg-neutral-800 dark:bg-neutral-700",
    icon: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg> },
  { href: "/clients", title: "Klien & Proyek", desc: "Klien aktif, board, workspace", bg: "bg-neutral-800 dark:bg-neutral-700",
    icon: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg> },
  { href: "/documents", title: "Dokumen", desc: "Resmi, laporan klien, arsip", bg: "bg-amber-600",
    icon: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg> },
];

const TABS = [
  { key: "overview" as const, label: "Ringkasan", Icon: LayoutDashboard },
  { key: "analitik" as const, label: "Analitik", Icon: BarChart3 },
];

type Tab = "overview" | "analitik";

function DashboardContent() {
  const { isAdmin } = useAuth();
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as Tab) || "overview";
  const [tab, setTab] = useState<Tab>(initialTab);

  const { analytics, patterns, hotLeads, topScoredLeads, alerts, boardOverview, financeOverview, isLoading } = useDashboardData();

  const maxProduct = analytics ? Math.max(...(analytics.leads_by_product ?? []).map(p => p.count), 1) : 1;
  const maxStatus = analytics ? Math.max(...(analytics.leads_by_status ?? []).map(s => s.count), 1) : 1;
  const urgentCount = hotLeads.length + alerts.length;
  const overdueTasks = boardOverview.reduce((t, p) => t + p.overdue_cards.length, 0);
  const dueSoonTasks = boardOverview.reduce((t, p) => t + p.due_soon_cards.length, 0);
  const formatIdr = (v: number) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(v);

  const STAT_CARDS = [
    { label: "Total Prospek", value: isLoading ? "—" : analytics?.total_leads ?? 0, sub: "Semua prospek tersimpan", color: "text-amber-600", bg: "bg-amber-50 dark:bg-amber-950/20" },
    { label: "Total Klien", value: isLoading ? "—" : analytics?.total_clients ?? 0, sub: "Sudah dikonversi", color: "text-emerald-600", bg: "bg-emerald-50 dark:bg-emerald-950/20" },
    { label: "Tingkat Konversi", value: isLoading ? "—" : `${analytics?.conversion_rate ?? 0}%`, sub: "Klien / Total Prospek", color: "text-amber-600", bg: "bg-amber-50 dark:bg-amber-950/20" },
    { label: "Kategori Aktif", value: isLoading ? "—" : analytics?.leads_by_product?.length ?? 0, sub: "Jenis layanan diminati", color: "text-amber-600", bg: "bg-amber-50 dark:bg-amber-950/20" },
  ];

  async function dismissAlert(id: string) {
    await apiFetch(`/api/alerts/reengagement/${id}/read`, { method: "POST" });
    // SWR will auto-revalidate
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Dashboard</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Ringkasan aktivitas CRM secara real-time.</p>
      </div>

      <div className="flex items-center gap-1 bg-neutral-100 dark:bg-neutral-800 rounded-xl p-1 w-fit">
        {TABS.map(t => {
          const isActive = tab === t.key;
          const badge = t.key === "overview" && urgentCount > 0 ? urgentCount : null;
          return (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${isActive ? "bg-white dark:bg-neutral-900 text-brand-yellow shadow-sm" : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"}`}>
              <t.Icon size={14} />
              {t.label}
              {badge !== null && <span className={`ml-1 px-1.5 py-0.5 rounded text-[10px] font-bold ${isActive ? "bg-brand-yellow/20 text-brand-yellow" : "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400"}`}>{badge}</span>}
            </button>
          );
        })}
      </div>

      {/* OVERVIEW TAB */}
      {tab === "overview" && (
        <div className="space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {STAT_CARDS.map(card => (
              <div key={card.label} className="card-hover p-5 flex flex-col gap-3 cursor-default">
                <div className={`w-10 h-10 rounded-xl ${card.bg} ${card.color} flex items-center justify-center`}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /></svg>
                </div>
                <div>
                  <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
                  <p className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mt-0.5">{card.label}</p>
                  <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5">{card.sub}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Kontrol Operasional - Admin/Owner only */}
          {isAdmin && (
          <div className="card p-5">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300">Kontrol Operasional</h2>
                <p className="text-xs text-neutral-400 mt-0.5">Pantau pekerjaan tim dan kesehatan kas.</p>
              </div>
              <div className="flex gap-2 text-xs font-semibold">
                <Link href="/board" className="text-amber-600 hover:text-amber-700">Board</Link>
                {financeOverview && <Link href="/finance" className="text-amber-600 hover:text-amber-700">Keuangan</Link>}
              </div>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
              {[
                { label: "Proyek Aktif", value: boardOverview.length, alert: false },
                { label: "Task Terlambat", value: overdueTasks, alert: overdueTasks > 0 },
                { label: "Jatuh Tempo <= 3 Hari", value: dueSoonTasks, alert: dueSoonTasks > 0 },
                { label: "Total Saldo", value: financeOverview ? formatIdr(financeOverview.total_balance) : "—", alert: false },
                { label: "Runway", value: financeOverview ? `${financeOverview.financial_runway_months} bulan` : "—", alert: financeOverview ? financeOverview.financial_runway_months < 3 : false },
              ].map(item => (
                <div key={item.label} className={`rounded-xl px-3 py-3 border ${item.alert ? "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900" : "bg-neutral-50 dark:bg-neutral-800/50 border-neutral-100 dark:border-neutral-700"}`}>
                  <p className={`text-lg font-bold ${item.alert ? "text-red-600 dark:text-red-400" : "text-neutral-800 dark:text-neutral-100"}`}>{item.value}</p>
                  <p className="text-[10px] uppercase tracking-wide font-semibold text-neutral-400 mt-1">{item.label}</p>
                </div>
              ))}
            </div>
          </div>
          )}

          {/* Hot Leads */}
          {hotLeads.length > 0 && (
            <div className="card p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                  <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300">Hot Leads — Aktif Sekarang</h2>
                </div>
                <span className="text-[10px] text-neutral-400 uppercase tracking-wide font-bold">{hotLeads.length} lead</span>
              </div>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {hotLeads.map(lead => (
                  <div key={lead.lead_id} className="flex items-center justify-between py-2 px-3 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-100 dark:border-neutral-700">
                    <div className="flex items-center gap-3">
                      <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${lead.status === "online" ? "bg-green-500 animate-pulse" : lead.status === "recent" ? "bg-amber-500" : "bg-neutral-300"}`}></span>
                      <div>
                        <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{lead.business_name}</p>
                        <p className="text-[10px] text-neutral-400">{lead.category || "—"} · {lead.total_opens}x buka · {lead.status === "online" ? "Sedang online" : lead.status === "recent" ? "Baru buka" : "Hari ini"}</p>
                      </div>
                    </div>
                    <a href={`https://wa.me/${lead.phone_number}?text=${encodeURIComponent(`Halo ${lead.business_name}, saya notice Anda baru saja membuka laporan audit digital. Apakah ada pertanyaan?`)}`} target="_blank" rel="noopener noreferrer"
                      className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-[10px] font-bold rounded-lg transition-colors whitespace-nowrap">
                      Follow Up
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Re-engagement alerts */}
          {alerts.length > 0 && (
            <div className="card p-5 border-l-4 border-amber-500">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
                  <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300">Prospek Kembali Aktif</h2>
                </div>
                <span className="text-[10px] text-amber-600 font-bold">{alerts.length} alert</span>
              </div>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {alerts.map(alert => (
                  <div key={alert.id} className="flex items-center justify-between py-2 px-3 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
                    <div>
                      <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{alert.business_name}</p>
                      <p className="text-[10px] text-neutral-500">Buka report lagi setelah <span className="font-bold text-amber-600">{alert.days_since_first_view} hari</span> — kemungkinan masih tertarik</p>
                    </div>
                    <div className="flex gap-2">
                      <a href={`https://wa.me/${alert.phone_number}`} target="_blank" rel="noopener noreferrer"
                        className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-[10px] font-bold rounded-lg transition-colors whitespace-nowrap">WA Sekarang</a>
                      <button onClick={() => dismissAlert(alert.id)} className="p-1.5 text-neutral-400 hover:text-neutral-600 transition-colors">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty state */}
          {hotLeads.length === 0 && alerts.length === 0 && !isLoading && (
            <div className="card p-6 text-center border border-dashed border-neutral-200 dark:border-neutral-700">
              <p className="text-sm text-neutral-400">Tidak ada aktivitas mendesak saat ini.</p>
            </div>
          )}

          {/* Quick Actions */}
          <div>
            <h2 className="text-sm font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-3">Quick Actions</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {QUICK_ACTIONS.map(action => (
                <Link key={action.title} href={action.href}
                  className={`${action.bg} rounded-2xl p-4 text-white flex items-center gap-4 hover:opacity-90 hover:scale-[1.01] transition-all duration-200 shadow-card hover:shadow-card-hover`}>
                  <div className="bg-white/20 rounded-xl p-2 shrink-0">{action.icon}</div>
                  <div>
                    <p className="font-bold text-sm leading-tight">{action.title}</p>
                    <p className="text-white/75 text-xs mt-0.5">{action.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ANALITIK TAB */}
      {tab === "analitik" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card p-6">
              <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-4">Layanan Paling Diminati</h2>
              {isLoading ? (
                <div className="space-y-3">{[...Array(3)].map((_, i) => <div key={i} className="h-6 bg-neutral-100 dark:bg-neutral-800 rounded animate-pulse" />)}</div>
              ) : analytics?.leads_by_product.length === 0 ? (
                <p className="text-xs text-neutral-400 italic">Belum ada data.</p>
              ) : (
                <div className="space-y-3">
                  {analytics?.leads_by_product.map(p => (
                    <div key={p.product}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-medium text-neutral-700 dark:text-neutral-300">{p.product}</span>
                        <span className="text-neutral-400 dark:text-neutral-500">{p.count} leads</span>
                      </div>
                      <div className="h-2 bg-neutral-100 dark:bg-neutral-800 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-amber-500 to-yellow-500 rounded-full transition-all duration-700" style={{ width: `${(p.count / maxProduct) * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="card p-6">
              <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-4">Distribusi Status Pipeline</h2>
              {isLoading ? (
                <div className="space-y-3">{[...Array(3)].map((_, i) => <div key={i} className="h-6 bg-neutral-100 dark:bg-neutral-800 rounded animate-pulse" />)}</div>
              ) : analytics?.leads_by_status.length === 0 ? (
                <p className="text-xs text-neutral-400 italic">Belum ada data.</p>
              ) : (
                <div className="space-y-3">
                  {analytics?.leads_by_status.map(s => (
                    <div key={s.status}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-medium text-neutral-700 dark:text-neutral-300">{getLeadStatusLabel(s.status)}</span>
                        <span className="text-neutral-400">{s.count}</span>
                      </div>
                      <div className="h-2 bg-neutral-100 dark:bg-neutral-800 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full transition-all duration-500 ${STATUS_COLORS[s.status] ?? "bg-gray-400"}`} style={{ width: `${(s.count / maxStatus) * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Top scored leads */}
          {topScoredLeads.length > 0 && (
            <div className="card p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Flame size={14} className="text-red-500" />
                  <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300">Prospek Prioritas Berdasarkan Skor</h2>
                </div>
                <span className="text-[10px] text-neutral-400 uppercase tracking-wide font-bold">{topScoredLeads.length} prioritas</span>
              </div>
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {topScoredLeads.map(lead => {
                  const score = lead.lead_score ?? 0;
                  const color = getScoreColor(score);
                  const tierLabel = getScoreLabel(score);
                  const waMsg = `Halo ${lead.business_name}, saya dari Kantor Teman. Ingin diskusi soal kebutuhan ${lead.product_interest || "digital"} bisnis Anda. Apakah ada waktu?`;
                  return (
                    <div key={lead.id} className="flex items-center justify-between py-2 px-3 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-100 dark:border-neutral-700">
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{lead.business_name}</p>
                            <span className="text-xs font-bold tabular-nums text-neutral-600 dark:text-neutral-400">{score}</span>
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <div className="h-1 w-24 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                              <div className={`h-full ${color}`} style={{ width: `${score}%` }}></div>
                            </div>
                            <p className="text-[10px] text-neutral-400 truncate">{tierLabel} · {lead.product_interest || "—"}</p>
                          </div>
                        </div>
                      </div>
                      <a href={`https://wa.me/${lead.phone_number}?text=${encodeURIComponent(waMsg)}`} target="_blank" rel="noopener noreferrer"
                        className="ml-2 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-[10px] font-bold rounded-lg transition-colors whitespace-nowrap shrink-0">Follow Up</a>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Conversion patterns */}
          <div className="card p-6">
            <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-4">Pola Konversi</h2>
            {!patterns ? (
              <p className="text-xs text-gray-400 italic">Memuat data...</p>
            ) : (
              <div className="space-y-4">
                {patterns.recommendation && (
                  <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-xl p-3">
                    <p className="text-xs text-amber-800 dark:text-amber-300 font-semibold">{patterns.recommendation}</p>
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-[10px] text-zinc-500 uppercase tracking-wide font-bold mb-2">Per Layanan</p>
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
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-neutral-400">Memuat...</div>}>
      <DashboardContent />
    </Suspense>
  );
}
