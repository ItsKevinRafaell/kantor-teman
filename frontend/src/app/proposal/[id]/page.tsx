"use client";
import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import { formatRupiah } from "../../../utils/formatter";
import { ServiceCardList } from "../../../components/proposal/ServiceCardList";
import { ProposalTimeline } from "../../../components/proposal/ProposalTimeline";
import ProposalHero from "../../../components/proposal/ProposalHero";
import ProposalPricing from "../../../components/proposal/ProposalPricing";
import ProposalROI from "../../../components/proposal/ProposalROI";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
}

const LONG_TERM_BENEFITS = [
  "Penghematan Biaya Operasional: Setelah proyek selesai, Anda tidak perlu lagi mengeluarkan biaya cetak brosur, sewa billboard, atau iklan fisik berulang. Semua aset digital bekerja otomatis 24/7.",
  "Akumulasi Aset Organic Traffic: Setiap bulan, trafik organik dari Google terus bertumbuh tanpa biaya tambahan. Ini adalah aset digital yang nilainya meningkat seiring waktu — menghasilkan leads gratis tanpa bakar duit iklan lagi.",
  "Efek Compounding Jangka Panjang: Bisnis yang sudah teroptimasi secara digital akan semakin mudah ditemukan, semakin dipercaya, dan semakin sulit disaingi oleh kompetitor yang baru mulai. Keunggulan ini terakumulasi setiap bulan.",
];

interface Proposal {
  id: string; lead_id: number; business_name: string | null; slug: string | null;
  services_detail: { name: string; price: number; features: string[] }[];
  total_price: number; base_price: number | null; discount_price: number | null;
  status: string; created_at: string | null;
  timeline_data?: { sequence: number; title: string; description: string }[];
  roi_data?: { enabled?: boolean; roi_months?: number; roi_multiplier?: number; monthly_ads_cost?: number; has_retainer?: boolean; retainer_period?: number; retainer_monthly?: number; onetime_total?: number; our_total_cost?: number; ads_total_cost?: number; comparison_period?: number; comparison_points?: { aspect: string; ads: string; ours: string }[] } | null;
  admin_wa?: string; admin_name?: string; accepted_at?: string | null;
  discount_expires_at?: string | null;
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
  const analyticsIdRef = useRef<string | null>(null);
  const lastPingRef = useRef<number>(Date.now());

  // Countdown timer
  useEffect(() => {
    if (!proposal?.discount_expires_at) { setTimeLeft(null); return; }
    const expiresMs = new Date(proposal.discount_expires_at).getTime();
    if (isNaN(expiresMs)) { setTimeLeft(null); return; }
    const interval = setInterval(() => {
      const remaining = expiresMs - Date.now();
      if (remaining <= 0) { setTimeLeft(0); clearInterval(interval); return; }
      setTimeLeft(remaining);
    }, 1000);
    return () => clearInterval(interval);
  }, [proposal?.discount_expires_at]);

  // Load proposal
  async function refreshProposal() { const res = await fetch(`${API_BASE}/api/proposals/public/${id}`); if (res.ok) setProposal(await res.json()); }

