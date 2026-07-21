"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { BarChart3, Check, Copy, Download, ExternalLink, FileText, Plus, RefreshCw, Search, Trash2, Upload, X } from "lucide-react";
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

// Minimal detection fields only — prev/baseline/target digabung ke 1 notes.
// Comparison tables opsional via comparisonGroups UI di bawah form.

const SEO_FIELDS: MetricField[] = [
  { key: "website_url", label: "URL website", placeholder: "https://domain-klien.com" },
  { key: "gsc_clicks", label: "GSC clicks", type: "number" },
  { key: "gsc_impressions", label: "GSC impressions", type: "number" },
  { key: "gsc_ctr", label: "CTR", placeholder: "3,2%" },
  { key: "gsc_average_position", label: "Avg position", placeholder: "12,4" },
  { key: "gbp_views", label: "GBP views", type: "number" },
  { key: "gbp_calls", label: "GBP calls", type: "number" },
  { key: "gsc_comparison_notes", label: "Analisis & catatan", type: "textarea", placeholder: "Clicks naik karena 2 artikel baru. Target bulan depan: optimasi meta title." },
];

const SERVICE_FIELDS: Record<string, MetricField[]> = {
  seo_gmaps: SEO_FIELDS,
  maintenance: [
    { key: "website_url", label: "URL website", placeholder: "https://domain-klien.com" },
    { key: "last_backup_at", label: "Backup terakhir", type: "date" },
    { key: "backup_status", label: "Status backup", placeholder: "Berhasil / Gagal" },
    { key: "uptime", label: "Uptime", placeholder: "99.9%" },
    { key: "work_done", label: "Pekerjaan dilakukan", type: "textarea", placeholder: "Update plugin, optimasi, fix bug…" },
    { key: "incidents", label: "Insiden/downtime", placeholder: "Tidak ada / 1x 15 menit" },
    { key: "maintenance_notes", label: "Catatan & rekomendasi", type: "textarea", placeholder: "Website normal. Rekomendasi: upgrade PHP." },
  ],
  sosmed: [
    { key: "posts", label: "Konten publish", type: "number" },
    { key: "reach", label: "Reach", type: "number" },
    { key: "engagement", label: "Engagement", type: "number" },
    { key: "followers_delta", label: "Δ followers", placeholder: "+42" },
    { key: "sosmed_notes", label: "Catatan", type: "textarea", placeholder: "Highlight konten / insight periode ini" },
  ],
  web_dev: [
    { key: "pages_done_count", label: "Halaman selesai", type: "number" },
    { key: "features_done_count", label: "Fitur selesai", type: "number" },
    { key: "open_bugs", label: "Bug terbuka", type: "number" },
    { key: "qa_status", label: "Status QA", placeholder: "Mobile OK, form OK" },
    { key: "handover_link", label: "Link handover", placeholder: "Drive/Notion" },
  ],
  web_dev_bulanan: [
    { key: "pages_done_count", label: "Update/halaman selesai", type: "number" },
    { key: "features_done_count", label: "Fitur/maintenance selesai", type: "number" },
    { key: "open_bugs", label: "Bug terbuka", type: "number" },
    { key: "qa_status", label: "Status QA", placeholder: "Mobile OK" },
    { key: "handover_link", label: "Link bukti", placeholder: "Drive/Notion" },
  ],
  branding: [
    { key: "deliverables_done_count", label: "Deliverables selesai", type: "number" },
    { key: "approved_assets_count", label: "Asset approved", type: "number" },
    { key: "revision_round", label: "Putaran revisi", type: "number" },
    { key: "asset_link", label: "Link asset final", placeholder: "Drive/Figma/Canva" },
  ],
  general: [
    { key: "progress_score", label: "Progress score", type: "number" },
    { key: "highlights", label: "Highlight singkat", type: "textarea", placeholder: "Tugas penting yang selesai" },
  ],
};

function uniqueMetricFields(fields: MetricField[]) {
  const seen = new Set<string>();
  return fields.filter(field => {
    if (seen.has(field.key)) return false;
    seen.add(field.key);
    return true;
  });
}

