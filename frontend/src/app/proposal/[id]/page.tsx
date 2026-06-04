"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import { formatRupiah } from "../../../utils/formatter";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface TimelinePhase {
  sequence: number;
  title: string;
  description: string;
}

interface RoiData {
  enabled: boolean;
  monthly_ads_cost: number;
  roi_months: number;
  roi_multiplier: number;
  has_retainer?: boolean;
  retainer_period?: number;
  retainer_monthly?: number;
  onetime_total?: number;
  our_total_cost?: number;
  ads_total_cost?: number;
  comparison_period?: number;
  comparison_points?: { aspect: string; ads: string; ours: string }[];
}

interface Proposal {
  id: string;
  lead_id: number;
  services_detail: { name: string; price: number; features: string[] }[];
  total_price: number;
  base_price: number | null;
  discount_price: number | null;
  additional_options: string | null;
  status: string;
  created_at: string | null;
  business_name: string | null;
  phone_number: string | null;
  slug: string | null;
  timeline_data?: TimelinePhase[];
  roi_data?: RoiData | null;
  admin_wa?: string;
  admin_name?: string;
  accepted_at?: string | null;
  rejected_at?: string | null;
  discount_expires_at?: string | null;
}


function formatDate(iso: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
}

const SERVICE_BENEFITS: Record<string, string[]> = {
  "seo": [
    "Memastikan bisnis Anda ditemukan di halaman #1 saat calon pelanggan lokal siap membeli",
    "Menghemat biaya iklan berbayar jangka panjang dengan trafik organik stabil",
    "Meningkatkan kepercayaan calon pelanggan karena posisi teratas Google",
  ],
  "google maps": [
    "Bisnis Anda muncul pertama saat orang sekitar mencari jasa Anda di Maps",
    "Ulasan positif terkelola meningkatkan konversi hingga 3x lipat",
    "Calon pelanggan bisa langsung klik telepon/navigasi ke lokasi Anda",
  ],
  "website": [
    "Mengubah 70% pengunjung HP menjadi calon pembeli yang siap menghubungi",
    "Sistem navigasi instan tanpa lemot — loading di bawah 2 detik",
    "Tampilan profesional yang membangun kepercayaan sejak detik pertama",
  ],
  "landing page": [
    "Halaman khusus yang dirancang satu tujuan: mengkonversi pengunjung jadi leads",
    "Terintegrasi langsung dengan WhatsApp untuk respon instan",
    "Optimasi untuk iklan berbayar — setiap rupiah iklan lebih efektif",
  ],
  "instagram": [
    "Konten konsisten yang membangun brand awareness di benak calon pelanggan",
    "Strategi hashtag & engagement yang menarik followers berkualitas",
    "Mengubah followers pasif menjadi pelanggan aktif yang membeli",
  ],
  "tiktok": [
    "Jangkauan viral organik tanpa biaya iklan besar",
    "Konten video pendek yang membangun trust dan awareness masif",
    "Menjangkau generasi pembeli baru yang aktif di platform ini",
  ],
  "chatbot": [
    "Respon otomatis 24/7 — tidak ada lagi pelanggan yang terabaikan",
    "Kualifikasi leads otomatis sebelum masuk ke tim sales Anda",
    "Mengurangi beban kerja admin hingga 60% per hari",
  ],
  "sosial media": [
    "Presence digital konsisten yang membangun kepercayaan brand",
    "Konten strategis yang mendorong engagement dan konversi",
    "Analisis performa rutin untuk optimasi berkelanjutan",
  ],
  "default": [
    "Solusi yang dirancang khusus untuk meningkatkan performa bisnis Anda",
    "Pendekatan data-driven untuk hasil yang terukur dan transparan",
    "Tim profesional berdedikasi yang fokus pada pertumbuhan bisnis Anda",
  ],
};

function getBenefits(serviceName: string): string[] {
  const name = serviceName.toLowerCase();
  for (const [key, benefits] of Object.entries(SERVICE_BENEFITS)) {
    if (key !== "default" && name.includes(key)) return benefits;
  }
  return SERVICE_BENEFITS["default"];
}

