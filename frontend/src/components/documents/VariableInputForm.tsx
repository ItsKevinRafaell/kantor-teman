"use client";
import { formatRupiah } from "../../utils/formatter";
import { useState, useEffect, useRef } from "react";
import { Search, Plus, Trash2, X, BookOpen, Save } from "lucide-react";

const FIELD_LABELS: Record<string, string> = {
  klien: "Nama Klien",
  layanan: "Layanan",
  items_rows: "Rincian Layanan",
  scope: "Lingkup Pekerjaan",
  terms: "Syarat dan Ketentuan",
  payment_info: "Informasi Pembayaran",
  payment_method: "Metode Pembayaran",
  nilai_kontrak: "Nilai Kontrak",
  tanggal_mulai: "Tanggal Mulai",
  tanggal_akhir: "Tanggal Selesai",
  // Service-specific contract variables
  tech_spec: "Spesifikasi Teknis",
  deliverables: "Lingkup Deliverables",
  revision_limit: "Batas Revisi",
  milestones: "Milestone & Serah Terima",
  domain_hosting: "Kepemilikan Domain & Hosting",
  bug_warranty: "Garansi Bug Fixing",
  ip_rights: "Hak atas Kekayaan Intelektual",
  out_of_scope: "Di Luar Lingkup",
  payment_schedule: "Jadwal Pembayaran",
  target_keywords: "Keyword Target",
  success_metrics: "Metrik Keberhasilan",
  disclaimer: "Batasan Ekspektasi",
  reporting: "Laporan & Reporting",
  scope_change: "Perubahan Keyword / Arah",
  platforms: "Platform",
  approval_flow: "Proses Approval Konten",
  content_ownership: "Hak Kepemilikan Konten",
  platform_rules: "Kepatuhan Aturan Platform",
  escalation: "Escalation & Urgent Content",
  scope_included: "Cakupan Layanan",
  sla_metrics: "SLA Response Time",
  coverage_hours: "Jam Coverage",
  emergency_escalation: "Escalation Darurat",
  ticket_resolution: "Penyelesaian Ticket",
  concept_count: "Jumlah Konsep Awal",
  moodboard_approval: "Moodboard & Brief Approval",
  color_standards: "Standar Warna & Tipografi",
  file_usage_rights: "Format File & Hak Penggunaan",
  scope_monthly: "Cakupan per Bulan",
  hour_allocation: "Penggunaan Jam/Slot Bulanan",
  addon_rate: "Rate Add-on",
  change_request_process: "Proses Change Request",
  termination_notice: "Pemberitahuan Penghentian",
};

const DATE_KEY_PATTERNS = ["tanggal", "due_date", "valid_until", "tanggal_mulai", "tanggal_akhir", "expired", "expiry"];
const INVOICE_NUMBER_KEYS = ["nomor_invoice", "no_invoice", "nomor"];
const LINE_ITEM_KEYS = ["items_rows", "items_table", "line_items", "items"];
const TOTAL_KEYS = ["total", "total_harga", "grand_total", "total_bayar", "total_amount", "jumlah_total", "total_tagihan"];
const LOGO_KEYS = ["logo", "logo_perusahaan", "company_logo"];
const LARGE_TEXT_PATTERNS = ["html", "body", "scope", "terms", "rows", "alamat", "payment_info", "catatan", "keterangan", "deliverables", "out_of_scope", "payment_schedule", "tech_spec", "milestones", "ip_rights", "bug_warranty", "domain_hosting", "revision_limit", "sla_metrics", "coverage_hours", "scope_included", "emergency_escalation", "ticket_resolution", "target_keywords", "success_metrics", "disclaimer", "reporting", "scope_change", "platforms", "approval_flow", "content_ownership", "platform_rules", "escalation", "concept_count", "moodboard_approval", "color_standards", "file_usage_rights", "scope_monthly", "hour_allocation", "addon_rate", "change_request_process", "termination_notice"];
const RUPIAH_PATTERNS = ["nilai", "harga", "amount", "nominal", "bayar", "biaya", "tarif", "fee", "price", "cost"];
const PHONE_PATTERNS = ["phone", "telepon", "telp", "hp", "whatsapp", "wa"];
const EMAIL_PATTERNS = ["email", "mail"];
const READONLY_COMPANY_KEYS = ["brand_name", "nama_perusahaan", "alamat_perusahaan", "phone_perusahaan", "email_perusahaan", "tagline"];
const LAYANAN_KEYS = ["layanan", "service", "jenis_layanan"];
const KLIEN_KEYS = ["klien", "nama_klien"];
const PAYMENT_METHOD_KEY = "payment_method";
const DEDUP_PAIRS: [string, string][] = [
  ["valid_until", "validity"],
  ["klien", "nama"],
];