  async function handleAccept() {
    if (!clientName.trim() || !clientPhone.trim() || !proposal?.slug) return;
    setSubmitting(true);
    try { const res = await fetch(`${API_BASE}/api/proposals/public/${proposal.slug}/accept`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_name: clientName, client_phone: clientPhone, accept_notes: acceptNotes || null }) }); if (!res.ok) throw new Error(); await refreshProposal(); setAcceptModal(false); }
    catch { setToastMsg("Gagal mengirim."); setTimeout(() => setToastMsg(null), 4000); } finally { setSubmitting(false); }
  }

  async function handleReject() {
    if (!proposal?.slug) return;
    setSubmitting(true);
    try { const res = await fetch(`${API_BASE}/api/proposals/public/${proposal.slug}/reject`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: rejectReason || null }) }); if (!res.ok) throw new Error(); await refreshProposal(); setRejectModal(false); }
    catch { setToastMsg("Gagal mengirim."); setTimeout(() => setToastMsg(null), 4000); } finally { setSubmitting(false); }
  }

  useEffect(() => {
    async function load() {
      try { const res = await fetch(`${API_BASE}/api/proposals/public/${id}`); if (!res.ok) throw new Error("Proposal tidak ditemukan"); setProposal(await res.json()); }
      catch (e: any) { setError(e.message || "Gagal memuat proposal"); } finally { setLoading(false); }
    }
    load();
  }, [id]);

  // Analytics tracking
  useEffect(() => {
    if (!proposal) return;
    let pingInterval: NodeJS.Timeout | null = null;
    fetch(`${API_BASE}/api/proposals/track/open`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ proposal_id: proposal.id }) })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.analytics_id) { analyticsIdRef.current = data.analytics_id; lastPingRef.current = Date.now(); pingInterval = setInterval(() => { if (document.hidden || !analyticsIdRef.current) return; const elapsed = Math.round((Date.now() - lastPingRef.current) / 1000); lastPingRef.current = Date.now(); if (elapsed > 0 && elapsed <= 60) fetch(`${API_BASE}/api/proposals/track/ping`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ analytics_id: analyticsIdRef.current, seconds: elapsed, sections_viewed: [] }) }).catch(() => {}); }, 10000); } })
      .catch(() => {});
    return () => { if (pingInterval) clearInterval(pingInterval); };
  }, [proposal]);

  useEffect(() => {
    if (!proposal?.slug) return;
    const mountTime = Date.now(); const slug = proposal.slug; let sent = false;
    function sendDuration() { if (sent) return; sent = true; const seconds = Math.round((Date.now() - mountTime) / 1000); if (seconds <= 0) return; const url = `${API_BASE}/api/proposals/${slug}/view-duration`; try { if (navigator.sendBeacon) navigator.sendBeacon(url, new Blob([JSON.stringify({ duration_seconds: seconds })], { type: "application/json" })); else fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ duration_seconds: seconds }), keepalive: true }).catch(() => {}); } catch {} }
    function onVisibility() { if (document.visibilityState === "hidden") sendDuration(); }
    window.addEventListener("beforeunload", sendDuration); document.addEventListener("visibilitychange", onVisibility);
    return () => { window.removeEventListener("beforeunload", sendDuration); document.removeEventListener("visibilitychange", onVisibility); sendDuration(); };
  }, [proposal?.slug]);

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-white"><div className="animate-pulse text-zinc-500 text-lg font-medium">Memuat proposal...</div></div>;
  if (error || !proposal) return <div className="min-h-screen flex items-center justify-center bg-white"><div className="text-center"><h1 className="text-3xl font-bold text-zinc-900 mb-2">404</h1><p className="text-zinc-600">{error || "Proposal tidak ditemukan"}</p></div></div>;

  const timeline = proposal.timeline_data || [];
  const adminWa = proposal.admin_wa || "";
  const adminName = proposal.admin_name || "Admin";
  const waText = `Halo ${adminName}, saya sudah pelajari detail produk dan benefit di proposal akhir untuk ${proposal.business_name}. Penawarannya sangat menarik, saya setuju untuk amankan slot proyeknya ya!`;
  const waLink = `https://wa.me/${adminWa}?text=${encodeURIComponent(waText)}`;
  const finalTotal = proposal.discount_price || proposal.total_price;

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 bg-[radial-gradient(#e4e4e7_1px,transparent_1px)] dark:bg-[radial-gradient(#27272a_1px,transparent_1px)] [background-size:20px_20px] text-zinc-900 dark:text-zinc-100 print:bg-white print:text-black">
      {toastMsg && <div className="fixed top-5 left-1/2 -translate-x-1/2 z-[80] bg-red-500 text-white px-5 py-3 rounded-xl shadow-lg text-sm font-medium">{toastMsg}</div>}

      <div className="max-w-3xl mx-auto px-5 py-12 md:py-16">
        <ProposalHero proposal={proposal} />
        <ServiceCardList services={proposal.services_detail} />
        <ProposalTimeline timeline={timeline} />

        {/* Long-term benefits */}
        {timeline.length > 0 && (
          <section className="mb-12 break-inside-avoid">
            <div className="bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-300 dark:border-amber-800 rounded-2xl p-6 print:bg-white print:border-amber-400">
              <h3 className="text-base font-black text-zinc-900 mb-4 print:text-black">Estimasi Nilai & Posibilitas Keuntungan Jangka Panjang</h3>
              <div className="space-y-3">
                {LONG_TERM_BENEFITS.map((text, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-amber-200 text-amber-700 flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">{i + 1}</div>
                    <p className="text-sm text-zinc-800 leading-relaxed print:text-zinc-900"><span className="font-bold">{text.split(":")[0]}:</span> {text.split(":").slice(1).join(":").trim()}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        <ProposalPricing proposal={proposal} />

        {/* CTA Section */}
        <section className="space-y-4 print:hidden">
          {proposal.status === "accepted" ? (
            <div className="bg-green-50 border-2 border-green-400 rounded-2xl p-6 text-center">
              <svg className="w-10 h-10 text-green-500 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <h3 className="text-lg font-black text-green-800">Proposal Diterima!</h3>
              <p className="text-sm text-green-700 mt-1">Diterima pada {formatDate(proposal.accepted_at || null)}</p>
            </div>
          ) : proposal.status === "rejected" ? (
            <div className="bg-zinc-100 border-2 border-zinc-300 rounded-2xl p-6 text-center">
              <p className="text-sm font-bold text-zinc-500">Penawaran ini telah ditolak.</p>
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
              <button onClick={() => setAcceptModal(true)} disabled={timeLeft === 0}
                className="block w-full text-center py-5 px-6 rounded-2xl bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white font-black text-lg shadow-md border-b-4 border-amber-700 transition-all hover:scale-[1.02]">
                Setuju & Mulai Project
              </button>
              <button onClick={() => setRejectModal(true)} className="block w-full text-center py-3 px-6 rounded-2xl bg-white border-2 border-zinc-200 hover:border-zinc-400 text-zinc-600 font-semibold text-sm">Tolak Penawaran</button>
              <p className="text-center text-xs text-zinc-500">Atau hubungi kami via <a href={waLink} target="_blank" rel="noopener noreferrer" className="text-amber-600 font-semibold underline">WhatsApp</a></p>
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
                  <label className="text-xs font-bold text-zinc-600 uppercase">Nama Lengkap</label>
                  <input type="text" value={clientName} onChange={e => setClientName(e.target.value)} placeholder="Nama Anda"
                    className="mt-1 w-full border-2 border-zinc-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-amber-400" />
                </div>
                <div>
                  <label className="text-xs font-bold text-zinc-600 uppercase">Nomor WhatsApp</label>
                  <input type="tel" value={clientPhone} onChange={e => setClientPhone(e.target.value)} placeholder="08xxxxxxxxxx"
                    className="mt-1 w-full border-2 border-zinc-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-amber-400" />
                </div>
                <div>
                  <label className="text-xs font-bold text-zinc-600 uppercase">Catatan (opsional)</label>
                  <textarea value={acceptNotes} onChange={e => setAcceptNotes(e.target.value)} rows={2}
                    className="mt-1 w-full border-2 border-zinc-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-amber-400 resize-none" />
                </div>
              </div>
              <div className="flex gap-3 mt-5">
                <button onClick={() => setAcceptModal(false)} className="flex-1 py-2.5 rounded-xl border-2 border-zinc-200 text-zinc-600 font-semibold text-sm">Batal</button>
                <button onClick={handleAccept} disabled={submitting || !clientName.trim() || !clientPhone.trim()}
                  className="flex-1 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white font-black text-sm">
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
              <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} rows={3}
                className="w-full border-2 border-zinc-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-zinc-400 resize-none" />
              <div className="flex gap-3 mt-5">
                <button onClick={() => setRejectModal(false)} className="flex-1 py-2.5 rounded-xl border-2 border-zinc-200 text-zinc-600 font-semibold text-sm">Batal</button>
                <button onClick={handleReject} disabled={submitting}
                  className="flex-1 py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-900 disabled:opacity-50 text-white font-semibold text-sm">
                  {submitting ? "Mengirim..." : "Tolak Penawaran"}
                </button>
              </div>
            </div>
          </div>
        )}

        <footer className="hidden print:block border-t-2 border-zinc-300 pt-6 mt-12 text-center break-inside-avoid">
          <p className="text-sm text-zinc-700 leading-relaxed max-w-xl mx-auto">Proposal ini diterbitkan oleh Kantor Teman Digital Agency.</p>
          <p className="text-xs text-zinc-500 mt-3">&copy; {new Date().getFullYear()} Kantor Teman</p>
        </footer>
      </div>
    </div>
  );
}