function getServiceDescription(serviceName: string): string {
  const name = serviceName.toLowerCase();
  if (name.includes("seo") && name.includes("lokal")) return "Optimasi menyeluruh agar bisnis Anda mendominasi pencarian Google di wilayah operasional — menarik pelanggan yang sudah siap membeli.";
  if (name.includes("seo")) return "Strategi lengkap untuk menempatkan bisnis Anda di posisi teratas Google — di mana calon pelanggan paling banyak mencari.";
  if (name.includes("google maps") || name.includes("gmaps")) return "Setup & optimasi profil Google Maps agar bisnis Anda muncul pertama saat orang sekitar mencari jasa Anda.";
  if (name.includes("riset kata kunci")) return "Identifikasi kata kunci bernilai tinggi yang diketik oleh calon pelanggan yang sudah siap bertransaksi.";
  if (name.includes("company profile") || name.includes("website")) return "Pembuatan website modern yang dirancang khusus untuk mengkonversi pengunjung menjadi pelanggan yang menghubungi Anda.";
  if (name.includes("landing page")) return "Halaman konversi tinggi yang fokus pada satu tujuan: mengubah pengunjung iklan menjadi leads berkualitas.";
  if (name.includes("chatbot") || name.includes("chat bot")) return "Sistem respon otomatis WhatsApp yang melayani calon pelanggan 24/7 tanpa Anda harus standby.";
  if (name.includes("instagram")) return "Pengelolaan akun Instagram profesional dengan konten strategis yang membangun brand dan mendatangkan pelanggan.";
  if (name.includes("tiktok")) return "Produksi konten TikTok yang dirancang untuk viral organik dan menjangkau calon pelanggan baru secara masif.";
  if (name.includes("desain") || name.includes("branding")) return "Identitas visual konsisten yang membuat brand Anda terlihat profesional dan mudah diingat di semua platform.";
  return "Layanan profesional yang dirancang untuk memberikan dampak langsung pada pertumbuhan bisnis Anda.";
}

