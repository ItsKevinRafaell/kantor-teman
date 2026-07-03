"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useParams } from "next/navigation";
import { Download, ExternalLink } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface PublicReport {
  id: string;
  title: string;
  report_type: string;
  service_type: string | null;
  metrics: Record<string, any>;
  evidence: Record<string, any>;
  narrative: {
    executive_summary?: string;
    highlights?: string[];
    issues?: string[];
    next_steps?: string[];
    notes?: string;
  };
  month_number: number | null;
  open_count: number;
  max_duration_seconds: number;
  download_document_id?: string | null;
  created_at: string;
}

interface ComparisonGroup {
  title?: string;
  reference_label?: string;
  current_label?: string;
  notes?: string;
  rows: { label?: string; current?: any; previous?: any; lower_is_better?: boolean; delta?: any }[];
}

const SERVICE_LABELS: Record<string, string> = {
  seo_gmaps: "SEO & Google Maps",
  maintenance: "Maintenance Website",
  sosmed: "Kelola Sosial Media",
  web_dev: "Web Development",
  web_dev_bulanan: "Web Development Bulanan",
  branding: "Branding & Identitas Visual",
  general: "Layanan Umum",
};

function valueText(value: any) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return value.toLocaleString("id-ID");
  return String(value);
}

function deltaText(delta: any, lowerIsBetter = false) {
  if (!delta) return "Komparasi belum diisi";
  const rawDelta = Number(delta.delta);
  if (!Number.isFinite(rawDelta)) return "Komparasi belum diisi";
  const pct = typeof delta.delta_pct === "number" ? ` (${delta.delta_pct > 0 ? "+" : ""}${delta.delta_pct.toLocaleString("id-ID")}%)` : "";
  if (rawDelta === 0) return `tetap: ${valueText(rawDelta)}${pct}`;
  const improved = lowerIsBetter ? rawDelta < 0 : rawDelta > 0;
  return `${improved ? "membaik" : "perlu perhatian"}: ${rawDelta > 0 ? "+" : ""}${valueText(rawDelta)}${pct}`;
}

function ComparisonRow({ label, delta, lowerIsBetter = false }: { label: string; delta: any; lowerIsBetter?: boolean }) {
  return (
    <tr>
      <th className="bg-neutral-50 px-3 py-2 text-left text-xs font-bold text-neutral-600">{label}</th>
      <td className="px-3 py-2 text-sm text-neutral-700">{valueText(delta?.previous)}</td>
      <td className="px-3 py-2 text-sm font-semibold text-neutral-900">{valueText(delta?.current)}</td>
      <td className="px-3 py-2 text-sm text-neutral-700">{deltaText(delta, lowerIsBetter)}</td>
    </tr>
  );
}