// Keys that are server-generated aliases — always hide if their primary exists
const SERVER_ALIAS_KEYS = new Set([
  "nama_klien", "perusahaan_klien", "nama_perusahaan",
  "alamat_perusahaan", "phone_perusahaan", "email_perusahaan",
  "brand_name", "tagline",
]);

const FIELD_HINTS: Record<string, string> = {
  klien: "Nama klien / bisnis penerima dokumen",
  nama: "Nama lengkap penerima",
  alamat: "Alamat lengkap klien",
  phone: "Contoh: 0812-3456-7890",
  email: "Contoh: klien@email.com",
  layanan: "Jenis layanan yang diberikan (mis. Pembuatan Website, SEO Bulanan)",
  perihal: "Topik / judul surat (mis. Penawaran Jasa Pembuatan Website)",
  scope: "Rincian pekerjaan yang dikerjakan — apa saja yang termasuk dan tidak termasuk",
  terms: "Syarat & ketentuan: pembayaran, revisi, kerahasiaan, dll",
  durasi: "Lama kontrak berlaku (mis. 3 bulan, 1 tahun)",
  nilai_kontrak: "Nilai total kontrak dalam Rupiah",
  tanggal_mulai: "Tanggal kontrak mulai berlaku",
  tanggal_akhir: "Tanggal kontrak berakhir",
  valid_until: "Batas akhir penawaran berlaku",
  due_date: "Tanggal jatuh tempo pembayaran",
  payment_info: "Rekening atau metode pembayaran yang tampil di invoice",
  catatan: "Catatan tambahan untuk penerima invoice",
  keterangan: "Keterangan pembayaran, misalnya termin pertama atau pelunasan",
  // Website Development
  tech_spec: "Domain, hosting, tech stack, browser support (pisahkan baris per item)",
  deliverables: "Daftar file/output yang diserahkan ke klien (pisahkan baris per item)",
  revision_limit: "Contoh: Maksimal 2 kali revisi gratis. Revisi tambahan berbayar.",
  milestones: "Daftar milestone: 1. Kick-off, 2. Development, 3. Testing, 4. Serah terima",
  domain_hosting: "Siapa punya domain, siapa manage hosting",
  bug_warranty: "Contoh: Bug fixing gratis 30 hari setelah serah terima",
  ip_rights: "Contoh: Source code milik klien setelah pelunasan",
  payment_schedule: "Jadwal termin: DP %, Approval %, Serah terima %",
  // SEO
  target_keywords: "Daftar keyword yang dijanjikan (pisahkan baris per keyword)",
  success_metrics: "Metrik keberhasilan: ranking, traffic, dll",
  disclaimer: "Batasan: Tidak menjamin ranking #1, hasil bergantung algoritma",
  reporting: "Frekuensi & format laporan bulanan",
  scope_change: "Contoh: Perubahan keyword memerlukan addendum + penyesuaian biaya",
  // Sosmed
  platforms: "Platform yang dikelola: Instagram, TikTok, Facebook, dll",
  approval_flow: "Proses approval konten: calendar H-3, approval H-1",
  content_ownership: "Hak milik konten setelah pembayaran; boleh untuk portofolio",
  platform_rules: "Klien bertanggung jawab atas kepatuhan aturan platform",
  escalation: "Kontak di luar jam kerja untuk konten urgent",
  // Maintenance
  scope_included: "Daftar yang termasuk: update plugin, backup, security scan, dll",
  sla_metrics: "Critical: 4 jam. Normal: 1x24 jam. Low: 3x24 jam",
  coverage_hours: "Contoh: Senin-Jumat 09.00-18.00 WIB",
  emergency_escalation: "Kontak WA/SMS untuk kondisi darurat di luar jam kerja",
  ticket_resolution: "Contoh: Issue resolved saat klien berikan sign-off",
  // Branding
  concept_count: "Contoh: 3 arah konsep awal, pilih 1 untuk dikembangkan",
  moodboard_approval: "Brief visual harus di-approve sebelum desain dimulai",
  color_standards: "Format warna: Pantone, CMYK, HEX, RGB sesuai kebutuhan",
  file_usage_rights: "Hak penggunaan komersial, excl. resale; portofolio dengan izin",
  // Retainer
  scope_monthly: "Daftar layanan per bulan (jam dev, konten, support, dll)",
  hour_allocation: "Contoh: Slot tak terpakai tidak dapat di-akumulasi",
  addon_rate: "Contoh: Rp 150.000/jam untuk add-on di luar paket",
  change_request_process: "Proses permintaan perubahan via email atau task board",
  termination_notice: "Contoh: Minimal 30 hari kalender sebelum akhir bulan berjalan",
};