function getMetricFields(serviceType: string | null | undefined, _reportType: string) {
  const serviceKey = serviceType || "general";
  return uniqueMetricFields(SERVICE_FIELDS[serviceKey] || SERVICE_FIELDS.general);
}

function getMetricHelper(serviceType: string | null | undefined, reportType: string) {
  if (reportType === "completion") {
    return "Field deteksi minimal — detail komparasi baseline bisa lewat tabel comparison opsional di bawah";
  }
  if (reportType === "monthly") {
    return "Field deteksi minimal — notes untuk prev/target; tabel comparison opsional jika butuh angka lengkap";
  }
  return serviceType === "seo_gmaps" ? "Isi metric SEO periode ini (field deteksi minimal)" : "Isi metric periode ini (field deteksi minimal)";
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
  const [pickerOpen, setPickerOpen] = useState(false);
  // Comparison groups (arbitrary user-supplied tables)
  const [comparisonGroups, setComparisonGroups] = useState<{ title: string; reference_label: string; current_label: string; notes: string; rows: { label: string; previous: string; current: string }[] }[]>([]);
  // Manual evidence (uploaded screenshots + URL links)
  const [uploadedEvidence, setUploadedEvidence] = useState<{ label: string; url: string; file_name: string; file_type: string }[]>([]);
  const [uploading, setUploading] = useState(false);

  const selectedProject = useMemo(() => projects.find(p => p.id === targetId) || null, [projects, targetId]);
  const selectedLead = useMemo(() => leads.find(l => String(l.id) === targetId) || null, [leads, targetId]);
  const selectedContact = useMemo(() => contacts.find(c => String(c.id) === targetId) || null, [contacts, targetId]);
  const selectedTarget = useMemo(() => targetOptions().find(item => item.value === targetId) || null, [targetType, targetId, projects, leads, contacts]);
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
    const parsedMetrics: Record<string, string | number | string[] | any[]> = {};
    const allowedMetricKeys = new Set(metricFields.map(field => field.key));
    for (const [key, value] of Object.entries(metrics)) {
      if (!allowedMetricKeys.has(key)) continue;
      if (!value.trim()) continue;
      parsedMetrics[key] = toNumberIfPossible(value);
    }
    const groupsPayload = comparisonGroups
      .filter(g => g.rows.some(r => r.label.trim() || r.previous.trim() || r.current.trim()))
      .map(g => ({
        title: g.title.trim() || "Komparasi",
        reference_label: g.reference_label.trim() || "Pembanding",
        current_label: g.current_label.trim() || "Sekarang",
        notes: g.notes.trim() || undefined,
        rows: g.rows
          .filter(r => r.label.trim() || r.previous.trim() || r.current.trim())
          .map(r => ({
            label: r.label.trim(),
            previous: toNumberIfPossible(r.previous),
            current: toNumberIfPossible(r.current),
          })),
      }));
    if (groupsPayload.length > 0) {
      parsedMetrics["comparison_groups"] = groupsPayload;
    }
    const evidenceItems = uploadedEvidence
      .filter(e => e.url.trim())
      .map(e => ({
        label: e.label.trim() || e.file_name || "Bukti",
        url: e.url.trim(),
        file_name: e.file_name || undefined,
        file_type: e.file_type || undefined,
        source: "manual",
      }));
    return {
      report_type: reportType,
      target_type: targetType,
      target_id: targetType === "empty" ? null : targetId || null,
      month_number: reportType === "monthly" && targetType === "project" ? monthNumber : null,
      period_start: periodStart || null,
      period_end: periodEnd || null,
      metrics: parsedMetrics,
      evidence: evidenceItems.length > 0 ? { items: evidenceItems } : {},
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

  // Comparison group helpers
  function addComparisonGroup() {
    setComparisonGroups(prev => [...prev, { title: "", reference_label: "Bulan lalu", current_label: "Bulan ini", notes: "", rows: [{ label: "", previous: "", current: "" }] }]);
  }
  function updateGroup(index: number, patch: Partial<{ title: string; reference_label: string; current_label: string; notes: string }>) {
    setComparisonGroups(prev => prev.map((g, i) => i === index ? { ...g, ...patch } : g));
  }
  function removeGroup(index: number) {
    setComparisonGroups(prev => prev.filter((_, i) => i !== index));
  }
  function addGroupRow(index: number) {
    setComparisonGroups(prev => prev.map((g, i) => i === index ? { ...g, rows: [...g.rows, { label: "", previous: "", current: "" }] } : g));
  }
  function updateGroupRow(groupIndex: number, rowIndex: number, patch: Partial<{ label: string; previous: string; current: string }>) {
    setComparisonGroups(prev => prev.map((g, gi) => gi === groupIndex ? { ...g, rows: g.rows.map((r, ri) => ri === rowIndex ? { ...r, ...patch } : r) } : g));
  }
  function removeGroupRow(groupIndex: number, rowIndex: number) {
    setComparisonGroups(prev => prev.map((g, gi) => gi === groupIndex ? { ...g, rows: g.rows.filter((_, ri) => ri !== rowIndex) } : g));
  }

  // Evidence upload
  async function uploadEvidence(file: File, label: string) {
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_BASE}/api/reports/attachments`, { method: "POST", body: form, credentials: "include" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Gagal upload");
      }
      const data = await res.json();
      setUploadedEvidence(prev => [...prev, { label: label || file.name, url: data.file_url, file_name: data.file_name, file_type: data.file_type }]);
      setToast({ message: "Screenshot terunggah", type: "success" });
    } catch (e: any) {
      setToast({ message: e.message || "Gagal upload", type: "error" });
    } finally {
      setUploading(false);
    }
  }
  function addLinkEvidence(label: string, url: string) {
    if (!url.trim()) return;
    setUploadedEvidence(prev => [...prev, { label: label || url, url: url.trim(), file_name: "", file_type: "" }]);
  }
  function removeEvidence(index: number) {
    setUploadedEvidence(prev => prev.filter((_, i) => i !== index));
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
              <span className="mb-1 block text-xs font-semibold text-neutral-500">
                {selectedTarget ? "Target dipilih" : `Pilih ${targetType === "project" ? "Proyek" : targetType === "lead" ? "Lead" : "Klien"}`}
              </span>
              {selectedTarget ? (
                <div className="flex items-center justify-between gap-3 rounded-lg border border-green-200 bg-green-50 dark:bg-green-900/20 dark:border-green-800 p-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-green-800 dark:text-green-200">
                      ✓ {selectedTarget.label}
                    </p>
                    {selectedProject && (
                      <p className="mt-0.5 text-xs text-green-600 dark:text-green-400">
                        {getServiceLabel(selectedProject.service_type) || "Layanan"} ·
                        {selectedProject.type === "RETAINER" ? "🔄 Retainer" : "📋 Fixed"}
                        {selectedProject.contract_months && ` · ${selectedProject.contract_months} bulan`}
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setPickerOpen(true)}
                    className="shrink-0 rounded-lg bg-white px-2.5 py-1.5 text-xs font-semibold text-green-700 hover:bg-green-100 dark:bg-green-900/40 dark:text-green-200 dark:hover:bg-green-900/60"
                  >
                    Ganti
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setPickerOpen(true)}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-neutral-300 bg-neutral-50 px-3 py-2.5 text-sm font-semibold text-neutral-500 hover:border-amber-400 hover:bg-amber-50 hover:text-amber-700 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-400 dark:hover:border-amber-600 dark:hover:bg-amber-950/20"
                >
                  <Search size={15} /> Cari & pilih {targetType === "project" ? "proyek" : targetType === "lead" ? "lead" : "klien"}
                </button>
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

          {/* Comparison Groups — arbitrary user tables */}
          <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-4 dark:border-blue-900/40 dark:bg-blue-950/10">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-neutral-900 dark:text-neutral-100">📊 Tabel Komparasi</h3>
              <button type="button" onClick={addComparisonGroup} className="inline-flex items-center gap-1 rounded-lg bg-blue-500 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-600">
                <Plus size={14} /> Tambah Tabel
              </button>
            </div>
            <p className="mb-3 text-xs text-neutral-500">Buat tabel komparasi bebas (mis. "Metriks Keseluruhan" bulan-ini vs bulan-lalu, atau "Kemajuan Proyek" benchmark vs sekarang). Label & baris bebas.</p>
            {comparisonGroups.length === 0 ? (
              <p className="rounded-lg bg-white px-3 py-3 text-xs text-neutral-400 dark:bg-neutral-900">Belum ada tabel. Klik "Tambah Tabel".</p>
            ) : (
              <div className="space-y-3">
                {comparisonGroups.map((group, gi) => (
                  <div key={gi} className="rounded-lg border border-neutral-200 bg-white p-3 dark:border-neutral-700 dark:bg-neutral-900">
                    <div className="grid gap-2 md:grid-cols-4">
                      <input value={group.title} onChange={e => updateGroup(gi, { title: e.target.value })} placeholder="Judul tabel" className="rounded-lg border border-neutral-200 px-2 py-1.5 text-xs dark:border-neutral-700 dark:bg-neutral-800 md:col-span-2" />
                      <input value={group.reference_label} onChange={e => updateGroup(gi, { reference_label: e.target.value })} placeholder="Label pembanding (mis. Mei 2026)" className="rounded-lg border border-neutral-200 px-2 py-1.5 text-xs dark:border-neutral-700 dark:bg-neutral-800" />
                      <input value={group.current_label} onChange={e => updateGroup(gi, { current_label: e.target.value })} placeholder="Label sekarang (mis. Juni 2026)" className="rounded-lg border border-neutral-200 px-2 py-1.5 text-xs dark:border-neutral-700 dark:bg-neutral-800" />
                    </div>
                    <div className="mt-2 space-y-2">
                      {group.rows.map((row, ri) => (
                        <div key={ri} className="grid grid-cols-[1fr_1fr_1fr_auto] gap-2">
                          <input value={row.label} onChange={e => updateGroupRow(gi, ri, { label: e.target.value })} placeholder="Metric (mis. Total Klik)" className="rounded-lg border border-neutral-200 px-2 py-1.5 text-xs dark:border-neutral-700 dark:bg-neutral-800" />
                          <input value={row.previous} onChange={e => updateGroupRow(gi, ri, { previous: e.target.value })} placeholder="Sebelum" inputMode="decimal" className="rounded-lg border border-neutral-200 px-2 py-1.5 text-xs dark:border-neutral-700 dark:bg-neutral-800" />
                          <input value={row.current} onChange={e => updateGroupRow(gi, ri, { current: e.target.value })} placeholder="Sekarang" inputMode="decimal" className="rounded-lg border border-neutral-200 px-2 py-1.5 text-xs dark:border-neutral-700 dark:bg-neutral-800" />
                          <button type="button" onClick={() => removeGroupRow(gi, ri)} className="rounded-lg p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"><Trash2 size={14} /></button>
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 flex items-center justify-between gap-2">
                      <button type="button" onClick={() => addGroupRow(gi)} className="inline-flex items-center gap-1 rounded-lg bg-neutral-100 px-2 py-1 text-xs font-semibold text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-300"><Plus size={12} /> Baris</button>
                      <button type="button" onClick={() => removeGroup(gi)} className="text-xs text-red-500 hover:underline">Hapus tabel</button>
                    </div>
                    <input value={group.notes} onChange={e => updateGroup(gi, { notes: e.target.value })} placeholder="Catatan tabel (opsional)" className="mt-2 w-full rounded-lg border border-neutral-200 px-2 py-1.5 text-xs dark:border-neutral-700 dark:bg-neutral-800" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Evidence upload — screenshots + links */}
          <div className="rounded-xl border border-green-200 bg-green-50/30 p-4 dark:border-green-900/40 dark:bg-green-950/10">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-neutral-900 dark:text-neutral-100">📸 Bukti Pengerjaan (Screenshot)</h3>
              <label className={`inline-flex cursor-pointer items-center gap-1 rounded-lg bg-green-500 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-green-600 ${uploading ? "opacity-50 pointer-events-none" : ""}`}>
                <Upload size={14} /> {uploading ? "Mengunggah..." : "Upload Screenshot"}
                <input type="file" accept="image/png,image/jpeg,image/webp,application/pdf" className="hidden" onChange={e => {
                  const f = e.target.files?.[0];
                  if (f) uploadEvidence(f, f.name);
                  e.target.value = "";
                }} />
              </label>
            </div>
            <p className="mb-3 text-xs text-neutral-500">Upload screenshot per aktivitas (BACKUP BULANAN, ARTIKEL, grafik GSC). Akan tampil inline di laporan publik + PDF.</p>
            {uploadedEvidence.length > 0 && (
              <div className="mb-3 grid gap-2">
                {uploadedEvidence.map((ev, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs dark:border-neutral-700 dark:bg-neutral-900">
                    <span className="truncate font-medium text-neutral-800 dark:text-neutral-100">{ev.label} {ev.file_type.startsWith("image/") && <span className="text-green-600">[gambar]</span>}</span>
                    <button type="button" onClick={() => removeEvidence(i)} className="text-red-400 hover:text-red-600"><Trash2 size={14} /></button>
                  </div>
                ))}
              </div>
            )}
            <div className="grid grid-cols-[1fr_1fr_auto] gap-2">
              <input id="ev-link-label" placeholder="Label (mis. BACKUP BULANAN)" className="rounded-lg border border-neutral-200 px-2 py-1.5 text-xs dark:border-neutral-700 dark:bg-neutral-800" />
              <input id="ev-link-url" placeholder="URL bukti (opsional, kalau bukan upload)" className="rounded-lg border border-neutral-200 px-2 py-1.5 text-xs dark:border-neutral-700 dark:bg-neutral-800" />
              <button type="button" onClick={() => {
                const l = (document.getElementById("ev-link-label") as HTMLInputElement)?.value || "";
                const u = (document.getElementById("ev-link-url") as HTMLInputElement)?.value || "";
                if (u) { addLinkEvidence(l, u); (document.getElementById("ev-link-label") as HTMLInputElement).value = ""; (document.getElementById("ev-link-url") as HTMLInputElement).value = ""; }
              }} className="rounded-lg bg-neutral-100 px-3 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-300">+ Link</button>
            </div>
          </div>

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

      {pickerOpen && targetType !== "empty" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setPickerOpen(false)} />
          <div className="relative bg-[var(--bg-surface)] rounded-2xl shadow-2xl border border-[var(--border-default)] w-full max-w-lg p-5 space-y-3 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-50">
                Pilih {targetType === "project" ? "Proyek" : targetType === "lead" ? "Lead" : "Klien"}
              </h3>
              <button onClick={() => setPickerOpen(false)} className="p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200">
                <X size={18} />
              </button>
            </div>
            <div className="relative">
              <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
              <input
                type="text"
                autoFocus
                placeholder={`Cari nama ${targetType === "project" ? "proyek" : targetType === "lead" ? "lead" : "klien"}...`}
                value={targetType === "project" ? projectSearch : targetType === "lead" ? leadSearch : contactSearch}
                onChange={e => {
                  if (targetType === "project") setProjectSearch(e.target.value);
                  else if (targetType === "lead") setLeadSearch(e.target.value);
                  else setContactSearch(e.target.value);
                }}
                className="w-full rounded-xl border border-neutral-200 bg-white pl-9 pr-3 py-2.5 text-sm dark:border-neutral-700 dark:bg-neutral-800"
              />
            </div>
            <div className="-mr-1 flex-1 overflow-y-auto pr-1">
              {targetOptions().length === 0 ? (
                <p className="px-2 py-6 text-center text-sm text-neutral-400">Tidak ada hasil. Coba kata kunci lain.</p>
              ) : (
                <div className="space-y-1">
                  {targetOptions().map(item => {
                    const isSelected = targetId === item.value;
                    return (
                      <button
                        key={item.value}
                        type="button"
                        onClick={() => {
                          setTargetId(item.value);
                          if (targetType === "project") setProjectSearch("");
                          else if (targetType === "lead") setLeadSearch("");
                          else setContactSearch("");
                          setPickerOpen(false);
                        }}
                        className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                          isSelected
                            ? "bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700"
                            : "hover:bg-neutral-50 dark:hover:bg-neutral-800 border border-transparent"
                        }`}
                      >
                        <span className="font-medium text-neutral-800 dark:text-neutral-100">{item.label}</span>
                        {isSelected && <Check size={16} className="text-amber-600 dark:text-amber-400" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