function ReportComparisonBlocks({ report }: { report: PublicReport }) {
  const comparisons = report.metrics?.comparisons || {};
  const referenceLabel = comparisons.reference_label || (report.report_type === "completion" ? "data awal proyek" : "bulan lalu");
  const showTargets = report.report_type === "monthly";
  const comparisonRows = Array.isArray(comparisons.metrics) ? comparisons.metrics : [];
  const targets = report.metrics?.next_month_targets || {};
  const targetRows = Array.isArray(targets.metrics) ? targets.metrics : [];
  const hasTargets = targetRows.some((item: any) => item.value !== null && item.value !== undefined && item.value !== "") || targets.notes;

  return (
    <div className="mt-4 space-y-4">
      <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white">
        <div className="border-b border-neutral-200 px-4 py-3">
          <h3 className="text-sm font-bold text-neutral-900">Komparasi Performa</h3>
          <p className="mt-1 text-xs text-neutral-500">Pembanding: {referenceLabel}</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-neutral-200 text-left text-xs text-neutral-500">
                <th className="px-3 py-2">Metric</th>
                <th className="px-3 py-2 capitalize">{referenceLabel}</th>
                <th className="px-3 py-2">Sekarang</th>
                <th className="px-3 py-2">Catatan angka</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {comparisonRows.length > 0 ? comparisonRows.map((item: any) => (
                <ComparisonRow key={item.key || item.label} label={item.label || item.key} delta={item.delta} lowerIsBetter={!!item.lower_is_better} />
              )) : (
                <tr><td colSpan={4} className="px-3 py-3 text-sm text-neutral-500">Komparasi belum diisi.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="border-t border-neutral-100 bg-neutral-50 px-4 py-3">
          <p className="text-xs font-bold uppercase tracking-wide text-neutral-500">Notes komparasi</p>
          <p className="mt-1 text-sm leading-6 text-neutral-700">{comparisons.notes || "Belum ada notes komparasi."}</p>
        </div>
      </div>

      {showTargets && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <h3 className="text-sm font-bold text-amber-950">Target Bulan Depan</h3>
          {hasTargets ? (
            <>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {targetRows.map((item: any) => (
                  <div key={item.key || item.label} className="rounded-lg bg-white px-3 py-2">
                    <p className="text-xs font-semibold text-amber-800">{item.label || item.key}</p>
                    <p className="mt-1 text-base font-bold text-neutral-900">{valueText(item.value)}</p>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-sm leading-6 text-amber-950">{targets.notes || "Notes target belum diisi."}</p>
            </>
          ) : (
            <p className="mt-2 text-sm text-amber-900">Target bulan depan belum diisi.</p>
          )}
        </div>
      )}
    </div>
  );
}

function ComparisonGroupTable({ group }: { group: ComparisonGroup }) {
  const ref = group.reference_label || "Pembanding";
  const cur = group.current_label || "Sekarang";
  return (
    <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white">
      <div className="border-b border-neutral-200 px-4 py-3">
        <h3 className="text-sm font-bold text-neutral-900">{group.title || "Komparasi Performa"}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-neutral-200 text-left text-xs text-neutral-500">
              <th className="px-3 py-2">Metric</th>
              <th className="px-3 py-2 capitalize">{ref}</th>
              <th className="px-3 py-2">{cur}</th>
              <th className="px-3 py-2">Perubahan</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {group.rows.map((item, index) => (
              <tr key={`${item.label}-${index}`}>
                <th className="bg-neutral-50 px-3 py-2 text-left text-xs font-bold text-neutral-600">{item.label}</th>
                <td className="px-3 py-2 text-sm text-neutral-700">{valueText(item.previous)}</td>
                <td className="px-3 py-2 text-sm font-semibold text-neutral-900">{valueText(item.current)}</td>
                <td className="px-3 py-2 text-sm text-neutral-700">{deltaText(item.delta, item.lower_is_better)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {group.notes && (
        <div className="border-t border-neutral-100 bg-neutral-50 px-4 py-3">
          <p className="text-xs font-bold uppercase tracking-wide text-neutral-500">Catatan</p>
          <p className="mt-1 text-sm leading-6 text-neutral-700">{group.notes}</p>
        </div>
      )}
    </div>
  );
}

function ListBlock({ items, empty }: { items?: string[]; empty: string }) {
  if (!items || items.length === 0) return <p className="text-sm text-neutral-500">{empty}</p>;
  return (
    <ul className="space-y-2 text-sm text-neutral-700">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="rounded-lg border border-neutral-200 bg-white px-3 py-2">{item}</li>
      ))}
    </ul>
  );
}

function ServiceMetrics({ report }: { report: PublicReport }) {
  const service = report.metrics?.service || {};
  const pagespeed = report.metrics?.pagespeed || {};
  const wrapMetrics = (children: ReactNode) => (
    <>
      <div className="grid gap-3 md:grid-cols-2">{children}</div>
      <ReportComparisonBlocks report={report} />
    </>
  );
  if (report.service_type === "seo_gmaps") {
    const gsc = service.gsc || {};
    const gbp = service.google_business || {};
    return wrapMetrics(
      <>
        <Metric label="GSC Clicks" value={gsc.clicks} />
        <Metric label="GSC Impressions" value={gsc.impressions} />
        <Metric label="CTR" value={gsc.ctr} />
        <Metric label="Average Position" value={gsc.average_position} />
        <Metric label="GBP Views" value={gbp.views} />
        <Metric label="GBP Calls" value={gbp.calls} />
        <Metric label="Directions" value={gbp.directions} />
        <Metric label="Website Clicks" value={gbp.website_clicks} />
      </>
    );
  }
  if (report.service_type === "maintenance") {
    const backup = service.backup || {};
    const updates = service.updates || {};
    const health = service.health || {};
    return wrapMetrics(
      <>
        <Metric label="Backup terakhir" value={backup.last_backup_at} />
        <Metric label="Status backup" value={backup.backup_status} />
        <Metric label="Update core" value={updates.core_updates} />
        <Metric label="Update plugin" value={updates.plugin_updates} />
        <Metric label="Update theme" value={updates.theme_updates} />
        <Metric label="Security/site health" value={health.security_status} />
        <Metric label="Uptime" value={health.uptime} />
        <Metric label="Insiden" value={health.incidents} />
      </>
    );
  }
  if (report.service_type === "sosmed") {
    const social = service.social || {};
    return wrapMetrics(
      <>
        <Metric label="Konten publish" value={social.posts} />
        <Metric label="Reach" value={social.reach} />
        <Metric label="Engagement" value={social.engagement} />
        <Metric label="Perubahan followers" value={social.followers_delta} />
      </>
    );
  }
  if (service.retainer) {
    const retainer = service.retainer;
    return (
      <>
        <div className="md:col-span-2 rounded-xl border-2 border-amber-200 bg-amber-50 p-4">
          <h3 className="text-sm font-bold text-amber-800 mb-3">📊 Before/After Retainer</h3>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg bg-white border border-amber-200 p-3">
              <p className="text-xs font-bold text-amber-700 mb-2">📌 Before (Baseline)</p>
              <p className="text-sm text-neutral-700 whitespace-pre-wrap">{retainer.before || "Belum ada data before."}</p>
            </div>
            <div className="rounded-lg bg-white border border-green-200 p-3">
              <p className="text-xs font-bold text-green-700 mb-2">✅ After (Hasil)</p>
              <p className="text-sm text-neutral-700 whitespace-pre-wrap">{retainer.after || "Belum ada data after."}</p>
            </div>
          </div>
          {retainer.notes && (
            <div className="mt-3 rounded-lg bg-white border border-neutral-200 p-3">
              <p className="text-xs font-bold text-neutral-600 mb-1">Catatan Analisis</p>
              <p className="text-sm text-neutral-700 whitespace-pre-wrap">{retainer.notes}</p>
            </div>
          )}
        </div>
        <ReportComparisonBlocks report={report} />
      </>
    );
  }
  if (report.service_type === "branding") {
    const branding = service.branding || {};
    return wrapMetrics(
      <>
        <Metric label="Deliverables" value={branding.deliverables} />
        <Metric label="Revisi" value={branding.revision_round} />
        <Metric label="Approval" value={branding.approval_status} />
        <Metric label="Asset final" value={branding.asset_link} />
      </>
    );
  }
  const delivery = service.delivery || {};
  return wrapMetrics(
    <>
      <Metric label="Halaman selesai" value={delivery.pages_done} />
      <Metric label="Fitur selesai" value={delivery.features_done} />
      <Metric label="QA" value={delivery.qa_status} />
      <Metric label="PageSpeed mobile" value={pagespeed.performance_score ? `${pagespeed.performance_score}/100` : pagespeed.reason || pagespeed.status} />
    </>
  );
}

function Metric({ label, value }: { label: string; value: any }) {
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{label}</p>
      <p className="mt-1 text-lg font-bold text-neutral-900">{valueText(value)}</p>
    </div>
  );
}

export default function PublicClientReportPage() {
  const params = useParams();
  const slug = params.slug as string;
  const [report, setReport] = useState<PublicReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const openedAtRef = useRef(Date.now());

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/reports/public/${slug}`);
        if (!res.ok) throw new Error("Laporan tidak ditemukan");
        setReport(await res.json());
      } catch (e: any) {
        setError(e.message || "Gagal memuat laporan");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [slug]);

  useEffect(() => {
    if (!slug) return;
    openedAtRef.current = Date.now();
    function sendDuration() {
      const duration = Math.floor((Date.now() - openedAtRef.current) / 1000);
      if (duration <= 0) return;
      const payload = JSON.stringify({ duration_seconds: duration });
      if (navigator.sendBeacon) {
        navigator.sendBeacon(`${API_BASE}/api/reports/public/${slug}/duration`, new Blob([payload], { type: "application/json" }));
        return;
      }
      fetch(`${API_BASE}/api/reports/public/${slug}/duration`, { method: "POST", headers: { "Content-Type": "application/json" }, body: payload }).catch(() => {});
    }
    const onVisibility = () => { if (document.visibilityState === "hidden") sendDuration(); };
    const interval = setInterval(sendDuration, 15000);
    window.addEventListener("beforeunload", sendDuration);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      sendDuration();
      clearInterval(interval);
      window.removeEventListener("beforeunload", sendDuration);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [slug]);

  if (loading) return <div className="min-h-screen bg-neutral-50 p-8 text-center text-sm text-neutral-500">Memuat laporan...</div>;
  if (error || !report) return <div className="min-h-screen bg-neutral-50 p-8 text-center text-sm text-neutral-500">{error || "Laporan tidak ditemukan"}</div>;

  const workspace = report.metrics?.workspace || {};
  const evidence = [
    ...(report.evidence?.workspace_evidence || []),
    ...(report.evidence?.items || []),
  ];
  const comparisonGroups: ComparisonGroup[] = report.metrics?.comparison_groups || [];
  const pagespeed = report.metrics?.pagespeed || {};
  const downloadUrl = report.download_document_id ? `${API_BASE}/api/reports/public/${slug}/download` : null;

  return (
    <main className="min-h-screen bg-neutral-50 text-neutral-900">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-amber-700">Laporan Klien</p>
            <h1 className="mt-1 text-xl font-bold leading-tight">{report.title}</h1>
            <p className="mt-1 text-sm text-neutral-500">{SERVICE_LABELS[report.service_type || "general"] || report.service_type || "Layanan"} · {new Date(report.created_at).toLocaleDateString("id-ID")}</p>
          </div>
          {downloadUrl && (
            <a href={downloadUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2 text-sm font-bold text-white hover:bg-amber-600">
              <Download size={16} /> Download PDF
            </a>
          )}
        </div>
      </header>

      <div className="mx-auto max-w-4xl space-y-5 px-4 py-6">
        <section className="rounded-2xl border border-neutral-200 bg-white p-5">
          <h2 className="text-base font-bold">Ringkasan Eksekutif</h2>
          <p className="mt-2 text-sm leading-7 text-neutral-700">{report.narrative?.executive_summary || "Ringkasan belum tersedia."}</p>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <Metric label="Progress tugas" value={`${workspace.completion_pct || 0}%`} />
            <Metric label="Tugas selesai" value={`${workspace.completed_tasks || 0} / ${workspace.total_tasks || 0}`} />
            <Metric label="PageSpeed" value={pagespeed.performance_score ? `${pagespeed.performance_score}/100` : pagespeed.reason || pagespeed.status} />
            <Metric label="Dibuka" value={`${report.open_count || 0}x`} />
          </div>
        </section>

        <section className="rounded-2xl border border-neutral-200 bg-white p-5">
          <h2 className="mb-3 text-base font-bold">Metric Layanan</h2>
          <ServiceMetrics report={report} />
        </section>

        {comparisonGroups.length > 0 && (
          <div className="space-y-4">
            {comparisonGroups.map((group, index) => <ComparisonGroupTable key={`${group.title}-${index}`} group={group} />)}
          </div>
        )}

        <section className="grid gap-5 md:grid-cols-3">
          <div className="rounded-2xl border border-neutral-200 bg-white p-5">
            <h2 className="mb-3 text-base font-bold">Highlight</h2>
            <ListBlock items={report.narrative?.highlights} empty="Belum ada highlight manual." />
          </div>
          <div className="rounded-2xl border border-neutral-200 bg-white p-5">
            <h2 className="mb-3 text-base font-bold">Catatan</h2>
            <ListBlock items={report.narrative?.issues} empty="Tidak ada issue yang dicatat." />
          </div>
          <div className="rounded-2xl border border-neutral-200 bg-white p-5">
            <h2 className="mb-3 text-base font-bold">Rencana Berikutnya</h2>
            <ListBlock items={report.narrative?.next_steps} empty="Rencana berikutnya belum diisi." />
          </div>
        </section>

        <section className="rounded-2xl border border-neutral-200 bg-white p-5">
          <h2 className="mb-3 text-base font-bold">Bukti Pengerjaan</h2>
          {evidence.length === 0 ? (
            <p className="text-sm text-neutral-500">Belum ada bukti/link yang dilampirkan.</p>
          ) : (
            <div className="grid gap-4">
              {evidence.slice(0, 20).map((item: any, index: number) => {
                const url = item.url || item.file_path || item.link || "";
                const absoluteUrl = url && url.startsWith("/") ? `${API_BASE}${url}` : url;
                const label = item.label || item.title || item.file_name || "Bukti";
                const isImage = (item.file_type || "").toLowerCase().startsWith("image/") || /\.(png|jpe?g|webp|gif)$/i.test(url);
                if (isImage && absoluteUrl) {
                  return (
                    <div key={`${url}-${index}`} className="rounded-xl border border-neutral-200 p-3">
                      <p className="mb-2 text-sm font-semibold text-neutral-900">{label}</p>
                      <a href={absoluteUrl} target="_blank" rel="noopener noreferrer" className="block">
                        <img src={absoluteUrl} alt={label} className="max-h-96 w-full rounded-lg object-contain" />
                      </a>
                    </div>
                  );
                }
                return (
                  <div key={`${url}-${index}`} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-neutral-200 px-3 py-2 text-sm">
                    <span className="font-semibold">{label}</span>
                    {absoluteUrl ? (
                      <a href={absoluteUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-amber-700 hover:underline">
                        <ExternalLink size={13} /> Buka
                      </a>
                    ) : <span className="text-neutral-400">Tidak ada link</span>}
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