const TEMPLATE_STORAGE_PREFIX = "kt_field_templates_";

function loadFieldTemplates(key: string): string[] {
  try { return JSON.parse(localStorage.getItem(TEMPLATE_STORAGE_PREFIX + key) || "[]"); } catch { return []; }
}

function saveFieldTemplate(key: string, value: string) {
  const existing = loadFieldTemplates(key);
  const trimmed = value.trim();
  if (!trimmed || existing.includes(trimmed)) return;
  localStorage.setItem(TEMPLATE_STORAGE_PREFIX + key, JSON.stringify([trimmed, ...existing].slice(0, 10)));
}

function deleteFieldTemplate(key: string, idx: number) {
  const existing = loadFieldTemplates(key);
  existing.splice(idx, 1);
  localStorage.setItem(TEMPLATE_STORAGE_PREFIX + key, JSON.stringify(existing));
}

function isDateKey(key: string): boolean {
  const k = key.toLowerCase();
  return DATE_KEY_PATTERNS.some(p => k === p || k.startsWith(p + "_") || k.endsWith("_" + p));
}

function isInvoiceNumberKey(key: string): boolean {
  return INVOICE_NUMBER_KEYS.includes(key.toLowerCase());
}

function isRupiahKey(key: string): boolean {
  const k = key.toLowerCase();
  return RUPIAH_PATTERNS.some(p => k.includes(p));
}

function isPhoneKey(key: string): boolean {
  const k = key.toLowerCase();
  return PHONE_PATTERNS.some(p => k === p || k.includes(p));
}

function isEmailKey(key: string): boolean {
  const k = key.toLowerCase();
  return EMAIL_PATTERNS.some(p => k === p || k.endsWith("_" + p));
}

function isReadonlyCompanyKey(key: string): boolean {
  return READONLY_COMPANY_KEYS.includes(key.toLowerCase());
}

function isLayananKey(key: string): boolean {
  return LAYANAN_KEYS.includes(key.toLowerCase());
}

function isLineItemKey(key: string): boolean {
  const k = key.toLowerCase();
  return LINE_ITEM_KEYS.includes(k);
}

function isTotalKey(key: string): boolean {
  return TOTAL_KEYS.includes(key.toLowerCase());
}

function isLogoKey(key: string): boolean {
  return LOGO_KEYS.includes(key.toLowerCase());
}

function isLargeTextKey(key: string): boolean {
  const k = key.toLowerCase();
  return LARGE_TEXT_PATTERNS.some(p => k.includes(p));
}

function parseRupiah(val: string): number {
  return parseInt(val.replace(/[^0-9]/g, "")) || 0;
}

function toRupiahDisplay(num: number): string {
  if (!num) return "";
  return "Rp " + new Intl.NumberFormat("id-ID").format(num);
}

function toRupiahRaw(display: string): string {
  const num = parseRupiah(display);
  return num ? toRupiahDisplay(num) : display;
}

function extractImgSrc(html: string): string {
  const m = html.match(/src=["']([^"']+)["']/i);
  return m ? m[1] : "";
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  })[char] || char);
}

interface LineItem {
  id: string;
  name: string;
  description: string;
  qty: number;
  price: number;
}

function lineItemsToHtml(items: LineItem[]): string {
  if (items.length === 0) return "";
  const rows = items.map((item, i) => {
    const subtotal = item.qty * item.price;
    const description = item.description
      ? `<div style="margin-top:3px;color:#6b7280;font-size:11px;line-height:1.45">${escapeHtml(item.description)}</div>`
      : "";
    return `<tr><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb"><strong>${escapeHtml(item.name)}</strong>${description}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:center">${item.qty}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right">${formatRupiah(item.price)}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600">${formatRupiah(subtotal)}</td></tr>`;
  }).join("");
  const total = items.reduce((s, i) => s + i.qty * i.price, 0);
  return `<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#f3f4f6"><th style="padding:8px;text-align:left">Layanan</th><th style="padding:8px;text-align:center">Jumlah</th><th style="padding:8px;text-align:right">Harga</th><th style="padding:8px;text-align:right">Total</th></tr></thead><tbody>${rows}</tbody><tfoot><tr style="background:#fef3c7"><td colspan="3" style="padding:8px;text-align:right;font-weight:bold">Total Tagihan</td><td style="padding:8px;text-align:right;font-weight:bold">${formatRupiah(total)}</td></tr></tfoot></table>`;
}

