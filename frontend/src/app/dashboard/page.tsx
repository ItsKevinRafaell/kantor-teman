"use client";

import Link from "next/link";
import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "../../lib/api";

interface Analytics {
  total_leads: number;
  total_clients: number;
  conversion_rate: number;
  leads_by_product: { product: string; count: number }[];
  leads_by_status: { status: string; count: number }[];
}

const QUICK_ACTIONS = [
  {
    href: "/scraper",
    title: "Mulai Scrape Maps",
    desc: "Cari bisnis baru dari Google Places",
    gradient: "from-amber-500 to-yellow-600",
    icon: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>,
  },
  {
    href: "/contacts",
    title: "Lihat Pipeline CRM",
    desc: "Kelola dan update status semua leads",
    gradient: "from-emerald-500 to-teal-600",
    icon: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>,
  },
  {
    href: "/clients",
    title: "Buku Klien",
    desc: "Lihat dan kelola klien aktif",
    gradient: "from-amber-500 to-rose-500",
    icon: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>,
  },
];

export default function DashboardPage() {
  const router = useRouter();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [hotLeads, setHotLeads] = useState<{ lead_id: number; business_name: string; phone_number: string; category: string | null; status: string; last_active: string; total_opens: number; proposal_slug: string | null }[]>([]);
  const [alerts, setAlerts] = useState<{ id: string; lead_id: number; business_name: string; phone_number: string; category: string | null; triggered_at: string; days_since_first_view: number; proposal_slug: string | null }[]>([]);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const match = document.cookie.match(/(?:^|;\s*)kt_token=([^;]*)/);
    if (!match) router.replace("/login");
  }, [router]);

  const fetchAnalytics = useCallback(() => {
    apiFetch("/api/analytics")
      .then((r) => {
        if (r.status === 401 || r.status === 403) { router.replace("/login"); return null; }
        return r.ok ? r.json() : null;
      })
      .then((data) => { if (data) setAnalytics(data); })
      .finally(() => setLoading(false));
    apiFetch("/api/leads/hot")
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data) setHotLeads(data); })
      .catch(() => {});
    apiFetch("/api/alerts/reengagement")
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data) setAlerts(data); })
      .catch(() => {});
  }, [router]);

  useEffect(() => {
    fetchAnalytics();
    intervalRef.current = setInterval(fetchAnalytics, 60000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchAnalytics]);

  const maxProduct = analytics ? Math.max(...(analytics.leads_by_product ?? []).map((p) => p.count), 1) : 1;

  const STAT_CARDS = [
    { label: "Total Leads", value: loading ? "—" : analytics?.total_leads ?? 0, sub: "Semua prospek tersimpan", color: "text-amber-600", bg: "bg-amber-50" },
    { label: "Total Klien", value: loading ? "—" : analytics?.total_clients ?? 0, sub: "Sudah dikonversi", color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Conversion Rate", value: loading ? "—" : `${analytics?.conversion_rate ?? 0}%`, sub: "Klien / Total Leads", color: "text-amber-600", bg: "bg-amber-50" },
    { label: "Kategori Aktif", value: loading ? "—" : analytics?.leads_by_product?.length ?? 0, sub: "Jenis layanan diminati", color: "text-amber-600", bg: "bg-amber-50" },
  ];

  return (
    <div className="space-y-8 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Dashboard</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">Ringkasan aktivitas CRM Kantor Teman secara real-time.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STAT_CARDS.map((card) => (
          <div key={card.label}
            className="card-hover p-5 flex flex-col gap-3 cursor-default">
            <div className={`w-10 h-10 rounded-xl ${card.bg} dark:bg-opacity-20 ${card.color} flex items-center justify-center`}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" />
              </svg>
            </div>
            <div>
              <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
              <p className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mt-0.5">{card.label}</p>
              <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5">{card.sub}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Hot Leads */}
      {hotLeads.length > 0 && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
              <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300">Hot Leads — Sedang Aktif</h2>
            </div>
            <span className="text-[10px] text-neutral-400 uppercase tracking-wide font-bold">{hotLeads.length} lead</span>
          </div>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {hotLeads.map((lead) => (
              <div key={lead.lead_id} className="flex items-center justify-between py-2 px-3 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-100 dark:border-neutral-700">
                <div className="flex items-center gap-3">
                  <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${lead.status === "online" ? "bg-green-500 animate-pulse" : lead.status === "recent" ? "bg-amber-500" : "bg-neutral-300"}`}></span>
                  <div>
                    <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{lead.business_name}</p>
                    <p className="text-[10px] text-neutral-400">{lead.category || "—"} · {lead.total_opens}x buka · {lead.status === "online" ? "Sedang online" : lead.status === "recent" ? "Baru buka" : "Hari ini"}</p>
                  </div>
                </div>
                <a href={`https://wa.me/${lead.phone_number}?text=${encodeURIComponent(`Halo ${lead.business_name}, saya notice Anda baru saja membuka laporan audit digital yang kami kirimkan. Apakah ada pertanyaan atau hal yang ingin didiskusikan lebih lanjut? Saya siap bantu.`)}`} target="_blank" rel="noopener noreferrer"
                  className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-[10px] font-bold rounded-lg transition-colors whitespace-nowrap">
                  Follow Up
                </a>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Re-engagement Alerts */}
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
            {alerts.map((alert) => (
              <div key={alert.id} className="flex items-center justify-between py-2 px-3 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
                <div>
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{alert.business_name}</p>
                  <p className="text-[10px] text-neutral-500">Buka report lagi setelah <span className="font-bold text-amber-600">{alert.days_since_first_view} hari</span> — kemungkinan masih tertarik</p>
                </div>
                <div className="flex items-center gap-2">
                  <a href={`https://wa.me/${alert.phone_number}`} target="_blank" rel="noopener noreferrer"
                    className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-[10px] font-bold rounded-lg transition-colors whitespace-nowrap">
                    WA Sekarang
                  </a>
                  <button onClick={() => { apiFetch(`/api/alerts/reengagement/${alert.id}/read`, { method: "POST" }); setAlerts(prev => prev.filter(a => a.id !== alert.id)); }}
                    className="p-1.5 text-neutral-400 hover:text-neutral-600 transition-colors" title="Dismiss">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card p-6">
          <h2 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-4">Layanan Paling Diminati</h2>
          {loading ? (
            <div className="space-y-3">{[...Array(3)].map((_, i) => <div key={i} className="h-6 bg-neutral-100 dark:bg-neutral-800 rounded animate-pulse" />)}</div>
          ) : analytics?.leads_by_product.length === 0 ? (
            <p className="text-xs text-neutral-400 italic">Belum ada data.</p>
          ) : (
            <div className="space-y-3">
              {analytics?.leads_by_product.map((p) => (
                <div key={p.product}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-medium text-neutral-700 dark:text-neutral-300">{p.product}</span>
                    <span className="text-neutral-400 dark:text-neutral-500">{p.count} leads</span>
                  </div>
                  <div className="h-2 bg-neutral-100 dark:bg-neutral-800 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-amber-500 to-yellow-500 rounded-full transition-all duration-700"
                      style={{ width: `${(p.count / maxProduct) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">Quick Actions</h2>
          {QUICK_ACTIONS.map((action) => (
            <Link key={action.title} href={action.href}
              className={`bg-gradient-to-br ${action.gradient} rounded-2xl p-4 text-white flex items-center gap-4 hover:opacity-90 hover:scale-[1.01] transition-all duration-200 shadow-card hover:shadow-card-hover`}>
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
  );
}
