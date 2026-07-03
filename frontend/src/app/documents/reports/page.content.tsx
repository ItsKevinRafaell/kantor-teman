"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { BarChart3, Copy, Download, ExternalLink, FileText, Plus, RefreshCw } from "lucide-react";
import Breadcrumb from "../../../components/Breadcrumb";
import Toast from "../../../components/Toast";
import { apiFetch } from "../../../lib/api";
import { getServiceLabel } from "../../../lib/serviceLabels";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Debounce hook - must be defined outside component to follow React rules of hooks
function useDebounce(value: string, delay: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

interface Project {
  id: string;
  lead_id: number | null;
  name: string;
  service_type: string | null;
  contract_months: number | null;
  type: string | null; // "FIXED" or "RETAINER"
}

interface Lead {
  id: number;
  business_name: string;
  phone_number: string;
  product_interest: string | null;
}

interface Contact {
  id: number;
  business_name: string;
  phone_number: string;
  purchased_product: string | null;
}

interface ReportSnapshot {
  id: string;
  title: string;
  report_type: string;
  target_type: string;
  target_id: string | null;
  project_id: string | null;
  service_type: string | null;
  month_number: number | null;
  public_url: string | null;
  open_count: number;
  max_duration_seconds: number;
  generated_document_id: string | null;
  created_at: string;
  metrics?: Record<string, any>;
}

interface MetricField {
  key: string;
  label: string;
  placeholder?: string;
  type?: string;
}

const REPORT_TYPES = [
  { value: "monthly", label: "Laporan bulanan" },
  { value: "completion", label: "Laporan selesai proyek" },
  { value: "internal", label: "Laporan internal" },
  { value: "lead_audit", label: "Audit lead" },
];

const TARGET_TYPES = [
  { value: "project", label: "Proyek", helper: "Untuk laporan kerja bulanan/selesai proyek. Auto-pull workspace, board, attachment." },
  { value: "lead", label: "Lead", helper: "Untuk audit pre-sales atau laporan prospek." },
  { value: "contact", label: "Klien/Kontak", helper: "Untuk dokumen/laporan akun klien tanpa project spesifik." },
  { value: "empty", label: "Tanpa target", helper: "Untuk catatan internal atau laporan umum." },
];

const SEO_CURRENT_FIELDS: MetricField[] = [
  { key: "website_url", label: "URL website", placeholder: "https://domain-klien.com" },
  { key: "gsc_clicks", label: "GSC clicks periode ini", type: "number" },
  { key: "gsc_impressions", label: "GSC impressions periode ini", type: "number" },
  { key: "gsc_ctr", label: "CTR periode ini", placeholder: "3,2%" },
  { key: "gsc_average_position", label: "Average position periode ini", placeholder: "12,4" },
  { key: "gbp_views", label: "Google Business views", type: "number" },
  { key: "gbp_calls", label: "Google Business calls", type: "number" },
  { key: "gbp_directions", label: "Direction requests", type: "number" },
  { key: "gbp_website_clicks", label: "Website clicks dari GBP", type: "number" },
];

const SEO_MONTHLY_FIELDS: MetricField[] = [
  { key: "website_url", label: "URL website", placeholder: "https://domain-klien.com" },
  // GSC Current Month
  { key: "gsc_clicks", label: "GSC Clicks (Bulan Ini)", type: "number" },
  { key: "gsc_impressions", label: "GSC Impressions (Bulan Ini)", type: "number" },
  { key: "gsc_ctr", label: "GSC CTR (Bulan Ini)", placeholder: "8.78%" },
  { key: "gsc_average_position", label: "GSC Avg Position (Bulan Ini)", placeholder: "13.85" },
  // GSC Previous Month (Comparison)
  { key: "gsc_clicks_previous", label: "GSC Clicks (Bulan Lalu)", type: "number" },
  { key: "gsc_impressions_previous", label: "GSC Impressions (Bulan Lalu)", type: "number" },
  { key: "gsc_ctr_previous", label: "GSC CTR (Bulan Lalu)", placeholder: "8.5%" },
  { key: "gsc_average_position_previous", label: "GSC Avg Position (Bulan Lalu)", placeholder: "15.0" },
  // Google Business Profile
  { key: "gbp_views", label: "GBP Views", type: "number" },
  { key: "gbp_searches", label: "GBP Searches (Direct+Indirect)", type: "number" },
  { key: "gbp_directions", label: "GBP Directions", type: "number" },
  { key: "gbp_calls", label: "GBP Calls", type: "number" },
  { key: "gbp_website_clicks", label: "GBP Website Clicks", type: "number" },
  // Top Queries & Pages
  { key: "top_queries", label: "Top 5 Queries (1 per baris)", type: "textarea", placeholder: "jasa pembangunan rumah\npembangunan rumah jogja\n..." },
  { key: "top_pages", label: "Top 5 Pages (1 per baris)", placeholder: "/layanan/pembangunan-rumah\n/layanan/desain-interior\n..." },
  // Notes
  { key: "gsc_comparison_notes", label: "Analisis & Catatan", type: "textarea", placeholder: "Clicks naik 9.3% karena 2 artikel baru masuk halaman 1. CTR sedikit turun karena impressions naik lebih cepat. Perlu optimasi meta title untuk improve CTR." },
  // Target
  { key: "gsc_clicks_target_next_month", label: "Target GSC Clicks (Bulan Depan)", type: "number" },
  { key: "gsc_impressions_target_next_month", label: "Target GSC Impressions (Bulan Depan)", type: "number" },
  { key: "gsc_ctr_target_next_month", label: "Target CTR (Bulan Depan)", placeholder: "9.0%" },
  { key: "gsc_average_position_target_next_month", label: "Target Avg Position (Bulan Depan)", placeholder: "12.0" },
  { key: "seo_next_month_target_notes", label: "Notes Target Bulan Depan", type: "textarea", placeholder: "Target realistis: publish 2 artikel baru, optimasi 3 meta title existing, update GBP posting rutin." },
];

const SEO_COMPLETION_FIELDS: MetricField[] = [
  ...SEO_CURRENT_FIELDS,
  { key: "gsc_clicks_baseline", label: "GSC clicks data awal proyek", type: "number" },
  { key: "gsc_impressions_baseline", label: "GSC impressions data awal proyek", type: "number" },
  { key: "gsc_ctr_baseline", label: "CTR data awal proyek", placeholder: "1,9%" },
  { key: "gsc_average_position_baseline", label: "Average position data awal proyek", placeholder: "28,5" },
  { key: "gsc_comparison_notes", label: "Notes komparasi awal vs akhir proyek", type: "textarea", placeholder: "Contoh: impressions naik tajam dari baseline, tetapi beberapa query transaksi masih butuh optimasi lanjutan." },
];

const SERVICE_COMPARISON_FIELDS: Record<string, MetricField[]> = {
  seo_gmaps: [
    { key: "gsc_clicks", label: "GSC clicks", type: "number" },
    { key: "gsc_impressions", label: "GSC impressions", type: "number" },
    { key: "gsc_ctr", label: "CTR", placeholder: "3,2%" },
    { key: "gsc_average_position", label: "Average position", placeholder: "12,4" },
  ],
  maintenance: [
    { key: "uptime", label: "Uptime", placeholder: "99.9%" },
    { key: "security_score", label: "Security/site health score", type: "number" },
    { key: "incidents", label: "Jumlah insiden", type: "number" },
    { key: "resolved_issues", label: "Issue terselesaikan", type: "number" },
  ],
  sosmed: [
    { key: "posts", label: "Konten publish", type: "number" },
    { key: "reach", label: "Reach", type: "number" },
    { key: "engagement", label: "Engagement", type: "number" },
    { key: "followers_delta", label: "Perubahan followers", placeholder: "+42" },
  ],
  web_dev: [
    { key: "pages_done_count", label: "Jumlah halaman selesai", type: "number" },
    { key: "features_done_count", label: "Jumlah fitur selesai", type: "number" },
    { key: "open_bugs", label: "Bug terbuka", type: "number" },
    { key: "qa_passed_count", label: "QA passed", type: "number" },
  ],
  web_dev_bulanan: [
    { key: "pages_done_count", label: "Jumlah update/halaman selesai", type: "number" },
    { key: "features_done_count", label: "Jumlah fitur/maintenance selesai", type: "number" },
    { key: "open_bugs", label: "Bug terbuka", type: "number" },
    { key: "qa_passed_count", label: "QA passed", type: "number" },
  ],
  branding: [
    { key: "deliverables_done_count", label: "Deliverables selesai", type: "number" },
    { key: "approved_assets_count", label: "Asset approved", type: "number" },
    { key: "revision_round", label: "Putaran revisi", type: "number" },
  ],
  general: [
    { key: "progress_score", label: "Progress score", type: "number" },
    { key: "completed_items", label: "Item selesai", type: "number" },
    { key: "open_issues", label: "Issue terbuka", type: "number" },
  ],
};

const SERVICE_FIELDS: Record<string, MetricField[]> = {
  seo_gmaps: SEO_MONTHLY_FIELDS,
  maintenance: [
    // Website Info
    { key: "website_url", label: "URL Website", placeholder: "https://domain-klien.com" },
    { key: "wp_version", label: "Versi WordPress", placeholder: "WordPress 6.5.5" },
    // Backup Section
    { key: "last_backup_at", label: "Tanggal Backup Terakhir", type: "date" },
    { key: "backup_status", label: "Status Backup", placeholder: "Berhasil / Gagal / Pending" },
    { key: "backup_link", label: "Link/File Backup", placeholder: "https://drive.google.com/..." },
    { key: "backup_size", label: "Ukuran Backup", placeholder: "1.2 GB" },
    // WordPress Updates
    { key: "core_updates", label: "Update WordPress Core", placeholder: "6.5.4 -> 6.5.5 (1 update)" },
    { key: "plugin_updates", label: "Update Plugin", placeholder: "Plugin A (1.2.3 -> 1.2.4), Plugin B (2.0.0 -> 2.0.1)" },
    { key: "theme_updates", label: "Update Theme", placeholder: "Tema aktif sudah terbaru / Theme X updated" },
    // Security & Health
    { key: "security_status", label: "Status Security/Site Health", placeholder: "Aman - Tidak ada critical issue" },
    { key: "security_issues", label: "Issue Keamanan (jika ada)", placeholder: "Tidak ada / wp-config.php exposed" },
    { key: "uptime", label: "Uptime", placeholder: "99.9%" },
    // Work Done
    { key: "work_done", label: "Pekerjaan yang Dilakukan", type: "textarea", placeholder: "1. Update plugin A ke versi terbaru\n2. Backup manual setelah update major\n3. Optimasi gambar di halaman layanan" },
    { key: "incidents", label: "Insiden/Downtime", placeholder: "Tidak ada / 1x downtime 15 menit (server overload)" },
    { key: "resolved_issues", label: "Issue yang Diselesaikan", placeholder: "1. Error 500 di halaman kontak\n2. Plugin conflict dengan PHP 8.2" },
    // Notes
    { key: "maintenance_notes", label: "Catatan & Rekomendasi", type: "textarea", placeholder: "Website berjalan normal. Rekomendasi: upgrade PHP ke 8.3 semester ini untuk performa lebih baik." },
  ],
  sosmed: [
    { key: "posts", label: "Konten publish", type: "number" },
    { key: "reach", label: "Reach", type: "number" },
    { key: "engagement", label: "Engagement/interactions", type: "number" },
    { key: "followers_delta", label: "Perubahan followers", placeholder: "+42" },
  ],
  web_dev: [
    { key: "website_url", label: "URL staging/live", placeholder: "https://..." },
    { key: "pages_done", label: "Halaman selesai", placeholder: "Home, Tentang, Layanan" },
    { key: "pages_done_count", label: "Jumlah halaman selesai", type: "number" },
    { key: "features_done", label: "Fitur selesai", placeholder: "Form WA, katalog, checkout" },
    { key: "features_done_count", label: "Jumlah fitur selesai", type: "number" },
    { key: "qa_status", label: "Status QA", placeholder: "Mobile OK, form OK" },
    { key: "qa_passed_count", label: "QA passed", type: "number" },
    { key: "open_bugs", label: "Bug terbuka", type: "number" },
    { key: "handover_link", label: "Link handover", placeholder: "Drive/Notion/Docs" },
  ],
  web_dev_bulanan: [
    { key: "website_url", label: "URL website", placeholder: "https://..." },
    { key: "pages_done", label: "Perbaikan/halaman selesai", placeholder: "Landing promo, update menu" },
    { key: "pages_done_count", label: "Jumlah update/halaman selesai", type: "number" },
    { key: "features_done", label: "Fitur/maintenance selesai", placeholder: "Form, CTA, tracking" },
    { key: "features_done_count", label: "Jumlah fitur/maintenance selesai", type: "number" },
    { key: "qa_status", label: "Status QA", placeholder: "Mobile OK, form OK" },
    { key: "qa_passed_count", label: "QA passed", type: "number" },
    { key: "open_bugs", label: "Bug terbuka", type: "number" },
    { key: "handover_link", label: "Link bukti/handover", placeholder: "Drive/Notion/Docs" },
  ],
  branding: [
    { key: "deliverables", label: "Deliverables", placeholder: "Logo, brand guide, template feed" },
    { key: "deliverables_done_count", label: "Deliverables selesai", type: "number" },
    { key: "revision_round", label: "Putaran revisi", placeholder: "Revisi 2 selesai" },
    { key: "approved_assets_count", label: "Asset approved", type: "number" },
    { key: "approval_status", label: "Status approval", placeholder: "Disetujui / menunggu review" },
    { key: "asset_link", label: "Link asset final", placeholder: "Drive/Figma/Canva" },
  ],
  general: [
    { key: "website_url", label: "URL terkait", placeholder: "Opsional" },
    { key: "highlights", label: "Highlight singkat", placeholder: "Tugas penting yang selesai" },
  ],
};

function reportComparisonFields(serviceType: string | null | undefined, reportType: string): MetricField[] {
  const serviceKey = serviceType || "general";
  const fields = SERVICE_COMPARISON_FIELDS[serviceKey] || SERVICE_COMPARISON_FIELDS.general;
  if (reportType === "completion") {
    return [
      ...fields.map(field => ({ ...field, key: `${field.key}_baseline`, label: `${field.label} data awal proyek` })),
      { key: `${serviceKey}_comparison_notes`, label: "Notes komparasi data awal vs akhir proyek", type: "textarea", placeholder: "Contoh: progress naik signifikan dari baseline, tetapi ada bagian yang perlu dipantau setelah handover." },
    ];
  }
  if (reportType === "monthly") {
    return [
      ...fields.map(field => ({ ...field, key: `${field.key}_previous`, label: `${field.label} bulan lalu` })),
      { key: `${serviceKey}_comparison_notes`, label: "Notes komparasi bulan ini vs bulan lalu", type: "textarea", placeholder: "Contoh: performa naik karena eksekusi bulan ini, tapi beberapa metric masih perlu perhatian." },
      ...fields.map(field => ({ ...field, key: `${field.key}_target_next_month`, label: `Target ${field.label} bulan depan` })),
      { key: `${serviceKey}_next_month_target_notes`, label: "Notes target bulan depan", type: "textarea", placeholder: "Contoh: target realistis setelah task prioritas bulan depan selesai." },
    ];
  }
  return [
    { key: `${serviceKey}_comparison_notes`, label: "Notes komparasi", type: "textarea", placeholder: "Opsional jika laporan ini punya pembanding manual." },
  ];
}

function uniqueMetricFields(fields: MetricField[]) {
  const seen = new Set<string>();
  return fields.filter(field => {
    if (seen.has(field.key)) return false;
    seen.add(field.key);
    return true;
  });
}

function getMetricFields(serviceType: string | null | undefined, reportType: string) {
  const serviceKey = serviceType || "general";
  const baseFields = serviceKey === "seo_gmaps" ? SEO_CURRENT_FIELDS : (SERVICE_FIELDS[serviceKey] || SERVICE_FIELDS.general);
  return uniqueMetricFields([...baseFields, ...reportComparisonFields(serviceKey, reportType)]);
}

function getMetricHelper(serviceType: string | null | undefined, reportType: string) {
  if (reportType === "completion") {
    return "Data akhir proyek dibandingkan dengan data pertama/baseline awal proyek";
  }
  if (reportType === "monthly") {
    return "Data bulan ini dibandingkan bulan lalu, plus target bulan depan";
  }
  return serviceType === "seo_gmaps" ? "Isi metric audit SEO periode ini" : "Isi metric periode ini; notes komparasi opsional";
}

function toNumberIfPossible(value: string) {
  const normalized = value.trim().replace(",", ".");
  if (!normalized) return "";
  const n = Number(normalized);
  return Number.isFinite(n) && /^-?\d+([.,]\d+)?$/.test(value.trim()) ? n : value;
}

function linesToArray(value: string) {
  return value.split("\n").map(line => line.trim()).filter(Boolean);
}

function formatDuration(seconds: number) {
  if (!seconds) return "0 detik";
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return minutes > 0 ? `${minutes}m ${rest}s` : `${rest}s`;
}

export default function ReportsContent() {
  const searchParams = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [reports, setReports] = useState<ReportSnapshot[]>([]);
  const [targetType, setTargetType] = useState(searchParams.get("target_type") || "project");
  const [targetId, setTargetId] = useState(searchParams.get("project_id") || searchParams.get("target_id") || "");
  const [reportType, setReportType] = useState(searchParams.get("report_type") || "monthly");
  const [monthNumber, setMonthNumber] = useState(Number(searchParams.get("month") || "1"));
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [metrics, setMetrics] = useState<Record<string, string>>({});
  const [executiveSummary, setExecutiveSummary] = useState("");
  const [highlights, setHighlights] = useState("");
  const [issues, setIssues] = useState("");
  const [nextSteps, setNextSteps] = useState("");
  const [runPagespeed, setRunPagespeed] = useState(true);
  const [publicEnabled, setPublicEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  // Search states for lazy-loaded dropdowns
  const [projectSearch, setProjectSearch] = useState("");
  const [leadSearch, setLeadSearch] = useState("");
  const [contactSearch, setContactSearch] = useState("");

  const selectedProject = useMemo(() => projects.find(p => p.id === targetId) || null, [projects, targetId]);
  const selectedLead = useMemo(() => leads.find(l => String(l.id) === targetId) || null, [leads, targetId]);
  const selectedContact = useMemo(() => contacts.find(c => String(c.id) === targetId) || null, [contacts, targetId]);
  const serviceType = selectedProject?.service_type || "general";
  const metricFields = useMemo(() => getMetricFields(serviceType, reportType), [serviceType, reportType]);
  const metricHelper = useMemo(() => getMetricHelper(serviceType, reportType), [serviceType, reportType]);

  const fetchReports = useCallback(async () => {
    const res = await apiFetch("/api/reports");
    if (res.ok) setReports(await res.json());
  }, []);

  const debouncedProjectSearch = useDebounce(projectSearch, 300);
  const debouncedLeadSearch = useDebounce(leadSearch, 300);
  const debouncedContactSearch = useDebounce(contactSearch, 300);

  // Lazy load projects with search
  const fetchProjects = useCallback(async (search: string) => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    const res = await apiFetch(`/api/projects?${params}`);
    if (res.ok) setProjects(await res.json());
  }, []);

  // Lazy load leads with search
  const fetchLeads = useCallback(async (search: string) => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    params.set("limit", "50");
    const res = await apiFetch(`/api/leads?${params}`);
    if (res.ok) setLeads(await res.json());
  }, []);

  // Lazy load contacts with search
  const fetchContacts = useCallback(async (search: string) => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    params.set("limit", "50");
    const res = await apiFetch(`/api/contacts?${params}`);
    if (res.ok) setContacts(await res.json());
  }, []);

  // Initial load with limited results
  useEffect(() => {
    async function load() {
      try {
        await Promise.all([
          fetchProjects(""),
          fetchLeads(""),
          fetchContacts(""),
        ]);
        await fetchReports();
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [fetchProjects, fetchLeads, fetchContacts, fetchReports]);

  // Refetch when search changes
  useEffect(() => {
    fetchProjects(debouncedProjectSearch);
  }, [debouncedProjectSearch, fetchProjects]);

  useEffect(() => {
    fetchLeads(debouncedLeadSearch);
  }, [debouncedLeadSearch, fetchLeads]);

  useEffect(() => {
    fetchContacts(debouncedContactSearch);
  }, [debouncedContactSearch, fetchContacts]);

  useEffect(() => {
    if (targetType === "project" && selectedProject?.contract_months && monthNumber > selectedProject.contract_months) {
      setMonthNumber(1);
    }
  }, [monthNumber, selectedProject, targetType]);

  function targetOptions() {
    if (targetType === "project") return projects.map(p => ({ value: p.id, label: `${p.name} (${getServiceLabel(p.service_type) || "Layanan"})` }));
    if (targetType === "lead") return leads.map(l => ({ value: String(l.id), label: `${l.business_name} (${l.product_interest || l.phone_number})` }));
    if (targetType === "contact") return contacts.map(c => ({ value: String(c.id), label: `${c.business_name} (${c.purchased_product || c.phone_number})` }));
    return [];
  }

  function updateMetric(key: string, value: string) {
    setMetrics(prev => ({ ...prev, [key]: value }));
  }

  function buildPayload() {
    const parsedMetrics: Record<string, string | number | string[]> = {};
    const allowedMetricKeys = new Set(metricFields.map(field => field.key));
    for (const [key, value] of Object.entries(metrics)) {
      if (!allowedMetricKeys.has(key)) continue;
      if (!value.trim()) continue;
      parsedMetrics[key] = toNumberIfPossible(value);
    }
    return {
      report_type: reportType,
      target_type: targetType,
      target_id: targetType === "empty" ? null : targetId || null,
      month_number: reportType === "monthly" && targetType === "project" ? monthNumber : null,
      period_start: periodStart || null,
      period_end: periodEnd || null,
      metrics: parsedMetrics,
      evidence: {},
      narrative: {
        executive_summary: executiveSummary,
        highlights: linesToArray(highlights),
        issues: linesToArray(issues),
        next_steps: linesToArray(nextSteps),
      },
      run_pagespeed: runPagespeed,
      public_enabled: publicEnabled,
    };
  }

  async function generateReport() {
    if (targetType !== "empty" && !targetId) {
      setToast({ message: "Pilih target laporan dulu.", type: "error" });
      return;
    }
    setGenerating(true);
    try {
      const res = await apiFetch("/api/reports/generate", { method: "POST", body: JSON.stringify(buildPayload()) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setToast({ message: data.detail || "Gagal membuat laporan", type: "error" });
        return;
      }
      setReports(prev => {
        const existingIds = new Set(prev.map(r => r.id));
        if (existingIds.has(data.id)) {
          // Update existing instead of adding duplicate
          return prev.map(r => r.id === data.id ? data : r);
        }
        return [data, ...prev];
      });
      setToast({ message: "Laporan dibuat. PDF masuk arsip dan link publik siap dikirim.", type: "success" });
      if (data.public_url) window.open(data.public_url, "_blank");
    } catch {
      setToast({ message: "Gagal membuat laporan", type: "error" });
    } finally {
      setGenerating(false);
    }
  }

  async function copyLink(url: string | null) {
    if (!url) return;
    await navigator.clipboard.writeText(url);
    setToast({ message: "Link laporan disalin", type: "success" });
  }

  const targetHelper = TARGET_TYPES.find(item => item.value === targetType)?.helper || "";

  return (
    <div className="mx-auto max-w-7xl space-y-5 p-4 sm:p-6">
      <Breadcrumb items={[{ label: "Dokumen & Laporan", href: "/documents" }, { label: "Laporan Klien" }]} showBack backHref="/documents" />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Laporan Klien</h1>
          <p className="mt-1 text-sm text-neutral-500">Buat laporan bulanan atau laporan selesai proyek dari Workspace, Board, bukti kerja, PageSpeed, dan metric manual/API.</p>
        </div>
        <div className="flex gap-2">
          <Link href="/documents/generator" className="inline-flex items-center gap-1.5 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-semibold text-neutral-700 hover:bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-200">
            <FileText size={15} /> Dokumen Resmi
          </Link>
          <Link href="/proposals" className="inline-flex items-center gap-1.5 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-semibold text-neutral-700 hover:bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-200">
            <ExternalLink size={15} /> Proposal
          </Link>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.05fr)_minmax(360px,.95fr)]">
        <section className="space-y-4 rounded-2xl border border-amber-100 bg-white p-4 shadow-sm dark:border-amber-900/40 dark:bg-neutral-900">
          <div className="grid gap-3 md:grid-cols-2">
            <label>
              <span className="mb-1 block text-xs font-semibold text-neutral-500">Flow laporan</span>
              <select value={reportType} onChange={e => setReportType(e.target.value)} className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800">
                {REPORT_TYPES.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label>
              <span className="mb-1 block text-xs font-semibold text-neutral-500">Target</span>
              <select value={targetType} onChange={e => { setTargetType(e.target.value); setTargetId(""); }} className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800">
                {TARGET_TYPES.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
            </label>
          </div>
          <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950/20 dark:text-amber-200">{targetHelper}</p>

          {targetType !== "empty" && (
            <div className="space-y-2">
              <label className="block">
                <span className="mb-1 block text-xs font-semibold text-neutral-500">
                  Pilih {targetType === "project" ? "Proyek" : targetType === "lead" ? "Lead" : "Klien"}
                </span>
                {/* Searchable Combobox */}
                <div className="relative">
                  <input
                    type="text"
                    placeholder={`Ketik nama ${targetType === "project" ? "proyek" : targetType === "lead" ? "lead" : "klien"} untuk mencari...`}
                    value={targetType === "project" ? projectSearch : targetType === "lead" ? leadSearch : contactSearch}
                    onChange={e => {
                      if (targetType === "project") setProjectSearch(e.target.value);
                      else if (targetType === "lead") setLeadSearch(e.target.value);
                      else setContactSearch(e.target.value);
                    }}
                    className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5 text-sm dark:border-neutral-700 dark:bg-neutral-800"
                  />
                  {/* Dropdown Results */}
                  {targetOptions().length > 0 && (
                    <div className="absolute z-10 mt-1 w-full rounded-xl border border-neutral-200 bg-white shadow-lg dark:border-neutral-700 dark:bg-neutral-900 max-h-60 overflow-y-auto">
                      {targetOptions().map(item => (
                        <button
                          key={item.value}
                          type="button"
                          onClick={() => {
                            setTargetId(item.value);
                            // Clear search after selection
                            if (targetType === "project") setProjectSearch("");
                            else if (targetType === "lead") setLeadSearch("");
                            else setContactSearch("");
                          }}
                          className={`w-full text-left px-3 py-2.5 text-sm hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors ${
                            targetId === item.value ? "bg-amber-50 dark:bg-amber-900/20 border-l-2 border-amber-500" : ""
                          }`}
                        >
                          <span className="font-medium text-neutral-800 dark:text-neutral-100">{item.label}</span>
                          {targetId === item.value && (
                            <span className="ml-2 text-xs text-amber-600">✓ Dipilih</span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </label>
              {/* Selected Project Info */}
              {selectedProject && (
                <div className="rounded-lg border border-green-200 bg-green-50 dark:bg-green-900/20 dark:border-green-800 p-3">
                  <p className="text-sm font-semibold text-green-800 dark:text-green-200">
                    ✓ {selectedProject.name}
                  </p>
                  <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">
                    {getServiceLabel(selectedProject.service_type) || "Layanan"} ·
                    {selectedProject.type === "RETAINER" ? "🔄 Retainer" : "📋 Fixed"}
                    {selectedProject.contract_months && ` · ${selectedProject.contract_months} bulan`}
                  </p>
                </div>
              )}
              {!selectedProject && targetOptions().length === 0 && (
                <p className="text-xs text-neutral-400">Tidak ada hasil. Coba kata kunci lain.</p>
              )}
            </div>
          )}

          <div className="grid gap-3 md:grid-cols-3">
            {targetType === "project" && reportType === "monthly" && (
              <label>
                <span className="mb-1 block text-xs font-semibold text-neutral-500">Bulan ke</span>
                <select value={monthNumber} onChange={e => setMonthNumber(Number(e.target.value))} className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800">
                  {Array.from({ length: selectedProject?.contract_months || 12 }, (_, i) => i + 1).map(month => <option key={month} value={month}>Bulan {month}</option>)}
                </select>
              </label>
            )}
            <label>
              <span className="mb-1 block text-xs font-semibold text-neutral-500">Dari tanggal</span>
              <input type="date" value={periodStart} onChange={e => setPeriodStart(e.target.value)} className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800" />
            </label>
            <label>
              <span className="mb-1 block text-xs font-semibold text-neutral-500">Sampai tanggal</span>
              <input type="date" value={periodEnd} onChange={e => setPeriodEnd(e.target.value)} className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800" />
            </label>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between gap-2">
              <h2 className="text-sm font-bold text-neutral-900 dark:text-neutral-100">Metric {getServiceLabel(serviceType) || "Layanan"}</h2>
              <span className="text-right text-xs text-neutral-400">{metricHelper}</span>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {metricFields.map(field => (
                <label key={field.key} className={field.type === "textarea" ? "md:col-span-2" : undefined}>
                  <span className="mb-1 block text-xs font-semibold text-neutral-500">{field.label}</span>
                  {field.type === "textarea" ? (
                    <textarea
                      value={metrics[field.key] || ""}
                      onChange={e => updateMetric(field.key, e.target.value)}
                      placeholder={field.placeholder}
                      rows={3}
                      className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800"
                    />
                  ) : (
                    <input
                      type={field.type || "text"}
                      value={metrics[field.key] || ""}
                      onChange={e => updateMetric(field.key, e.target.value)}
                      placeholder={field.placeholder}
                      className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800"
                    />
                  )}
                </label>
              ))}
            </div>
          </div>

          {/* Retainer Before/After Section */}
          {selectedProject?.type === "RETAINER" && (
            <div className="rounded-xl border-2 border-amber-200 bg-amber-50/30 dark:bg-amber-950/20 p-4">
              <h3 className="text-sm font-bold text-amber-800 dark:text-amber-200 mb-3 flex items-center gap-2">
                📊 Before/After Retainer
                <span className="text-xs font-normal text-amber-600 dark:text-amber-400">(Periode sebelumnya vs sekarang)</span>
              </h3>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2">
                  <label>
                    <span className="mb-1 block text-xs font-semibold text-amber-700 dark:text-amber-300">📌 Before (baseline retainer)</span>
                    <textarea
                      value={metrics["retainer_before"] || ""}
                      onChange={e => updateMetric("retainer_before", e.target.value)}
                      placeholder="Kondisi awal retainer: URL, metric baseline, masalah yang mau diselesaikan..."
                      rows={3}
                      className="w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm dark:border-amber-800 dark:bg-neutral-900"
                    />
                  </label>
                </div>
                <div className="space-y-2">
                  <label>
                    <span className="mb-1 block text-xs font-semibold text-green-700 dark:text-green-300">✅ After (hasil periode ini)</span>
                    <textarea
                      value={metrics["retainer_after"] || ""}
                      onChange={e => updateMetric("retainer_after", e.target.value)}
                      placeholder="Hasil setelah periode retainer ini: apa yang berubah, improvement, dll..."
                      rows={3}
                      className="w-full rounded-lg border border-green-200 bg-white px-3 py-2 text-sm dark:border-green-800 dark:bg-neutral-900"
                    />
                  </label>
                </div>
              </div>
              <div className="mt-3">
                <label>
                  <span className="mb-1 block text-xs font-semibold text-neutral-500">Catatan before/after retainer</span>
                  <textarea
                    value={metrics["retainer_notes"] || ""}
                    onChange={e => updateMetric("retainer_notes", e.target.value)}
                    placeholder="Analisis: apa yang berhasil, apa yang perlu diperbaiki, next step..."
                    rows={2}
                    className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
                  />
                </label>
              </div>
            </div>
          )}

          <div className="grid gap-3 md:grid-cols-2">
            <label className="md:col-span-2">
              <span className="mb-1 block text-xs font-semibold text-neutral-500">Ringkasan eksekutif</span>
              <textarea value={executiveSummary} onChange={e => setExecutiveSummary(e.target.value)} rows={3} placeholder="Kosongkan kalau mau sistem buat ringkasan dari progress workspace." className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800" />
            </label>
            <label>
              <span className="mb-1 block text-xs font-semibold text-neutral-500">Highlight (1 baris per poin)</span>
              <textarea value={highlights} onChange={e => setHighlights(e.target.value)} rows={4} className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800" />
            </label>
            <label>
              <span className="mb-1 block text-xs font-semibold text-neutral-500">Issue/catatan (1 baris per poin)</span>
              <textarea value={issues} onChange={e => setIssues(e.target.value)} rows={4} className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800" />
            </label>
            <label className="md:col-span-2">
              <span className="mb-1 block text-xs font-semibold text-neutral-500">Rencana berikutnya (1 baris per poin)</span>
              <textarea value={nextSteps} onChange={e => setNextSteps(e.target.value)} rows={3} className="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-800" />
            </label>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-100 pt-3 dark:border-neutral-800">
            <div className="flex flex-wrap gap-4">
              <label className="inline-flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-300">
                <input type="checkbox" checked={runPagespeed} onChange={e => setRunPagespeed(e.target.checked)} className="h-4 w-4 accent-amber-500" />
                Auto PageSpeed
              </label>
              <label className="inline-flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-300">
                <input type="checkbox" checked={publicEnabled} onChange={e => setPublicEnabled(e.target.checked)} className="h-4 w-4 accent-amber-500" />
                Buat link publik tracked
              </label>
            </div>
            <button onClick={generateReport} disabled={generating || (targetType !== "empty" && !targetId)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-amber-500 px-4 py-2 text-sm font-bold text-white hover:bg-amber-600 disabled:opacity-50">
              {generating ? <RefreshCw size={15} className="animate-spin" /> : <Plus size={15} />}
              {generating ? "Membuat..." : "Generate Laporan"}
            </button>
          </div>
        </section>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-amber-600" />
              <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-100">Preview data otomatis</h2>
            </div>
            <div className="mt-3 grid gap-2 text-sm text-neutral-600 dark:text-neutral-300">
              <div className="flex justify-between gap-3"><span>Target</span><b className="text-right">{selectedProject?.name || selectedLead?.business_name || selectedContact?.business_name || "Tanpa target"}</b></div>
              <div className="flex justify-between gap-3"><span>Layanan</span><b>{getServiceLabel(serviceType) || "Umum"}</b></div>
              <div className="flex justify-between gap-3"><span>Workspace</span><b>{targetType === "project" ? "Dipakai otomatis" : "Tidak ada project"}</b></div>
              <div className="flex justify-between gap-3"><span>Board</span><b>{targetType === "project" ? "Dipakai otomatis" : "Tidak ada project"}</b></div>
              <div className="flex justify-between gap-3"><span>Output</span><b>PDF + arsip{publicEnabled ? " + link tracked" : ""}</b></div>
            </div>
          </div>

          <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-100">Laporan terbaru</h2>
              <button onClick={fetchReports} className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 dark:hover:bg-neutral-800"><RefreshCw size={14} /></button>
            </div>
            {loading ? (
              <p className="text-sm text-neutral-400">Memuat...</p>
            ) : reports.length === 0 ? (
              <p className="rounded-xl bg-neutral-50 p-4 text-sm text-neutral-500 dark:bg-neutral-800/60">Belum ada laporan. Generate pertama akan masuk ke sini dan otomatis tersimpan di Arsip.</p>
            ) : (
              <div className="space-y-2">
                {reports.slice(0, 12).map(report => (
                  <div key={report.id} className="rounded-xl border border-neutral-100 bg-neutral-50 p-3 dark:border-neutral-800 dark:bg-neutral-800/50">
                    <p className="line-clamp-2 text-sm font-bold text-neutral-900 dark:text-neutral-100">{report.title}</p>
                    <p className="mt-1 text-xs text-neutral-500">
                      {getServiceLabel(report.service_type) || report.service_type || "Umum"} · {new Date(report.created_at).toLocaleDateString("id-ID")} · dibuka {report.open_count || 0}x · {formatDuration(report.max_duration_seconds || 0)}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {report.public_url && (
                        <>
                          <a href={report.public_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded-lg bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800 hover:bg-amber-200 dark:bg-amber-950/30 dark:text-amber-200">
                            <ExternalLink size={12} /> Link
                          </a>
                          <button onClick={() => copyLink(report.public_url)} className="inline-flex items-center gap-1 rounded-lg bg-neutral-100 px-2 py-1 text-xs font-semibold text-neutral-700 hover:bg-neutral-200 dark:bg-neutral-700 dark:text-neutral-100">
                            <Copy size={12} /> Copy
                          </button>
                        </>
                      )}
                      {report.generated_document_id && (
                        <a href={`${API_BASE}/api/documents/${report.generated_document_id}/download`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 rounded-lg bg-blue-100 px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-200 dark:bg-blue-950/30 dark:text-blue-200">
                          <Download size={12} /> PDF
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