function formatDateForInput(val: string): string {
  if (!val) return "";
  const months: Record<string, string> = { januari: "01", februari: "02", maret: "03", april: "04", mei: "05", juni: "06", juli: "07", agustus: "08", september: "09", oktober: "10", november: "11", desember: "12" };
  const m = val.match(/^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$/);
  if (m) {
    const month = months[m[2].toLowerCase()];
    if (month) return `${m[3]}-${month}-${m[1].padStart(2, "0")}`;
  }
  if (/^\d{4}-\d{2}-\d{2}/.test(val)) return val.slice(0, 10);
  return "";
}

function formatDateForDisplay(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
}

interface VariableInputFormProps {
  variables: Record<string, string>;
  setVariables: (v: Record<string, string> | ((prev: Record<string, string>) => Record<string, string>)) => void;
  lineItems: Record<string, LineItem[]>;
  setLineItems: React.Dispatch<React.SetStateAction<Record<string, LineItem[]>>>;
  selectedTemplate: any;
  paymentMethods: any[];
  products: any[];
  setProductPickerForKey: (key: string | null) => void;
  setProductPickerMode: (mode: "line_item" | "single") => void;
  klienCandidates: any[];
  klienSearch: string;
  setKlienSearch: (s: string) => void;
  klienDropdownOpen: boolean;
  setKlienDropdownOpen: (b: boolean) => void;
  klienRef: React.RefObject<HTMLDivElement | null>;
  setShowSeqEditor: (b: boolean) => void;
  loadCurrentSequence: () => void;
  setToast: (t: { message: string; type: "success" | "error" } | null) => void;
}

