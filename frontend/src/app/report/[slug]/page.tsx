"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import { useTheme } from "next-themes";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const ADMIN_WA = process.env.NEXT_PUBLIC_ADMIN_WA ?? "6285156843788";

interface ReportData {
  id: string;
  slug: string;
  nama_usaha: string | null;
  phone_number: string | null;
  address: string | null;
  category: string | null;
  services_detail: { name: string; price: number; features: string[] }[];
  total_price: number;
  base_price: number | null;
  discount_price: number | null;
  discount_expires_at: string | null;
  is_discount_expired: boolean;
  active_price: number;
  first_viewed_at: string | null;
  additional_options: string | null;
  status: string;
  created_at: string | null;
  competitor_count: number;
  digital_analysis: {
    analysis: string;
    pain_points: string[];
    suggested_product: string | null;
    analyzed_at: string;
  } | null;
  faqs: { question: string; answer: string }[];
  monthly_search_volume: number;
  selected_addons: { id: string; name: string; price: number }[];
}

function formatRupiah(num: number): string {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
  }).format(num);
}

function extractCity(address: string | null): string {
  if (!address) return "kota Anda";
  const parts = address.split(",");
  return parts[parts.length - 1]?.trim() || "kota Anda";
}

function parsePainPoints(analysis: ReportData["digital_analysis"]): string[] {
  if (!analysis) return [];
  if (analysis.pain_points && analysis.pain_points.length > 0) {
    return analysis.pain_points.slice(0, 3);
  }
  if (analysis.analysis) {
    const lines = analysis.analysis.split("\n").filter((l) => l.trim().length > 10);
    return lines.slice(0, 3);
  }
  return [];
}

interface SectorConfig {
  baseTraffic: number;
  avgTransactionValue: number;
  conversionRate: number;
  isHighVolume: boolean;
}

const CITY_PROVINCE_MAP: Record<string, string> = {
  "jakarta": "DKI Jakarta",
  "bandung": "Jawa Barat",
  "surabaya": "Jawa Timur",
  "medan": "Sumatera Utara",
  "semarang": "Jawa Tengah",
  "makassar": "Sulawesi Selatan",
  "bali": "Bali",
  "balikpapan": "Kalimantan Timur",
  "samarinda": "Kalimantan Timur",
  "malang": "Jawa Timur",
  "jogja": "DI Yogyakarta",
  "yogyakarta": "DI Yogyakarta",
  "bekasi": "Jawa Barat",
  "tangerang": "Banten",
  "depok": "Jawa Barat",
  "bogor": "Jawa Barat",
  "solo": "Jawa Tengah",
  "palembang": "Sumatera Selatan",
  "manado": "Sulawesi Utara",
  "pontianak": "Kalimantan Barat",
  "banjarmasin": "Kalimantan Selatan",
  "denpasar": "Bali",
  "batam": "Kepulauan Riau",
  "pekanbaru": "Riau",
  "padang": "Sumatera Barat",
  "lampung": "Lampung",
  "cirebon": "Jawa Barat",
};

function getProvinceForCity(city: string): string | null {
  const normalized = city.toLowerCase().trim();
  for (const [key, province] of Object.entries(CITY_PROVINCE_MAP)) {
    if (normalized.includes(key) || key.includes(normalized)) {
      return province;
    }
  }
  return null;
}

const B2B_KEYWORDS = [
  "kontraktor", "epoxy", "waterproofing", "fabrikasi", "konstruksi",
  "industrial", "manufaktur", "supplier", "distributor", "b2b",
  "interior", "arsitek", "renovasi", "building", "bangunan",
  "teknik", "engineering", "konsultan", "proyek",
];

const RETAIL_KEYWORDS = [
  "cafe", "resto", "restoran", "salon", "barbershop", "toko",
  "warung", "kedai", "bakery", "laundry", "kopi", "coffee",
  "kuliner", "food", "minuman", "retail", "umkm", "olshop",
  "fashion", "clothing", "butik", "mart", "grocery",
];

function getSectorConfig(category: string): SectorConfig {
  const cat = category.toLowerCase();

  const isB2B = B2B_KEYWORDS.some((kw) => cat.includes(kw));
  if (isB2B) {
    return {
      baseTraffic: 80,
      avgTransactionValue: 25000000,
      conversionRate: 0.01,
      isHighVolume: false,
    };
  }

  const isRetail = RETAIL_KEYWORDS.some((kw) => cat.includes(kw));
  if (isRetail) {
    return {
      baseTraffic: 300,
      avgTransactionValue: 75000,
      conversionRate: 0.01,
      isHighVolume: true,
    };
  }

  // Default: sektor menengah
  return {
    baseTraffic: 150,
    avgTransactionValue: 500000,
    conversionRate: 0.01,
    isHighVolume: false,
  };
}

function AccordionItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="py-3">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between text-left gap-3"
      >
        <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{question}</span>
        <svg
          className={`w-4 h-4 shrink-0 text-amber-500 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${open ? "max-h-40 opacity-100 mt-2" : "max-h-0 opacity-0"}`}
      >
        <p className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">{answer}</p>
      </div>
    </div>
  );
}

export default function PublicReportPage() {
  const params = useParams();
  const slug = params.slug as string;
  const { theme, setTheme } = useTheme();

  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sliderValue, setSliderValue] = useState(30);
  const [timeLeft, setTimeLeft] = useState<string>("");
  const [discountExpired, setDiscountExpired] = useState(false);
  const [checkedAddons, setCheckedAddons] = useState<Set<string>>(new Set());

  const pleasureBridgeRef = useRef<HTMLDivElement>(null);
  const fomoCloserRef = useRef<HTMLDivElement>(null);
  const engageSentRef = useRef(false);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/proposals/public/report/${slug}`);
        if (!res.ok) throw new Error("Report tidak ditemukan");
        const data: ReportData = await res.json();
        setReport(data);
        setDiscountExpired(data.is_discount_expired);
      } catch (e: any) {
        setError(e.message || "Gagal memuat report");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [slug]);

  // Countdown timer — dihitung dari first_viewed_at + 24 jam (dikunci di database)
  useEffect(() => {
    if (!report?.first_viewed_at || discountExpired) return;
    const deadline = new Date(report.first_viewed_at).getTime() + 24 * 60 * 60 * 1000;
    const interval = setInterval(() => {
      const now = new Date().getTime();
      const diff = deadline - now;
      if (diff <= 0) {
        setDiscountExpired(true);
        setTimeLeft("00:00:00");
        clearInterval(interval);
        return;
      }
      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);
      setTimeLeft(
        `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`
      );
    }, 1000);
    return () => clearInterval(interval);
  }, [report?.first_viewed_at, discountExpired]);

  // Intent Detector — IntersectionObserver untuk deteksi ketertarikan klien
  useEffect(() => {
    if (!slug || engageSentRef.current) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && !engageSentRef.current) {
            engageSentRef.current = true;
            fetch(`${API_BASE}/api/proposals/public/report/${slug}/engage`, {
              method: "POST",
            }).catch(() => {});
            // Track ROI Slider viewed
            fetch(`${API_BASE}/api/proposals/public/report/${slug}/track-activity`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ activity_type: "ROI_SLIDER_VIEWED" }),
            }).catch(() => {});
            observer.disconnect();
            break;
          }
        }
      },
      { threshold: 0.3 }
    );
    if (pleasureBridgeRef.current) observer.observe(pleasureBridgeRef.current);
    if (fomoCloserRef.current) observer.observe(fomoCloserRef.current);
    return () => observer.disconnect();
  }, [slug, report]);

  // Activity Sensor — mobile detection & first human interaction
  useEffect(() => {
    if (!slug) return;
    const mobileSentRef = { sent: false };
    const clickSentRef = { sent: false };

    // Detect mobile device
    const isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    if (isMobile && !mobileSentRef.sent) {
      mobileSentRef.sent = true;
      fetch(`${API_BASE}/api/proposals/public/report/${slug}/track-activity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ activity_type: "IS_MOBILE" }),
      }).catch(() => {});
    }

    // First human interaction → LINK_CLICKED
    const handleFirstInteraction = () => {
      if (clickSentRef.sent) return;
      clickSentRef.sent = true;
      fetch(`${API_BASE}/api/proposals/public/report/${slug}/track-activity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ activity_type: "LINK_CLICKED" }),
      }).catch(() => {});
      window.removeEventListener("mousemove", handleFirstInteraction);
      window.removeEventListener("touchstart", handleFirstInteraction);
    };
    window.addEventListener("mousemove", handleFirstInteraction, { once: true });
    window.addEventListener("touchstart", handleFirstInteraction, { once: true });

    return () => {
      window.removeEventListener("mousemove", handleFirstInteraction);
      window.removeEventListener("touchstart", handleFirstInteraction);
    };
  }, [slug]);

  // Dynamic Math Engine — kalkulasi berdasarkan sektor industri
  const sectorConfig = getSectorConfig(report?.category || "");
  const trafficMultiplier = sectorConfig.isHighVolume
    ? Math.pow(sliderValue / 10, 1.8)
    : sliderValue / 10;
  const estimatedTrafficGain = Math.round(sectorConfig.baseTraffic * trafficMultiplier);
  const projectedLeads = Math.round(estimatedTrafficGain * sectorConfig.conversionRate);
  const projectedRevenue = projectedLeads * sectorConfig.avgTransactionValue;

  const city = report ? extractCity(report.address) : "";
  const painPoints = report ? parsePainPoints(report.digital_analysis) : [];

  // Add-on price calculation
  const addonsTotal = report
    ? report.selected_addons
        .filter((a) => checkedAddons.has(a.id))
        .reduce((sum, a) => sum + a.price, 0)
    : 0;
  const checkedAddonNames = report
    ? report.selected_addons.filter((a) => checkedAddons.has(a.id)).map((a) => a.name)
    : [];

  const waText = report
    ? `Halo Vin, saya sudah lihat laporan audit web untuk ${report.nama_usaha}. Saya mau tanya solusi untuk perbaikan masalah tadi dong.${checkedAddonNames.length > 0 ? ` Dan saya tertarik menambahkan opsi: ${checkedAddonNames.join(" dan ")}.` : ""}`
    : "";
  const waLink = `https://wa.me/${ADMIN_WA}?text=${encodeURIComponent(waText)}`;

  const waTextExpired = report
    ? `Halo Vin, saya telat membuka laporan audit untuk ${report.nama_usaha} dan kuotanya sudah habis terkunci. Apakah masih ada slot antrean kosong untuk bulan depan?`
    : "";
  const waLinkExpired = `https://wa.me/${ADMIN_WA}?text=${encodeURIComponent(waTextExpired)}`;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#fcfaf7] dark:bg-zinc-950">
        <div className="animate-pulse text-zinc-400 text-lg">Memuat laporan...</div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#fcfaf7] dark:bg-zinc-950">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-zinc-800 dark:text-zinc-100 mb-2">404</h1>
          <p className="text-zinc-500 dark:text-zinc-400">{error || "Report tidak ditemukan"}</p>
        </div>
      </div>
    );
  }

  const sliderPercent = ((sliderValue - 10) / 90) * 100;

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 bg-[radial-gradient(#e4e4e7_1px,transparent_1px)] dark:bg-[radial-gradient(#27272a_1px,transparent_1px)] [background-size:20px_20px] text-zinc-900 dark:text-zinc-100 print:bg-white print:text-black print:bg-none">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white dark:bg-zinc-900 border-b-2 border-zinc-200 dark:border-zinc-700 print:hidden">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-zinc-600 dark:text-zinc-400 uppercase tracking-widest font-bold">Laporan Audit Digital</p>
            <h1 className="text-base font-bold text-zinc-900 dark:text-white truncate">{report.nama_usaha}</h1>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-100 border-2 border-amber-400">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
              <span className="text-[10px] font-bold text-amber-700">Live</span>
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        {/* ============================================================ */}
        {/* KOMPONEN 1: THE PAIN BOX */}
        {/* ============================================================ */}
        <section className="bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-200 dark:border-amber-800 rounded-2xl p-6 shadow-sm hover:border-amber-500 transition-all duration-300 ease-in-out">
          <h2 className="text-sm font-bold uppercase tracking-widest text-amber-700 dark:text-amber-400 mb-4">
            Masalah Kritis yang Ditemukan
          </h2>
          <div className="space-y-4">
            {(painPoints.length > 0 ? painPoints : [
              "Kecepatan Web Lambat: Bikin sekitar 40% calon pelanggan Anda kabur sebelum halaman terbuka.",
              `Unoptimized Local SEO: Bisnis Anda tenggelam di Google Maps, kalah saing dari kompetitor di ${city}.`,
              "Tidak Ada Sistem Konversi: Pengunjung datang tapi tidak ada mekanisme untuk mengubah mereka jadi pelanggan.",
            ]).map((point, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">
                  {i + 1}
                </div>
                <p className="text-sm text-zinc-900 leading-relaxed font-medium">{point}</p>
              </div>
            ))}
          </div>

          {/* Executive Search Volume Widget */}
          {report.monthly_search_volume > 0 && (
            <div className="mt-6 pt-5 border-t-2 border-amber-200">
              <p className="text-[10px] uppercase tracking-widest text-zinc-700 font-bold mb-3">Fakta Pasar Digital — {city}</p>
              <div className="flex items-end gap-3 mb-3">
                <span className="text-4xl md:text-5xl font-black text-amber-600 tracking-tight">
                  {report.monthly_search_volume.toLocaleString("id-ID")}
                </span>
                <span className="text-sm text-zinc-700 font-medium pb-1">pencarian/bulan</span>
              </div>
              <div className="w-full h-2 bg-amber-200 rounded-full overflow-hidden">
                <div className="bg-amber-500 h-full rounded-full" style={{ width: "75%" }}></div>
              </div>
              <p className="text-sm text-zinc-900 mt-3 leading-relaxed">
                Ada sekitar <span className="font-bold text-amber-600">{report.monthly_search_volume.toLocaleString("id-ID")}</span> orang di <span className="font-bold text-zinc-900">{city}</span> yang aktif mencari solusi <span className="font-bold text-zinc-900">{report.category}</span> setiap bulannya di Google. Tanpa optimasi yang tepat, potensi pasar ini sepenuhnya mengalir ke kompetitor Anda.
              </p>
            </div>
          )}
        </section>

        {/* ============================================================ */}
        {/* KOMPONEN: AUDIT SCORE */}
        {/* ============================================================ */}
        <section className="bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-700 rounded-2xl p-6 shadow-sm">
          <p className="text-[10px] uppercase tracking-widest text-zinc-600 dark:text-zinc-400 font-bold mb-4">Skor Kesehatan Digital</p>
          <div className="flex items-center gap-6">
            {/* Speedometer */}
            <div className="relative w-28 h-28 shrink-0">
              <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
                <circle cx="60" cy="60" r="50" fill="none" stroke="#e4e4e7" strokeWidth="12" className="dark:stroke-zinc-700" />
                <circle cx="60" cy="60" r="50" fill="none" stroke={(() => {
                  const score = Math.max(10, Math.min(100, Math.round(
                    (report.competitor_count > 3 ? 10 : 25) +
                    (report.monthly_search_volume > 500 ? 5 : 15) +
                    (painPoints.length >= 3 ? 5 : 20) +
                    (report.digital_analysis ? 10 : 0)
                  )));
                  if (score <= 30) return "#ef4444";
                  if (score <= 60) return "#f59e0b";
                  return "#22c55e";
                })()} strokeWidth="12" strokeLinecap="round"
                  strokeDasharray={`${Math.round(
                    ((Math.max(10, Math.min(100, Math.round(
                      (report.competitor_count > 3 ? 10 : 25) +
                      (report.monthly_search_volume > 500 ? 5 : 15) +
                      (painPoints.length >= 3 ? 5 : 20) +
                      (report.digital_analysis ? 10 : 0)
                    )))) / 100) * 314
                  )} 314`}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-black text-zinc-900 dark:text-white">{Math.max(10, Math.min(100, Math.round(
                  (report.competitor_count > 3 ? 10 : 25) +
                  (report.monthly_search_volume > 500 ? 5 : 15) +
                  (painPoints.length >= 3 ? 5 : 20) +
                  (report.digital_analysis ? 10 : 0)
                )))}</span>
                <span className="text-[9px] text-zinc-500 font-bold">/100</span>
              </div>
            </div>
            <div className="flex-1 space-y-2">
              <p className="text-base font-bold text-zinc-900 dark:text-white">
                {(() => {
                  const score = Math.max(10, Math.min(100, Math.round(
                    (report.competitor_count > 3 ? 10 : 25) +
                    (report.monthly_search_volume > 500 ? 5 : 15) +
                    (painPoints.length >= 3 ? 5 : 20) +
                    (report.digital_analysis ? 10 : 0)
                  )));
                  if (score <= 30) return "Kondisi Kritis — Perlu Tindakan Segera";
                  if (score <= 60) return "Perlu Perbaikan Signifikan";
                  return "Cukup Baik, Bisa Ditingkatkan";
                })()}
              </p>
              <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                Skor ini dihitung berdasarkan visibilitas Google, tingkat kompetisi di {city}, dan kesiapan digital {report.nama_usaha} saat ini.
              </p>
              <div className="flex flex-wrap gap-2 mt-2">
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-semibold dark:bg-red-900/30 dark:text-red-400">SEO: Lemah</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-semibold dark:bg-red-900/30 dark:text-red-400">Maps: Tidak Terlihat</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold dark:bg-amber-900/30 dark:text-amber-400">Konversi: Rendah</span>
              </div>
            </div>
          </div>
        </section>

        {/* ============================================================ */}
        {/* KOMPONEN: BEFORE vs AFTER */}
        {/* ============================================================ */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Before */}
          <div className="bg-zinc-100 dark:bg-zinc-800 border-2 border-zinc-200 dark:border-zinc-700 rounded-2xl p-5 space-y-4 transition-all duration-300 ease-in-out">
            <div className="flex items-center justify-between">
              <p className="text-[10px] uppercase tracking-widest text-zinc-600 dark:text-zinc-400 font-bold">Kondisi Saat Ini</p>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-200 border-2 border-zinc-300 text-[10px] font-bold text-zinc-600">🔴 Masalah Kritis</span>
            </div>
            <h3 className="text-sm font-bold text-zinc-800">{report.nama_usaha}</h3>
            <div className="space-y-3">
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-zinc-200 border-2 border-zinc-300 flex items-center justify-center shrink-0 mt-0.5"><span className="text-zinc-600 text-[9px] font-bold">!</span></div>
                <div>
                  <p className="text-sm text-zinc-600">Skor Kecepatan Web: <span className="text-zinc-500 line-through font-medium">32/100</span></p>
                  <p className="text-[11px] text-zinc-500">Pengunjung menunggu &gt;5 detik</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-zinc-200 border-2 border-zinc-300 flex items-center justify-center shrink-0 mt-0.5"><span className="text-zinc-600 text-[9px] font-bold">!</span></div>
                <div>
                  <p className="text-sm text-zinc-600">Google Maps: <span className="text-zinc-500 line-through font-medium">Tidak Terlihat</span></p>
                  <p className="text-[11px] text-zinc-500">Tidak muncul di halaman utama {city}</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-zinc-200 border-2 border-zinc-300 flex items-center justify-center shrink-0 mt-0.5"><span className="text-zinc-600 text-[9px] font-bold">!</span></div>
                <div>
                  <p className="text-sm text-zinc-600">SEO Lokal: <span className="text-zinc-500 line-through font-medium">Tidak Teroptimasi</span></p>
                  <p className="text-[11px] text-zinc-500">Kalah saing dari kompetitor</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-zinc-200 border-2 border-zinc-300 flex items-center justify-center shrink-0 mt-0.5"><span className="text-zinc-600 text-[9px] font-bold">!</span></div>
                <div>
                  <p className="text-sm text-zinc-600">Konversi: <span className="text-zinc-500 line-through font-medium">&lt;1%</span></p>
                  <p className="text-[11px] text-zinc-500">Tidak ada sistem penangkap leads</p>
                </div>
              </div>
            </div>
          </div>

          {/* After */}
          <div className="bg-white dark:bg-zinc-900 border-2 border-amber-200 dark:border-amber-800 rounded-2xl p-5 space-y-4 transition-all duration-300 ease-in-out hover:border-amber-500 shadow-sm">
            <div className="flex items-center justify-between">
              <p className="text-[10px] uppercase tracking-widest text-zinc-600 font-bold">Proyeksi Perbaikan</p>
              <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-700 border-2 border-amber-300 text-xs px-2.5 py-1 rounded-full font-bold">Peringkat #1</span>
            </div>
            <h3 className="text-sm font-bold text-zinc-900 dark:text-white">Bersama Kantor Teman</h3>

            {/* Mockup Google Search */}
            <div className="rounded-xl border-2 border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 p-3.5 space-y-1.5">
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-4 rounded-full bg-amber-500 flex items-center justify-center">
                  <span className="text-white text-[7px] font-bold">✓</span>
                </div>
                <span className="text-[10px] text-zinc-600">kantorteman.com › {report.slug}</span>
              </div>
              <p className="text-sm font-bold text-blue-700">{report.nama_usaha} — Solusi Terpercaya di {city}</p>
              <div className="flex items-center gap-1">
                <span className="text-amber-500 text-xs">★★★★★</span>
                <span className="text-[10px] text-zinc-600">5.0 · Terverifikasi</span>
              </div>
              <p className="text-[11px] text-zinc-600">Layanan profesional {report.category || "bisnis"} terbaik di {city}.</p>
            </div>

            <div className="space-y-2.5">
              <div className="flex items-center gap-2">
                <span className="text-amber-600 text-sm font-bold">✓</span>
                <p className="text-sm text-zinc-900">Kecepatan Web: <span className="text-amber-600 font-bold">98/100</span></p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-amber-600 text-sm font-bold">✓</span>
                <p className="text-sm text-zinc-900">Google Maps: <span className="text-amber-600 font-bold">Peringkat 1 di {city}</span></p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-amber-600 text-sm font-bold">✓</span>
                <p className="text-sm text-zinc-900">SEO Lokal: <span className="text-amber-600 font-bold">Fully Optimized</span></p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-amber-600 text-sm font-bold">✓</span>
                <p className="text-sm text-zinc-900">Konversi: <span className="text-amber-600 font-bold">8-12%</span></p>
              </div>
            </div>
          </div>
        </section>

        {/* ============================================================ */}
        {/* KOMPONEN 2: THE PLEASURE BRIDGE */}
        {/* ============================================================ */}
        {!discountExpired ? (
          <section ref={pleasureBridgeRef} className="bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-700 rounded-2xl p-6 shadow-sm transition-all duration-300 ease-in-out hover:border-amber-500 print:hidden">
            <p className="text-sm text-zinc-900 dark:text-zinc-100 font-medium mb-5">
              Geser slider di bawah untuk memvisualisasikan potensi pertumbuhan bisnis Anda jika masalah digital di atas diperbaiki.
            </p>

            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-zinc-700 dark:text-zinc-300 uppercase tracking-widest font-bold">Kenaikan Trafik</span>
                <span className="text-2xl font-black text-amber-600">{sliderValue}%</span>
              </div>

              {/* Proyeksi Keuntungan Bulanan */}
              <div className="bg-zinc-50 dark:bg-zinc-800/50 rounded-xl p-4 border border-zinc-200 dark:border-zinc-700">
                <p className="text-[10px] text-zinc-500 dark:text-zinc-400 uppercase tracking-widest font-bold mb-3">Proyeksi Keuntungan 6 Bulan ke Depan</p>
                <div className="flex items-end gap-2" style={{ height: "90px" }}>
                  {[1, 2, 3, 4, 5, 6].map((month) => {
                    const growth = 1 + (sliderValue / 100) * 0.3 * month;
                    const barHeight = Math.max(12, Math.round((growth / (1 + (sliderValue / 100) * 1.8)) * 90));
                    const monthRevenue = Math.round(projectedRevenue * growth * 0.3);
                    return (
                      <div key={month} className="flex-1 flex flex-col items-center">
                        {month === 6 && (
                          <span className="text-[8px] text-amber-600 font-bold mb-1 whitespace-nowrap">{formatRupiah(monthRevenue)}</span>
                        )}
                        <div
                          className="w-full rounded-t transition-all duration-300 ease-out"
                          style={{
                            height: `${barHeight}px`,
                            backgroundColor: `rgba(245, 158, 11, ${0.3 + (month * 0.12)})`,
                          }}
                        ></div>
                        <span className="text-[8px] text-zinc-400 mt-1">Bln {month}</span>
                      </div>
                    );
                  })}
                </div>
                <p className="text-[10px] text-zinc-400 dark:text-zinc-500 mt-3 text-center italic">Setiap bulan yang ditunda = potensi revenue yang hilang permanen</p>
              </div>

              {/* Custom Slider Track */}
              <div className="relative w-full h-3 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                <div className="absolute inset-y-0 left-0 bg-amber-500 rounded-full transition-all duration-150" style={{ width: `${sliderPercent}%` }}></div>
              </div>
              <input
                type="range"
                min={10}
                max={100}
                step={5}
                value={sliderValue}
                onInput={(e) => setSliderValue(Number((e.target as HTMLInputElement).value))}
                onChange={(e) => setSliderValue(Number(e.target.value))}
                className="w-full h-3 -mt-3 relative z-10 appearance-none bg-transparent cursor-pointer touch-none accent-amber-500 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-7 [&::-webkit-slider-thumb]:w-7 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-amber-500 [&::-webkit-slider-thumb]:border-4 [&::-webkit-slider-thumb]:border-white [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:ring-2 [&::-webkit-slider-thumb]:ring-amber-600 [&::-moz-range-thumb]:h-7 [&::-moz-range-thumb]:w-7 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-amber-500 [&::-moz-range-thumb]:border-4 [&::-moz-range-thumb]:border-white [&::-moz-range-thumb]:shadow-lg [&::-moz-range-thumb]:ring-2 [&::-moz-range-thumb]:ring-amber-600 [&::-webkit-slider-runnable-track]:bg-transparent [&::-moz-range-track]:bg-transparent"
              />
              <p className="text-center text-xs text-zinc-500 dark:text-zinc-400 font-medium mt-1">← Geser untuk melihat proyeksi →</p>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-200 dark:border-amber-800 rounded-xl p-3 text-center">
                  <p className="text-[10px] text-zinc-700 dark:text-zinc-300 uppercase tracking-widest font-bold mb-1">Proyeksi Leads Baru</p>
                  <p className="text-2xl font-black text-amber-600 transition-all duration-300">+{projectedLeads}</p>
                  <p className="text-[11px] text-zinc-600 dark:text-zinc-400 font-medium mt-0.5">leads/bulan</p>
                </div>
                <div className="bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-200 dark:border-amber-800 rounded-xl p-3 text-center overflow-hidden">
                  <p className="text-[10px] text-zinc-700 dark:text-zinc-300 uppercase tracking-widest font-bold mb-1">Tambahan Omzet</p>
                  <p className="text-lg md:text-2xl font-extrabold text-amber-600 tracking-tight transition-all duration-300 truncate">{formatRupiah(projectedRevenue)}</p>
                  <p className="text-[11px] text-zinc-600 dark:text-zinc-400 font-medium mt-0.5">per bulan</p>
                </div>
              </div>

              {/* Kompetitor Counter */}
              {report.competitor_count > 0 && (
                <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-xl p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center shrink-0">
                      <span className="text-red-600 font-black text-sm">{report.competitor_count}</span>
                    </div>
                    <div>
                      <p className="text-sm font-bold text-zinc-800 dark:text-zinc-200">Kompetitor di {city} sudah aktif digital</p>
                      <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">Setiap hari mereka mengambil pelanggan yang seharusnya milik Anda.</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Pencarian Hari Ini */}
              {report.monthly_search_volume > 0 && (
                <div className="bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700 rounded-xl p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center shrink-0">
                      <span className="text-amber-600 font-black text-sm">~{Math.round(report.monthly_search_volume / 30)}</span>
                    </div>
                    <div>
                      <p className="text-sm font-bold text-zinc-800 dark:text-zinc-200">Orang hari ini mencari &ldquo;{report.category || "jasa"} {city}&rdquo;</p>
                      <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">Berapa dari mereka yang menemukan bisnis Anda?</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Slot Terbatas */}
              <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-300 dark:border-amber-700 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-amber-200 dark:bg-amber-800 flex items-center justify-center shrink-0 mt-0.5">
                    <span className="text-amber-700 dark:text-amber-300 text-xs font-black">!</span>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-zinc-800 dark:text-zinc-200">Slot terbatas: Maks. 5 klien per kota</p>
                    <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">Kami membatasi jumlah klien per wilayah untuk menghindari konflik interest antar bisnis sejenis.</p>
                  </div>
                </div>
              </div>

              {/* Opportunity Cost */}
              <div className="bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-xl p-4 text-center">
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mb-1">Jika Anda mulai 3 bulan lalu, estimasi Anda sudah mendapat:</p>
                <p className="text-base font-bold text-zinc-800 dark:text-zinc-200">+{projectedLeads * 3} leads & <span className="text-amber-600">{formatRupiah(projectedRevenue * 3)}</span> tambahan omzet</p>
                <p className="text-[10px] text-zinc-400 dark:text-zinc-500 mt-1 italic">Waktu yang berlalu tidak bisa dikembalikan.</p>
              </div>
            </div>
          </section>
        ) : (
          <section className="bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-700 rounded-2xl p-6 text-center print:hidden">
            <div className="space-y-3">
              <svg className="w-12 h-12 mx-auto text-zinc-600 dark:text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <p className="text-zinc-900 dark:text-zinc-100 font-bold text-base leading-relaxed">
                Maaf, Kuota Promo Slot Optimasi SEO & Web untuk Wilayah{" "}
                <span className="text-amber-600">{city}</span> Bulan Ini Telah Habis Terkunci.
              </p>
              <p className="text-zinc-600 dark:text-zinc-400 text-sm font-medium">
                Anda masih bisa mendaftar antrean untuk bulan depan.
              </p>
            </div>
          </section>
        )}

        {/* ============================================================ */}
        {/* KOMPONEN: OBJECTION DESTROYER ACCORDION (FAQ) */}
        {/* ============================================================ */}
        {report.faqs && report.faqs.length > 0 && (
          <section className="bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-700 rounded-2xl p-6 shadow-sm transition-all duration-300 ease-in-out hover:border-amber-500">
            <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-700 dark:text-zinc-300 mb-4">Pertanyaan yang Sering Ditanyakan</h3>
            <div className="divide-y divide-zinc-200 dark:divide-zinc-700">
              {report.faqs.map((faq, i) => (
                <AccordionItem key={i} question={faq.question} answer={faq.answer} />
              ))}
            </div>
          </section>
        )}

        {/* ============================================================ */}
        {/* KOMPONEN 3: THE FOMO CLOSER */}
        {/* ============================================================ */}
        <section ref={fomoCloserRef} className="bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-700 rounded-2xl p-6 shadow-sm space-y-5 print:hidden">
          {/* Scarcity text */}
          <p className="text-sm text-zinc-900 dark:text-zinc-100 text-center leading-relaxed font-medium">
            Untuk menjaga kualitas pengerjaan dan hasil yang maksimal, kami membatasi kemitraan hanya untuk{" "}
            <span className="text-amber-600 font-black">1 bisnis</span> di sektor{" "}
            <span className="font-black text-zinc-900">{report.category || "bisnis ini"}</span> untuk wilayah{" "}
            <span className="font-black text-zinc-900">{city}</span> pada bulan ini. Saat ini, laporan khusus ini juga sedang diakses oleh beberapa bisnis sejenis di kota Anda.
          </p>

          {/* Competitor alert */}
          {report.competitor_count > 0 && (
            <div className="rounded-xl bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-200 dark:border-amber-800 px-4 py-2.5 text-center">
              <p className="text-sm text-zinc-900 dark:text-zinc-100 font-medium">
                Saat ini ada <span className="font-black text-amber-600">{report.competitor_count} bisnis sejenis</span> di {city} yang juga sedang membuka laporan ini.
              </p>
            </div>
          )}

          {/* Digital Countdown Box */}
          {!discountExpired && (
            <div className="space-y-3 text-center">
              <div className="flex items-center justify-center gap-3">
                <span className="text-sm text-zinc-500 line-through font-medium">{formatRupiah(report.base_price || report.total_price)}</span>
                <span className="text-2xl font-black text-amber-600">{formatRupiah(report.discount_price || report.total_price)}</span>
              </div>
              <div className="bg-zinc-900 border-2 border-zinc-800 text-amber-500 font-mono text-2xl py-2 px-5 rounded-xl inline-block text-center shadow-md font-bold tracking-widest">
                {timeLeft}
              </div>
              <p className="text-[11px] text-zinc-700 dark:text-zinc-400 font-medium">Sisa waktu harga spesial</p>
            </div>
          )}

          {/* Geographic Proximity Trust Badge */}
          <div className="rounded-xl bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-200 dark:border-amber-800 px-4 py-3">
            <p className="text-sm text-zinc-900 dark:text-zinc-100 leading-relaxed">
              📍 <span className="font-bold text-zinc-900">Prioritas Layanan Wilayah {city || "Kota Anda"} & Sekitarnya:</span>{" "}
              Tim kami memastikan seluruh langkah optimasi disesuaikan dengan algoritma kompetisi pasar area{" "}
              <span className="font-bold text-zinc-900">{getProvinceForCity(city) || "Wilayah Kota Anda & Sekitarnya"}</span>.
            </p>
          </div>

          {/* CTA WhatsApp Button */}
          {!discountExpired ? (
            <a
              href={waLink}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full text-center py-4 px-6 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-black text-lg shadow-md border-b-4 border-amber-700 animate-pulse transition-all duration-200 hover:scale-[1.02]"
            >
              <span className="inline-flex items-center gap-2.5">
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                </svg>
                Konsultasi Gratis via WhatsApp
              </span>
            </a>
          ) : (
            <a
              href={waLinkExpired}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full text-center py-4 px-6 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-white font-black text-lg border-b-4 border-zinc-900 shadow-md transition-all duration-200 hover:scale-[1.02]"
            >
              <span className="inline-flex items-center gap-2.5">
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                </svg>
                Daftar Antrean Waiting List Bulan Depan
              </span>
            </a>
          )}

          {/* Partner Share Button */}
          <button
            onClick={() => {
              const shareText = `Eh Bro, coba liat audit website kita dari agensi Teman UMKM. Ternyata web kita lemot dan kalah saing di ${city}. Coba lu cek deh kalkulator proyeksi omzetnya di sini: kantorteman.com/report/${report.slug}`;
              if (navigator.share) {
                navigator.share({ title: `Audit Digital - ${report.nama_usaha}`, text: shareText }).catch(() => {});
              } else {
                window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(shareText)}`, "_blank");
              }
              fetch(`${API_BASE}/api/proposals/public/report/${report.slug}/track-activity`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ activity_type: "SHARE_PARTNER_CLICKED" }),
              }).catch(() => {});
            }}
            className="block w-full text-center py-3 px-4 rounded-xl border-2 border-zinc-200 bg-zinc-50 hover:bg-zinc-100 text-zinc-700 hover:text-zinc-900 font-bold text-sm transition-all duration-300"
          >
            🔗 Share Laporan Ini ke Partner Bisnis Anda
          </button>
        </section>

        {/* Footer */}
        <footer className="text-center text-xs text-zinc-600 py-6 print:hidden">
          <p>Laporan ini dibuat otomatis oleh sistem audit digital Kantor Teman.</p>
          <p className="mt-1">&copy; {new Date().getFullYear()} Kantor Teman</p>
        </footer>

        {/* Print-only formal block */}
        <section className="hidden print:block border-t border-gray-300 pt-6 mt-8 text-center">
          <p className="text-sm text-gray-700 leading-relaxed max-w-2xl mx-auto">
            Laporan audit digital ini diterbitkan secara eksklusif oleh Teman UMKM Kita. Dokumen ini sah dan bersifat konfidensial untuk jajaran manajemen internal. Silakan hubungi nomor WhatsApp resmi agensi kami untuk konsultasi implementasi fisik dan eksekusi perbaikan taktis.
          </p>
          <p className="text-xs text-gray-500 mt-4">&copy; {new Date().getFullYear()} Kantor Teman &mdash; Dokumen Resmi</p>
        </section>
      </main>

      {/* Floating WA CTA */}
      {!discountExpired && (
        <div className="fixed bottom-0 left-0 right-0 z-50 print:hidden">
          <div className="max-w-3xl mx-auto px-4 pb-4">
            <a href={`https://wa.me/${ADMIN_WA}?text=${encodeURIComponent(`Halo Vin, saya sudah baca laporan audit digital untuk ${report.nama_usaha}. Saya tertarik untuk diskusi lebih lanjut tentang solusinya.`)}`}
              target="_blank" rel="noopener noreferrer"
              className="flex items-center justify-between w-full px-5 py-3.5 bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-2xl shadow-lg shadow-amber-500/30 transition-all hover:scale-[1.02]">
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
                <span className="text-sm">Konsultasi Gratis Sekarang</span>
              </div>
              {timeLeft && timeLeft !== "00:00:00" && (
                <span className="text-xs bg-white/20 px-2.5 py-1 rounded-lg font-mono">{timeLeft}</span>
              )}
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