export default function ProposalPage() {
  const params = useParams();
  const id = params.id as string;
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acceptModal, setAcceptModal] = useState(false);
  const [rejectModal, setRejectModal] = useState(false);
  const [clientName, setClientName] = useState("");
  const [clientPhone, setClientPhone] = useState("");
  const [acceptNotes, setAcceptNotes] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState<number | null>(null);
  const [clientCount, setClientCount] = useState<number>(0);
  const analyticsIdRef = useRef<string | null>(null);
  const lastPingRef = useRef<number>(Date.now());

  useEffect(() => {
    if (!proposal?.discount_expires_at) { setTimeLeft(null); return; }
    const expiresMs = new Date(proposal.discount_expires_at).getTime();
    if (isNaN(expiresMs)) { setTimeLeft(null); return; }
    const tick = () => {
      const remaining = expiresMs - Date.now();
      if (remaining <= 0) {
        setTimeLeft(0);
        clearInterval(interval);
        return;
      }
      setTimeLeft(remaining);
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [proposal?.discount_expires_at]);

  useEffect(() => {
    if (!proposal?.slug) return;
    fetch(`${API_BASE}/api/proposals/${proposal.slug}/social-proof`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.client_count) setClientCount(d.client_count); })
      .catch(() => {});
  }, [proposal?.slug]);

  async function refreshProposal() {
    const res = await fetch(`${API_BASE}/api/proposals/public/${id}`);
    if (res.ok) setProposal(await res.json());
  }

  async function handleAccept() {
    if (!clientName.trim() || !clientPhone.trim() || !proposal?.slug) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/proposals/public/${proposal.slug}/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_name: clientName, client_phone: clientPhone, accept_notes: acceptNotes || null }),
      });
      if (!res.ok) throw new Error("Gagal");
      await refreshProposal();
      setAcceptModal(false);
    } catch {
      setToastMsg("Gagal mengirim. Silakan coba lagi.");
      setTimeout(() => setToastMsg(null), 4000);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReject() {
    if (!proposal?.slug) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/proposals/public/${proposal.slug}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: rejectReason || null }),
      });
      if (!res.ok) throw new Error("Gagal");
      await refreshProposal();
      setRejectModal(false);
    } catch {
      setToastMsg("Gagal mengirim. Silakan coba lagi.");
      setTimeout(() => setToastMsg(null), 4000);
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/proposals/public/${id}`);
        if (!res.ok) throw new Error("Proposal tidak ditemukan");
        setProposal(await res.json());
      } catch (e: any) {
        setError(e.message || "Gagal memuat proposal");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  // Track view: open + periodic ping for total_time_seconds
  useEffect(() => {
    if (!proposal || analyticsIdRef.current) return;
    let pingInterval: NodeJS.Timeout | null = null;

    fetch(`${API_BASE}/api/proposals/track/open`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ proposal_id: proposal.id }),
    })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data?.analytics_id) {
          analyticsIdRef.current = data.analytics_id;
          lastPingRef.current = Date.now();
          pingInterval = setInterval(() => {
            if (document.hidden || !analyticsIdRef.current) return;
            const now = Date.now();
            const elapsed = Math.round((now - lastPingRef.current) / 1000);
            lastPingRef.current = now;
            if (elapsed <= 0 || elapsed > 60) return;
            fetch(`${API_BASE}/api/proposals/track/ping`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ analytics_id: analyticsIdRef.current, seconds: elapsed, sections_viewed: [] }),
            }).catch(() => {});
          }, 10000);
        }
      })
      .catch(() => {});

    return () => {
      if (pingInterval) clearInterval(pingInterval);
    };
  }, [proposal]);

  // Track view duration: send total time on page hide/unload via sendBeacon
  useEffect(() => {
    if (!proposal?.slug) return;
    const mountTime = Date.now();
    const slug = proposal.slug;
    let sent = false;

    function sendDuration() {
      if (sent) return;
      sent = true;
      const seconds = Math.round((Date.now() - mountTime) / 1000);
      if (seconds <= 0) return;
      const url = `${API_BASE}/api/proposals/${slug}/view-duration`;
      const body = JSON.stringify({ duration_seconds: seconds });
      try {
        if (navigator.sendBeacon) {
          const blob = new Blob([body], { type: "application/json" });
          navigator.sendBeacon(url, blob);
        } else {
          fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true }).catch(() => {});
        }
      } catch {}
    }

    function onVisibility() {
      if (document.visibilityState === "hidden") sendDuration();
    }

    window.addEventListener("beforeunload", sendDuration);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("beforeunload", sendDuration);
      document.removeEventListener("visibilitychange", onVisibility);
      sendDuration();
    };
  }, [proposal?.slug]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="animate-pulse text-zinc-500 text-lg font-medium">Memuat proposal...</div>
      </div>
    );
  }

  if (error || !proposal) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-zinc-900 mb-2">404</h1>
          <p className="text-zinc-600">{error || "Proposal tidak ditemukan"}</p>
        </div>
      </div>
    );
  }

  const subtotal = proposal.base_price || proposal.total_price;
  const discount = subtotal - (proposal.discount_price || proposal.total_price);
  const finalTotal = proposal.discount_price || proposal.total_price;
  const timeline = proposal.timeline_data || [];

  const adminWa = proposal.admin_wa || "";
  const adminName = proposal.admin_name || "Admin";
  const waText = `Halo ${adminName}, saya sudah pelajari detail produk dan benefit di proposal akhir untuk ${proposal.business_name}. Penawarannya sangat menarik, saya setuju untuk amankan slot proyeknya ya!`;
  const waLink = `https://wa.me/${adminWa}?text=${encodeURIComponent(waText)}`;

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 bg-[radial-gradient(#e4e4e7_1px,transparent_1px)] dark:bg-[radial-gradient(#27272a_1px,transparent_1px)] [background-size:20px_20px] text-zinc-900 dark:text-zinc-100 print:bg-white print:text-black print:bg-none">
      {toastMsg && (
        <div className="fixed top-5 left-1/2 -translate-x-1/2 z-[80] bg-red-500 text-white px-5 py-3 rounded-xl shadow-lg text-sm font-medium">
          {toastMsg}
        </div>
      )}
      <div className="max-w-3xl mx-auto px-5 py-12 md:py-16">

        {/* ============================================================ */}
        {/* HEADER */}
        {/* ============================================================ */}
        <header className="text-center mb-12 break-inside-avoid">
          {proposal.status === "accepted" ? (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-100 dark:bg-green-900/30 border-2 border-green-400 dark:border-green-700 mb-5">
              <svg className="w-3 h-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
              <span className="text-xs font-bold text-green-700 dark:text-green-400">Diterima pada {formatDate(proposal.accepted_at || null)}</span>
            </div>
          ) : proposal.status === "rejected" ? (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800 border-2 border-zinc-300 dark:border-zinc-600 mb-5">
              <span className="text-xs font-bold text-zinc-500 dark:text-zinc-400">Penawaran Ditolak</span>
            </div>
          ) : (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-100 dark:bg-amber-900/30 border-2 border-amber-400 dark:border-amber-700 mb-5">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
              <span className="text-xs font-bold text-amber-700 dark:text-amber-400">Penawaran Aktif</span>
            </div>
          )}
          <h1 className="text-2xl md:text-3xl font-black text-zinc-900 dark:text-white leading-tight print:text-black">
            Proposal Solusi & Proyeksi Pertumbuhan Digital
          </h1>
          <p className="text-xl md:text-2xl font-black text-amber-600 mt-2 print:text-amber-700">
            {proposal.business_name}
          </p>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 font-medium mt-4 print:text-zinc-700">
            Disiapkan secara eksklusif oleh Tim Kantor Teman · {formatDate(proposal.created_at)}
          </p>
        </header>

        {/* ============================================================ */}
        {/* PRODUCT SHOWCASE */}
        {/* ============================================================ */}
        <section className="space-y-4 mb-12">
          <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-600 mb-2">Solusi yang Kami Siapkan untuk Anda</h2>
          <div className="grid grid-cols-1 gap-4">
            {proposal.services_detail.map((service, i) => {
              const benefits = getBenefits(service.name);
              const description = getServiceDescription(service.name);
              return (
                <div
                  key={i}
                  className="bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-700 rounded-2xl p-6 shadow-sm transition-all duration-300 ease-in-out hover:shadow-md hover:border-amber-500 break-inside-avoid print:border-zinc-300 print:shadow-none"
                >
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div>
                      <h3 className="text-lg font-bold text-zinc-900 dark:text-white print:text-black">{service.name}</h3>
                      <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1 leading-relaxed print:text-zinc-700">{description}</p>
                    </div>
                    <span className="shrink-0 text-sm font-bold text-amber-600 whitespace-nowrap print:text-amber-700">
                      {formatRupiah(service.price)}
                    </span>
                  </div>
                  <div className="border-t-2 border-zinc-100 pt-3 mt-3 print:border-zinc-200">
                    <p className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold mb-2">Dampak Langsung ke Bisnis Anda</p>
                    <ul className="space-y-1.5">
                      {benefits.map((b, j) => (
                        <li key={j} className="flex items-start gap-2 text-sm text-zinc-700 print:text-zinc-800">
                          <svg className="w-4 h-4 text-amber-500 mt-0.5 shrink-0 print:text-amber-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                          </svg>
                          <span>{b}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ============================================================ */}
        {/* TIMELINE INTERAKTIF */}
        {/* ============================================================ */}
        {timeline.length > 0 && (
          <section className="mb-12 break-inside-avoid">
            <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-600 mb-4">Alur Kerja & Timeline Pengerjaan</h2>
            <div className="bg-white border-2 border-zinc-200 rounded-2xl p-6 shadow-sm print:border-zinc-300 print:shadow-none">
              {/* Progress bar */}
              <div className="relative mb-6">
                <div className="h-2 bg-zinc-100 rounded-full">
                  <div className="h-2 bg-amber-500 rounded-full transition-all duration-500" style={{ width: "8%" }}></div>
                </div>
                <div className="flex justify-between mt-2">
                  <span className="text-[9px] text-amber-600 font-bold">Anda di sini</span>
                  <span className="text-xs font-semibold text-zinc-500">Proyek Selesai</span>
                </div>
              </div>
              <div className="space-y-0">
                {timeline.map((phase, idx) => (
                  <div key={idx} className="relative flex items-start gap-4 pb-5 last:pb-0">
                    {idx < timeline.length - 1 && (
                      <div className="absolute left-4 top-9 w-0.5 h-full bg-amber-200"></div>
                    )}
                    <div className="w-8 h-8 rounded-full bg-amber-500 text-white text-sm font-bold flex items-center justify-center shrink-0 mt-0.5 relative z-10 print:bg-amber-600">
                      {phase.sequence}
                    </div>
                    <div className="flex-1 pb-4 border-b border-zinc-100 last:border-0">
                      <h4 className="text-base font-bold text-zinc-900 print:text-black">{phase.title}</h4>
                      <p className="text-sm text-zinc-600 leading-relaxed mt-1 print:text-zinc-700">{phase.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Print-only timeline format */}
            <div className="hidden print:block mt-4">
              <ol className="list-none space-y-2">
                {timeline.map((phase) => (
                  <li key={phase.sequence} className="text-sm text-black">
                    <span className="font-bold">[{phase.sequence}] - {phase.title}:</span> {phase.description}
                  </li>
                ))}
              </ol>
            </div>
          </section>
        )}

        {/* ============================================================ */}
        {/* POSIBILITAS KEUNTUNGAN MASA DEPAN */}
        {/* ============================================================ */}
        {timeline.length > 0 && (
          <section className="mb-12 break-inside-avoid">
            <div className="bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-300 dark:border-amber-800 rounded-2xl p-6 print:bg-white print:border-amber-400">
              <h3 className="text-base font-black text-zinc-900 mb-4 print:text-black">
                Estimasi Nilai & Posibilitas Keuntungan Jangka Panjang
              </h3>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-amber-200 text-amber-700 flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">1</div>
                  <p className="text-sm text-zinc-800 leading-relaxed print:text-zinc-900">
                    <span className="font-bold">Penghematan Biaya Operasional:</span> Setelah proyek selesai, Anda tidak perlu lagi mengeluarkan biaya cetak brosur, sewa billboard, atau iklan fisik berulang. Semua aset digital bekerja otomatis 24/7.
                  </p>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-amber-200 text-amber-700 flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">2</div>
                  <p className="text-sm text-zinc-800 leading-relaxed print:text-zinc-900">
                    <span className="font-bold">Akumulasi Aset Organic Traffic:</span> Setiap bulan, trafik organik dari Google terus bertumbuh tanpa biaya tambahan. Ini adalah aset digital yang nilainya meningkat seiring waktu — menghasilkan leads gratis tanpa bakar duit iklan lagi.
                  </p>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-amber-200 text-amber-700 flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">3</div>
                  <p className="text-sm text-zinc-800 leading-relaxed print:text-zinc-900">
                    <span className="font-bold">Efek Compounding Jangka Panjang:</span> Bisnis yang sudah teroptimasi secara digital akan semakin mudah ditemukan, semakin dipercaya, dan semakin sulit disaingi oleh kompetitor yang baru mulai. Keunggulan ini terakumulasi setiap bulan.
                  </p>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ============================================================ */}
        {/* PRICING & DISCOUNT TABLE */}
        {/* ============================================================ */}
        <section className="bg-white border-2 border-zinc-200 rounded-2xl p-6 mb-12 shadow-sm break-inside-avoid print:border-zinc-300 print:shadow-none">
          <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-600 mb-5">Rincian Nilai Investasi</h2>

          <div className="space-y-3">
            {proposal.services_detail.map((service, i) => (
              <div key={i} className="flex justify-between items-center py-2 border-b-2 border-zinc-100 last:border-0 print:border-zinc-200">
                <span className="text-sm text-zinc-700 print:text-zinc-800">{service.name}</span>
                <span className="text-sm font-bold text-zinc-900 whitespace-nowrap print:text-black">{formatRupiah(service.price)}</span>
              </div>
            ))}
          </div>

          <div className="border-t-2 border-zinc-200 mt-4 pt-4 space-y-2 print:border-zinc-300">
            <div className="flex justify-between text-sm">
              <span className="text-zinc-600">Subtotal Nilai Jasa</span>
              <span className="text-zinc-800 font-medium print:text-zinc-900">{formatRupiah(subtotal)}</span>
            </div>
            {discount > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-amber-600 font-medium">Potongan Harga Promo 15%</span>
                <span className="text-amber-600 font-medium line-through">-{formatRupiah(discount)}</span>
              </div>
            )}
            <div className="flex justify-between items-center pt-3 border-t-2 border-zinc-200 print:border-zinc-300">
              <span className="text-sm font-bold text-zinc-600 print:text-zinc-700">Total Investasi Final</span>
              <span className="text-2xl md:text-3xl font-black text-amber-600 print:text-amber-700">{formatRupiah(finalTotal)}</span>
            </div>
          </div>
        </section>

        {/* ============================================================ */}
        {/* ROI CALCULATOR */}
        {/* ============================================================ */}
        {(!proposal.roi_data || proposal.roi_data.enabled) && (
        <section className="bg-white border-2 border-zinc-200 rounded-2xl p-6 mb-12 shadow-sm break-inside-avoid print:border-zinc-300 print:shadow-none">
          <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-600 mb-5">Kalkulasi Return on Investment</h2>
          {(() => {
            const roiMonths = proposal.roi_data?.roi_months || 3;
            const roiMultiplier = proposal.roi_data?.roi_multiplier || 3.5;
            const monthlyAdsCost = proposal.roi_data?.monthly_ads_cost || 5000000;
            const hasRetainer = proposal.roi_data?.has_retainer || false;
            const retainerPeriod = proposal.roi_data?.retainer_period || 0;
            const retainerMonthly = proposal.roi_data?.retainer_monthly || 0;
            const onetimeTotal = proposal.roi_data?.onetime_total || finalTotal;
            const ourTotalCost = proposal.roi_data?.our_total_cost || finalTotal;
            const comparisonPeriod = proposal.roi_data?.comparison_period || 12;
            const adsTotalCost = proposal.roi_data?.ads_total_cost || (monthlyAdsCost * 12);
            return (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-zinc-50 rounded-xl p-3 text-center border border-zinc-200">
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wide font-bold mb-1">Investasi</p>
                  <p className="text-sm md:text-base font-black text-zinc-900">{formatRupiah(ourTotalCost)}</p>
                  <p className="text-[10px] text-zinc-400 mt-0.5">{hasRetainer ? `${retainerPeriod} bulan` : "sekali bayar"}</p>
                </div>
                <div className="bg-amber-50 rounded-xl p-3 text-center border border-amber-200">
                  <p className="text-[10px] text-amber-700 uppercase tracking-wide font-bold mb-1">Estimasi Balik Modal</p>
                  <p className="text-sm md:text-base font-black text-amber-600">{roiMonths} Bulan</p>
                  <p className="text-[10px] text-amber-500 mt-0.5">berdasarkan proyeksi</p>
                </div>
                <div className="bg-green-50 rounded-xl p-3 text-center border border-green-200">
                  <p className="text-[10px] text-green-700 uppercase tracking-wide font-bold mb-1">Profit {comparisonPeriod} Bulan</p>
                  <p className="text-sm md:text-base font-black text-green-600">{formatRupiah(ourTotalCost * roiMultiplier)}</p>
                  <p className="text-[10px] text-green-500 mt-0.5">estimasi konservatif</p>
                </div>
              </div>
              {hasRetainer && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
                  <p className="text-[10px] text-amber-700 font-semibold">Rincian: {onetimeTotal > 0 ? `${formatRupiah(onetimeTotal)} (sekali bayar) + ` : ""}{formatRupiah(retainerMonthly)}/bulan × {retainerPeriod} bulan</p>
                </div>
              )}
              <div className="bg-zinc-50 border border-zinc-200 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <div className="flex justify-between text-[10px] text-zinc-500 font-bold mb-1">
                      <span>Bulan 1</span>
                      <span>Bulan {roiMonths} (BEP)</span>
                      <span>Bulan {comparisonPeriod}</span>
                    </div>
                    <div className="h-3 bg-zinc-200 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-gradient-to-r from-red-400 via-amber-400 to-green-500" style={{ width: "100%" }}></div>
                    </div>
                    <div className="flex justify-between text-[9px] text-zinc-400 mt-1">
                      <span>Investasi</span>
                      <span className="text-amber-600 font-bold">Balik Modal</span>
                      <span className="text-green-600 font-bold">Profit</span>
                    </div>
                  </div>
                </div>
              </div>
              <p className="text-[11px] text-zinc-500 text-center italic">Estimasi berdasarkan rata-rata performa klien kami di industri serupa. Hasil aktual dapat bervariasi.</p>
            </div>
            );
          })()}
        </section>
        )}

        {/* ============================================================ */}
        {/* COMPARISON TABLE: Google Ads vs Optimasi */}
        {/* ============================================================ */}
        {(!proposal.roi_data || proposal.roi_data.enabled) && (
        <section className="bg-white border-2 border-zinc-200 rounded-2xl p-6 mb-12 shadow-sm break-inside-avoid print:border-zinc-300 print:shadow-none">
          <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-600 mb-5">Perbandingan: Iklan Berbayar vs Optimasi Digital</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-zinc-200">
                  <th className="text-left py-3 text-xs text-zinc-500 font-bold uppercase tracking-wide">Aspek</th>
                  <th className="text-center py-3 text-xs text-zinc-400 font-bold uppercase tracking-wide">Google Ads</th>
                  <th className="text-center py-3 text-xs text-amber-600 font-bold uppercase tracking-wide">Optimasi Kami</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {(proposal.roi_data?.comparison_points && proposal.roi_data.comparison_points.length > 0) ? (
                  proposal.roi_data.comparison_points.map((point, i) => (
                    <tr key={i}>
                      <td className="py-3 text-zinc-700 font-medium">{point.aspect}</td>
                      <td className="py-3 text-center text-zinc-500">{point.ads}</td>
                      <td className="py-3 text-center text-amber-700 font-bold">{point.ours}</td>
                    </tr>
                  ))
                ) : (
                  (() => {
                    const hasRetainer = proposal.roi_data?.has_retainer || false;
                    const compPeriod = proposal.roi_data?.comparison_period || 12;
                    const adsCost = proposal.roi_data?.monthly_ads_cost || 5000000;
                    const ourCost = proposal.roi_data?.our_total_cost || finalTotal;
                    const adsTotalCost = proposal.roi_data?.ads_total_cost || (adsCost * 12);
                    const retainerMonthly = proposal.roi_data?.retainer_monthly || 0;
                    return (
                    <>
                      <tr>
                        <td className="py-3 text-zinc-700 font-medium">Biaya Bulanan</td>
                        <td className="py-3 text-center text-zinc-500">{formatRupiah(adsCost)}/bulan<br/><span className="text-[10px] text-red-500">terus-menerus</span></td>
                        <td className="py-3 text-center text-amber-700 font-bold">{hasRetainer ? `${formatRupiah(retainerMonthly)}/bulan` : formatRupiah(ourCost)}<br/><span className="text-[10px] text-green-600">{hasRetainer ? `${compPeriod} bulan kontrak` : "sekali bayar"}</span></td>
                      </tr>
                      <tr>
                        <td className="py-3 text-zinc-700 font-medium">Durasi Efek</td>
                        <td className="py-3 text-center text-zinc-500">Berhenti bayar = hilang</td>
                        <td className="py-3 text-center text-amber-700 font-bold">{hasRetainer ? "Akumulatif selama kontrak" : "Permanen & akumulatif"}</td>
                      </tr>
                      <tr>
                        <td className="py-3 text-zinc-700 font-medium">Total Biaya {compPeriod} Bulan</td>
                        <td className="py-3 text-center text-red-600 font-bold">{formatRupiah(adsTotalCost)}</td>
                        <td className="py-3 text-center text-green-600 font-bold">{formatRupiah(ourCost)}</td>
                      </tr>
                      <tr>
                        <td className="py-3 text-zinc-700 font-medium">Kepercayaan User</td>
                        <td className="py-3 text-center text-zinc-500">Rendah (label &ldquo;Iklan&rdquo;)</td>
                        <td className="py-3 text-center text-amber-700 font-bold">Tinggi (organik)</td>
                      </tr>
                      <tr>
                        <td className="py-3 text-zinc-700 font-medium">Kompetisi Harga</td>
                        <td className="py-3 text-center text-zinc-500">Makin mahal tiap tahun</td>
                        <td className="py-3 text-center text-amber-700 font-bold">Investasi tetap</td>
                      </tr>
                    </>
                    );
                  })()
                )}
              </tbody>
            </table>
          </div>
          <div className="mt-4 bg-amber-50 border border-amber-200 rounded-xl p-3 text-center">
            <p className="text-xs text-amber-800 font-semibold">Dengan optimasi digital, Anda menghemat hingga <span className="font-black">{formatRupiah((proposal.roi_data?.ads_total_cost || ((proposal.roi_data?.monthly_ads_cost || 5000000) * 12)) - (proposal.roi_data?.our_total_cost || finalTotal))}</span> dalam {proposal.roi_data?.comparison_period || 12} bulan dibanding iklan berbayar — dan hasilnya terus bekerja tanpa biaya tambahan.</p>
          </div>
        </section>
        )}

        {/* ============================================================ */}
        {/* CTA — Accept / Reject */}
        {/* ============================================================ */}
        <section className="space-y-4 print:hidden">
          {proposal.status === "accepted" ? (
            <div className="bg-green-50 border-2 border-green-400 rounded-2xl p-6 text-center">
              <svg className="w-10 h-10 text-green-500 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <h3 className="text-lg font-black text-green-800">Proposal Diterima!</h3>
              <p className="text-sm text-green-700 mt-1">Diterima pada {formatDate(proposal.accepted_at || null)}</p>
              <p className="text-sm text-zinc-600 mt-3">Tim kami akan segera menghubungi Anda untuk memulai proyek.</p>
            </div>
          ) : proposal.status === "rejected" ? (
            <div className="bg-zinc-100 border-2 border-zinc-300 rounded-2xl p-6 text-center">
              <p className="text-sm font-bold text-zinc-500">Penawaran ini telah ditolak.</p>
              <p className="text-xs text-zinc-400 mt-2">Hubungi kami jika Anda berubah pikiran.</p>
            </div>
          ) : (
            <>
              {timeLeft !== null && timeLeft > 0 && (
                <div className="bg-red-50 border-2 border-red-300 rounded-2xl p-4 text-center">
                  <p className="text-xs font-bold text-red-600 uppercase tracking-wide mb-1">Penawaran berakhir dalam</p>
                  <p className="text-2xl font-black text-red-700 tabular-nums">
                    {String(Math.floor(timeLeft / 3600000)).padStart(2, "0")}:{String(Math.floor((timeLeft % 3600000) / 60000)).padStart(2, "0")}:{String(Math.floor((timeLeft % 60000) / 1000)).padStart(2, "0")}
                  </p>
                </div>
              )}
              {timeLeft === 0 && (
                <div className="bg-zinc-100 border-2 border-zinc-300 rounded-2xl p-4 text-center">
                  <p className="text-sm font-bold text-zinc-500">Penawaran telah berakhir.</p>
                  <p className="text-xs text-zinc-400 mt-1">Hubungi kami untuk perpanjangan.</p>
                </div>
              )}
              {clientCount > 0 && (
                <div className="text-center py-2">
                  <p className="text-sm text-zinc-600 dark:text-zinc-400 font-medium">
                    {clientCount} klien sudah menggunakan layanan ini
                  </p>
                </div>
              )}
              <button
                onClick={() => setAcceptModal(true)}
                disabled={timeLeft === 0}
                className="block w-full text-center py-5 px-6 rounded-2xl bg-amber-500 hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 text-white font-black text-lg shadow-md border-b-4 border-amber-700 transition-all duration-200 hover:scale-[1.02]"
              >
                <span className="inline-flex items-center gap-2.5">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                  Setuju & Mulai Project
                </span>
              </button>
              <button
                onClick={() => setRejectModal(true)}
                className="block w-full text-center py-3 px-6 rounded-2xl bg-white border-2 border-zinc-200 hover:border-zinc-400 text-zinc-600 font-semibold text-sm transition-all duration-200"
              >
                Tolak Penawaran
              </button>
              <p className="text-center text-xs text-zinc-500">
                Atau hubungi kami langsung via{" "}
                <a href={waLink} target="_blank" rel="noopener noreferrer" className="text-amber-600 font-semibold underline">WhatsApp</a>
              </p>
            </>
          )}
        </section>

        {/* Accept Modal */}
        {acceptModal && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 print:hidden">
            <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
              <h3 className="text-lg font-black text-zinc-900 mb-1">Konfirmasi Penerimaan</h3>
              <p className="text-sm text-zinc-500 mb-5">Isi data di bawah untuk mengkonfirmasi persetujuan Anda.</p>
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-bold text-zinc-600 uppercase tracking-wide">Nama Lengkap</label>
                  <input
                    type="text"
                    value={clientName}
                    onChange={e => setClientName(e.target.value)}
                    placeholder="Nama Anda"
                    className="mt-1 w-full border-2 border-zinc-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-amber-400"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-zinc-600 uppercase tracking-wide">Nomor WhatsApp</label>
                  <input
                    type="tel"
                    value={clientPhone}
                    onChange={e => setClientPhone(e.target.value)}
                    placeholder="08xxxxxxxxxx"
                    className="mt-1 w-full border-2 border-zinc-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-amber-400"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-zinc-600 uppercase tracking-wide">Catatan (opsional)</label>
                  <textarea
                    value={acceptNotes}
                    onChange={e => setAcceptNotes(e.target.value)}
                    placeholder="Ada hal yang ingin disampaikan?"
                    rows={2}
                    className="mt-1 w-full border-2 border-zinc-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-amber-400 resize-none"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-5">
                <button onClick={() => setAcceptModal(false)} className="flex-1 py-2.5 rounded-xl border-2 border-zinc-200 text-zinc-600 font-semibold text-sm">
                  Batal
                </button>
                <button
                  onClick={handleAccept}
                  disabled={submitting || !clientName.trim() || !clientPhone.trim()}
                  className="flex-1 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white font-black text-sm transition-colors"
                >
                  {submitting ? "Mengirim..." : "Konfirmasi"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Reject Modal */}
        {rejectModal && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 print:hidden">
            <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
              <h3 className="text-lg font-black text-zinc-900 mb-1">Tolak Penawaran</h3>
              <p className="text-sm text-zinc-500 mb-5">Boleh ceritakan alasannya? (opsional)</p>
              <textarea
                value={rejectReason}
                onChange={e => setRejectReason(e.target.value)}
                placeholder="Alasan penolakan..."
                rows={3}
                className="w-full border-2 border-zinc-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-zinc-400 resize-none"
              />
              <div className="flex gap-3 mt-5">
                <button onClick={() => setRejectModal(false)} className="flex-1 py-2.5 rounded-xl border-2 border-zinc-200 text-zinc-600 font-semibold text-sm">
                  Batal
                </button>
                <button
                  onClick={handleReject}
                  disabled={submitting}
                  className="flex-1 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-900 disabled:opacity-50 text-white font-semibold text-sm transition-colors"
                >
                  {submitting ? "Mengirim..." : "Tolak Penawaran"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* PRINT-ONLY FOOTER */}
        {/* ============================================================ */}
        <footer className="hidden print:block border-t-2 border-zinc-300 pt-6 mt-12 text-center break-inside-avoid">
          <p className="text-sm text-zinc-700 leading-relaxed max-w-xl mx-auto">
            Proposal ini diterbitkan oleh Kantor Teman Digital Agency. Untuk konfirmasi dan memulai proyek, hubungi tim kami melalui WhatsApp.
          </p>
          <p className="text-xs text-zinc-500 mt-3">&copy; {new Date().getFullYear()} Kantor Teman</p>
        </footer>

      </div>
    </div>
  );
}