export default function VariableInputForm({
  variables, setVariables, lineItems, setLineItems, selectedTemplate, paymentMethods, products,
  setProductPickerForKey, setProductPickerMode, klienCandidates, klienSearch, setKlienSearch,
  klienDropdownOpen, setKlienDropdownOpen, klienRef, setShowSeqEditor, loadCurrentSequence, setToast,
}: VariableInputFormProps) {
  const [fieldTemplateOpen, setFieldTemplateOpen] = useState<string | null>(null);
  const [fieldTemplates, setFieldTemplates] = useState<Record<string, string[]>>({});
  const [layananOpenKey, setLayananOpenKey] = useState<string | null>(null);
  const [layananSearch, setLayananSearch] = useState("");
  const layananRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (layananRef.current && !layananRef.current.contains(e.target as Node)) {
        setLayananOpenKey(null);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const updateLineItem = (key: string, id: string, patch: Partial<LineItem>) => {
    setLineItems(prev => {
      const items = (prev[key] || []).map(it => it.id === id ? { ...it, ...patch } : it);
      const html = lineItemsToHtml(items);
      setVariables(v => ({ ...v, [key]: html }));
      const total = items.reduce((s, it) => s + it.qty * it.price, 0);
      setVariables(v => {
        const updated = { ...v };
        for (const k of Object.keys(updated)) {
          if (isTotalKey(k)) updated[k] = formatRupiah(total);
        }
        return updated;
      });
      return { ...prev, [key]: items };
    });
  };

  const deleteLineItem = (key: string, id: string) => {
    setLineItems(prev => {
      const items = (prev[key] || []).filter(it => it.id !== id);
      const html = lineItemsToHtml(items);
      setVariables(v => ({ ...v, [key]: html }));
      const total = items.reduce((s, it) => s + it.qty * it.price, 0);
      setVariables(v => {
        const updated = { ...v };
        for (const k of Object.keys(updated)) {
          if (isTotalKey(k)) updated[k] = formatRupiah(total);
        }
        return updated;
      });
      return { ...prev, [key]: items };
    });
  };

  const addEmptyLineItem = (key: string) => {
    const newItem: LineItem = { id: crypto.randomUUID(), name: "", description: "", qty: 1, price: 0 };
    setLineItems(prev => {
      const items = [...(prev[key] || []), newItem];
      const html = lineItemsToHtml(items);
      setVariables(v => ({ ...v, [key]: html }));
      const total = items.reduce((s, it) => s + it.qty * it.price, 0);
      setVariables(v => {
        const updated = { ...v };
        for (const k of Object.keys(updated)) {
          if (isTotalKey(k)) updated[k] = formatRupiah(total);
        }
        return updated;
      });
      return { ...prev, [key]: items };
    });
  };

  const addLineItemFromProduct = (key: string, product: any) => {
    const newItem: LineItem = {
      id: crypto.randomUUID(),
      name: product.name,
      description: product.description || (product.features?.join(", ") || ""),
      qty: 1,
      price: product.base_price,
    };
    setLineItems(prev => {
      const items = [...(prev[key] || []), newItem];
      const html = lineItemsToHtml(items);
      setVariables(v => ({ ...v, [key]: html }));
      const total = items.reduce((s, it) => s + it.qty * it.price, 0);
      setVariables(v => {
        const updated = { ...v };
        for (const k of Object.keys(updated)) {
          if (isTotalKey(k)) updated[k] = formatRupiah(total);
        }
        return updated;
      });
      return { ...prev, [key]: items };
    });
    setProductPickerForKey(null);
  };

  const pickProductForSingleField = (key: string, product: any) => {
    setVariables(prev => ({
      ...prev,
      [key]: product.name,
      scope: key === "layanan" && !prev.scope
        ? (product.description || product.features?.join("\n") || "")
        : prev.scope,
    }));
    setProductPickerForKey(null);
  };

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Isi Variabel</h2>
      <p className="text-xs text-gray-500">Identitas perusahaan, logo, dan tagline diambil otomatis dari Brand Kit.</p>
      {Object.keys(variables).length === 0 && <p className="text-sm text-gray-400">Template ini tidak punya variabel.</p>}
      <div className="space-y-4">
        {(() => {
          const allKeys = Object.keys(variables);
          const usesAutoNumber = ["invoice", "receipt", "surat_penawaran"].includes(selectedTemplate?.type || "");
          const numberKeys = usesAutoNumber ? allKeys.filter(k => isInvoiceNumberKey(k)) : [];
          const primaryNumberKey = numberKeys[0] || null;
          const renderedKeys = new Set<string>();

          const suppressedKeys = new Set<string>();
          for (const [primary, secondary] of DEDUP_PAIRS) {
            if (allKeys.includes(primary) && allKeys.includes(secondary)) {
              suppressedKeys.add(secondary);
            }
          }
          // Always suppress server alias keys — they're brand-owned or display-only
          allKeys.forEach(k => { if (SERVER_ALIAS_KEYS.has(k)) suppressedKeys.add(k); });

          return Object.entries(variables).map(([key, val]) => {
            if (renderedKeys.has(key)) return null;
            if (numberKeys.includes(key) && key !== primaryNumberKey) return null;
            if (suppressedKeys.has(key)) return null;
            renderedKeys.add(key);

            const label = FIELD_LABELS[key.toLowerCase()] || key.replace(/_/g, " ");

            // Logo field
            if (isLogoKey(key)) {
              const logoSrc = extractImgSrc(val);
              return (
                <div key={key}>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Logo</label>
                  <div className="mt-1 flex items-center gap-4 p-3 border border-gray-200 dark:border-neutral-700 rounded-xl bg-gray-50 dark:bg-neutral-800/50">
                    {logoSrc ? (
                      <img src={logoSrc} alt="Logo" className="h-12 w-auto object-contain rounded" />
                    ) : (
                      <div className="h-12 w-20 bg-gray-200 dark:bg-neutral-700 rounded flex items-center justify-center text-xs text-gray-400">No logo</div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-500">Logo dari Brand Kit (otomatis)</p>
                      <p className="text-[10px] text-gray-400 truncate mt-0.5">{logoSrc || "Belum ada logo di Brand Kit"}</p>
                    </div>
                  </div>
                </div>
              );
            }

            // Date field
            if (isDateKey(key)) {
              const isoVal = formatDateForInput(val);
              return (
                <div key={key}>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                  <input
                    type="date"
                    value={isoVal}
                    onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value ? formatDateForDisplay(e.target.value) : "" }))}
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800"
                  />
                  {val && <p className="text-xs text-gray-400 mt-1">Tampil: {val}</p>}
                </div>
              );
            }

            // Invoice number
            if (numberKeys.includes(key)) {
              const numberLabel = selectedTemplate?.type === "invoice"
                ? "Nomor Invoice"
                : selectedTemplate?.type === "receipt"
                  ? "Nomor Bukti Pembayaran"
                  : "Nomor Surat";
              return (
                <div key={key}>
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{numberLabel}</label>
                    {selectedTemplate?.type === "invoice" && (
                      <button type="button" onClick={() => { setShowSeqEditor(true); loadCurrentSequence(); }}
                        className="text-[11px] text-amber-600 hover:text-amber-700 font-semibold">Atur nomor awal</button>
                    )}
                  </div>
                  <input
                    type="text"
                    value={val}
                    readOnly
                    placeholder={`{{${key}}}`}
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-gray-50 dark:bg-neutral-800/50 font-mono"
                  />
                  <p className="text-[11px] text-gray-400 mt-1">Terisi otomatis dan dikunci saat PDF final dibuat.</p>
                </div>
              );
            }

            // Total field
            if (isTotalKey(key)) {
              if (selectedTemplate?.type === "invoice") return null;
              return (
                <div key={key}>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label} (otomatis)</label>
                  <input type="text" value={val} readOnly placeholder="Akan terisi otomatis dari line items"
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-gray-50 dark:bg-neutral-800/50 text-amber-700 font-bold" />
                </div>
              );
            }

            // Line items
            if (isLineItemKey(key)) {
              const items = lineItems[key] || [];
              const total = items.reduce((s, it) => s + it.qty * it.price, 0);
              return (
                <div key={key}>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                  <div className="mt-1 space-y-2">
                    {items.length === 0 && (
                      <div className="border border-dashed border-gray-200 dark:border-neutral-700 rounded-xl p-6 text-center text-sm text-gray-400">
                        Belum ada item. Tambah dari paket atau manual.
                      </div>
                    )}
                    {items.map((it, idx) => (
                      <div key={it.id} className="border border-gray-200 dark:border-neutral-700 rounded-xl p-3 space-y-2 bg-white dark:bg-neutral-900">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-gray-400 w-6 shrink-0">#{idx + 1}</span>
                          <input type="text" value={it.name} placeholder="Nama item"
                            onChange={e => updateLineItem(key, it.id, { name: e.target.value })}
                            className="flex-1 px-2 py-1.5 text-xs border border-gray-200 dark:border-neutral-700 rounded bg-white dark:bg-neutral-900" />
                          <button onClick={() => deleteLineItem(key, it.id)} className="text-gray-400 hover:text-red-500 shrink-0 p-1">
                            <Trash2 size={14} />
                          </button>
                        </div>
                        <div className="grid grid-cols-3 gap-2">
                          <div>
                            <label className="text-[10px] font-bold text-gray-400 uppercase">Qty</label>
                            <input type="number" min="1" value={it.qty}
                              onChange={e => updateLineItem(key, it.id, { qty: Math.max(1, parseInt(e.target.value) || 1) })}
                              className="w-full mt-0.5 px-2 py-1.5 text-xs border border-gray-200 dark:border-neutral-700 rounded bg-white dark:bg-neutral-900 text-center" />
                          </div>
                          <div>
                            <label className="text-[10px] font-bold text-gray-400 uppercase">Harga Satuan</label>
                            <input type="number" min="0" value={it.price}
                              onChange={e => updateLineItem(key, it.id, { price: Math.max(0, parseInt(e.target.value) || 0) })}
                              className="w-full mt-0.5 px-2 py-1.5 text-xs border border-gray-200 dark:border-neutral-700 rounded bg-white dark:bg-neutral-900 text-right" />
                          </div>
                          <div>
                            <label className="text-[10px] font-bold text-gray-400 uppercase">Subtotal</label>
                            <div className="w-full mt-0.5 px-2 py-1.5 text-xs border border-gray-200 dark:border-neutral-700 rounded bg-gray-50 dark:bg-neutral-800/50 text-right font-semibold text-amber-700">
                              {formatRupiah(it.qty * it.price)}
                            </div>
                          </div>
                        </div>
                        <div>
                          <label className="text-[10px] font-bold text-gray-400 uppercase">Deskripsi</label>
                          <textarea value={it.description} placeholder="Deskripsi paket / fitur..."
                            onChange={e => updateLineItem(key, it.id, { description: e.target.value })} rows={2}
                            className="w-full mt-0.5 px-2 py-1.5 text-xs border border-gray-200 dark:border-neutral-700 rounded bg-white dark:bg-neutral-900 resize-y" />
                        </div>
                      </div>
                    ))}
                    {items.length > 0 && (
                      <div className="flex items-center justify-between bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-xl px-4 py-2.5">
                        <span className="text-sm font-bold text-amber-800 dark:text-amber-200">TOTAL</span>
                        <span className="text-base font-bold text-amber-700 dark:text-amber-300">{formatRupiah(total)}</span>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 mt-2">
                    <button type="button" onClick={() => { setProductPickerMode("line_item"); setProductPickerForKey(key); }}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-amber-500 hover:bg-amber-600 text-white rounded-lg">
                      <Plus size={14} /> Tambah dari Paket
                    </button>
                    <button type="button" onClick={() => addEmptyLineItem(key)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border border-gray-200 dark:border-neutral-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-neutral-800">
                      <Plus size={14} /> Item Manual
                    </button>
                  </div>
                </div>
              );
            }

            // Read-only company info
            if (isReadonlyCompanyKey(key)) return null;

            // Rupiah field
            if (isRupiahKey(key)) {
              return (
                <div key={key}>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                  <input type="text" inputMode="numeric" value={val}
                    onChange={e => setVariables(prev => ({ ...prev, [key]: toRupiahRaw(e.target.value) }))}
                    placeholder="Rp 0"
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 font-semibold" />
                  <p className="text-[11px] text-gray-400 mt-1">{FIELD_HINTS[key.toLowerCase()] || "Format Rupiah otomatis"}</p>
                </div>
              );
            }

            // Phone field
            if (isPhoneKey(key)) {
              return (
                <div key={key}>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                  <input type="tel" value={val}
                    onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                    placeholder="0812-3456-7890"
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" />
                  <p className="text-[11px] text-gray-400 mt-1">{FIELD_HINTS[key.toLowerCase()] || "Nomor telepon / WhatsApp"}</p>
                </div>
              );
            }

            // Email field
            if (isEmailKey(key)) {
              const valid = !val || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
              return (
                <div key={key}>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                  <input type="email" value={val}
                    onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                    placeholder="klien@email.com"
                    className={`mt-1 w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-neutral-800 ${valid ? "border-gray-200 dark:border-neutral-700" : "border-red-400"}`} />
                  {!valid && <p className="text-[11px] text-red-500 mt-1">Format email tidak valid</p>}
                </div>
              );
            }

            // Klien field
            if (KLIEN_KEYS.includes(key.toLowerCase())) {
              const savedTpls = fieldTemplates[key] !== undefined ? fieldTemplates[key] : loadFieldTemplates(key);
              return (
                <div key={key} ref={klienRef as any}>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                  <div className="relative mt-1">
                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                    <input type="text" value={klienDropdownOpen ? klienSearch : val}
                      onFocus={() => { setKlienSearch(val); setKlienDropdownOpen(true); }}
                      onChange={e => { setKlienSearch(e.target.value); setVariables(prev => ({ ...prev, [key]: e.target.value })); }}
                      onBlur={() => setTimeout(() => setKlienDropdownOpen(false), 150)}
                      placeholder="Ketik atau cari dari leads/klien..."
                      className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" />
                    {klienDropdownOpen && klienCandidates.length > 0 && (
                      <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-700 rounded-xl shadow-lg max-h-52 overflow-y-auto">
                        {klienCandidates.map((c: any, i: number) => (
                          <button key={i} type="button"
                            onMouseDown={() => { c.onPick(); setKlienDropdownOpen(false); setKlienSearch(""); }}
                            className="w-full text-left px-3 py-2 hover:bg-amber-50 dark:hover:bg-amber-950/20 transition-colors">
                            <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{c.label}</p>
                            <p className="text-xs text-gray-400">{c.sub}</p>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  {FIELD_HINTS[key.toLowerCase()] && <p className="text-[11px] text-gray-400 mt-1">{FIELD_HINTS[key.toLowerCase()]}</p>}
                </div>
              );
            }

            // Payment method field
            if (key.toLowerCase() === PAYMENT_METHOD_KEY) {
              return (
                <div key={key}>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                  <select value={val} onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800">
                    <option value="">— Pilih metode pembayaran —</option>
                    {paymentMethods.map((m: any) => (
                      <option key={m.id} value={`${m.name} - ${m.account_name} (${m.account_number})`}>
                        {m.name} · {m.account_name} · {m.account_number}
                      </option>
                    ))}
                    <option value="Tunai">Tunai</option>
                  </select>
                  {paymentMethods.length === 0 && (
                    <p className="text-[11px] text-amber-600 mt-1">Belum ada metode pembayaran aktif. Tambah di Finance → Metode Pembayaran.</p>
                  )}
                </div>
              );
            }

            // Layanan field — custom combobox (searchable dropdown of packages + manual typing)
            if (isLayananKey(key)) {
              const hasProducts = products.length > 0;
              const isOpen = layananOpenKey === key;
              const q = layananSearch.toLowerCase().trim();
              const candidates = hasProducts
                ? products
                    .map((p: any) => ({ p, sub: formatRupiah(p.base_price) }))
                    .filter(x => !q || x.p.name.toLowerCase().includes(q) || String(x.p.description || "").toLowerCase().includes(q))
                    .slice(0, 30)
                : [];
              return (
                <div key={key} ref={layananRef}>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                  <div className="relative mt-1">
                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                    <input type="text" value={isOpen ? layananSearch : val}
                      onFocus={() => { setLayananSearch(val); setLayananOpenKey(key); }}
                      onChange={e => { setLayananSearch(e.target.value); setVariables(prev => ({ ...prev, [key]: e.target.value })); if (!isOpen) setLayananOpenKey(key); }}
                      onBlur={() => setTimeout(() => setLayananOpenKey(null), 150)}
                      placeholder={hasProducts ? "Ketik atau pilih paket layanan..." : "Ketik jenis layanan"}
                      className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" />
                    {isOpen && candidates.length > 0 && (
                      <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-700 rounded-xl shadow-lg max-h-56 overflow-y-auto">
                        {candidates.map(({ p, sub }: any) => (
                          <button key={p.id} type="button"
                            onMouseDown={() => { setVariables(prev => ({ ...prev, [key]: p.name })); setLayananOpenKey(null); setLayananSearch(""); }}
                            className="w-full text-left px-3 py-2 hover:bg-amber-50 dark:hover:bg-amber-950/20 transition-colors">
                            <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{p.name}</p>
                            <p className="text-xs text-gray-400">{sub}</p>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  <p className="text-[11px] text-gray-400 mt-1">
                    {hasProducts
                      ? `Pilih dari ${products.length} paket, atau ketik manual.`
                      : FIELD_HINTS[key.toLowerCase()] || "Ketik jenis layanan"}
                  </p>
                </div>
              );
            }

            // Large text field
            if (isLargeTextKey(key)) {
              const isTemplatable = ["terms", "scope", "catatan", "keterangan", "payment_info"].some(p => key.toLowerCase().includes(p));
              const savedTpls = fieldTemplates[key] !== undefined ? fieldTemplates[key] : loadFieldTemplates(key);
              return (
                <div key={key}>
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                    {isTemplatable && (
                      <div className="flex items-center gap-1.5">
                        <button type="button"
                          onClick={() => {
                            if (val.trim()) {
                              saveFieldTemplate(key, val);
                              setFieldTemplates(prev => ({ ...prev, [key]: loadFieldTemplates(key) }));
                              setToast({ message: "Disimpan sebagai template", type: "success" });
                            }
                          }}
                          title="Simpan teks ini sebagai template"
                          className="flex items-center gap-1 text-[11px] text-gray-400 hover:text-amber-600 transition-colors">
                          <Save size={12} /> Simpan
                        </button>
                        {savedTpls.length > 0 && (
                          <button type="button"
                            onClick={() => setFieldTemplateOpen(fieldTemplateOpen === key ? null : key)}
                            className="flex items-center gap-1 text-[11px] text-amber-600 hover:text-amber-700 font-semibold transition-colors">
                            <BookOpen size={12} /> Template ({savedTpls.length})
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                  {isTemplatable && fieldTemplateOpen === key && savedTpls.length > 0 && (
                    <div className="mt-1 border border-amber-200 dark:border-amber-800 rounded-xl bg-amber-50 dark:bg-amber-950/20 p-2 space-y-1 max-h-40 overflow-y-auto">
                      {savedTpls.map((tpl: string, i: number) => (
                        <div key={i} className="flex items-start gap-2 group">
                          <button type="button"
                            onClick={() => { setVariables(prev => ({ ...prev, [key]: tpl })); setFieldTemplateOpen(null); }}
                            className="flex-1 text-left text-xs text-neutral-700 dark:text-neutral-300 hover:text-amber-700 line-clamp-2 py-0.5">
                            {tpl}
                          </button>
                          <button type="button"
                            onClick={() => { deleteFieldTemplate(key, i); setFieldTemplates(prev => ({ ...prev, [key]: loadFieldTemplates(key) })); }}
                            className="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-0.5">
                            <X size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  <textarea value={val} onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))} rows={4}
                    placeholder={FIELD_HINTS[key.toLowerCase()] || `{{${key}}}`}
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 resize-y" />
                  {FIELD_HINTS[key.toLowerCase()] && <p className="text-[11px] text-gray-400 mt-1">{FIELD_HINTS[key.toLowerCase()]}</p>}
                </div>
              );
            }

            // Default text input
            return (
              <div key={key}>
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                <input type="text" value={val}
                  onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                  placeholder={FIELD_HINTS[key.toLowerCase()] || `{{${key}}}`}
                  className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" />
                {FIELD_HINTS[key.toLowerCase()] && <p className="text-[11px] text-gray-400 mt-1">{FIELD_HINTS[key.toLowerCase()]}</p>}
              </div>
            );
          });
        })()}
      </div>
    </div>
  );
}
