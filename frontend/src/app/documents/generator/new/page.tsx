"use client";
import { formatRupiah } from "../../../../utils/formatter";

import { useState, useEffect, useMemo, useRef } from "react";
import { apiFetch } from "../../../../lib/api";
import { ChevronRight, ChevronLeft, Download, Mail, Check, Search, Plus, Trash2, X, BookOpen, Save } from "lucide-react";
import Toast from "../../../../components/Toast";
import { TemplateStepper, TemplatePicker } from "../../../../components/documents/TemplatePicker";
import { TargetPicker } from "../../../../components/documents/TargetPicker";
import { VariableInputForm } from "../../../../components/documents/VariableInputForm";

interface PaymentMethod { id: number; name: string; account_number: string; account_name: string; notes: string | null; is_active: boolean; }

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

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DocTemplate { id: string; name: string; type: string; variables: string[]; }
interface Lead { id: number; business_name: string; phone_number: string; address: string | null; product_interest: string | null; }
interface Contact { id: number; business_name: string; owner_name: string | null; phone_number: string; purchased_product: string | null; }
interface Product { id: string; name: string; description: string | null; base_price: number; features: string[]; }
interface Project { id: string; lead_id: number | null; name: string; nominal: number; start_date: string | null; end_date: string | null; service_type: string | null; contract_months: number | null; }
interface GeneratedDoc { id: string; file_url: string; template_name: string; display_filename?: string; }

interface LineItem {
  id: string;
  name: string;
  description: string;
  qty: number;
  price: number;
}

const STEPS = ["Pilih Template", "Pilih Target", "Isi Variabel", "Preview", "Selesai"];

const PAYMENT_METHOD_KEY = "payment_method";
const KLIEN_KEYS = ["klien", "nama_klien"];
const DEDUP_PAIRS: [string, string][] = [
  ["valid_until", "validity"],
  ["klien", "nama"],
];

const DATE_KEY_PATTERNS = ["tanggal", "due_date", "valid_until", "tanggal_mulai", "tanggal_akhir", "expired", "expiry"];
const INVOICE_NUMBER_KEYS = ["nomor_invoice", "no_invoice", "nomor"];
const LINE_ITEM_KEYS = ["items_rows", "items_table", "line_items", "items"];
const TOTAL_KEYS = ["total", "total_harga", "grand_total", "total_bayar", "total_amount", "jumlah_total", "total_tagihan"];
const LOGO_KEYS = ["logo", "logo_perusahaan", "company_logo"];
const LARGE_TEXT_PATTERNS = ["html", "body", "scope", "terms", "rows", "alamat", "payment_info", "catatan", "keterangan"];
const RUPIAH_PATTERNS = ["nilai", "harga", "amount", "nominal", "bayar", "biaya", "tarif", "fee", "price", "cost"];
const PHONE_PATTERNS = ["phone", "telepon", "telp", "hp", "whatsapp", "wa"];
const EMAIL_PATTERNS = ["email", "mail"];
const READONLY_COMPANY_KEYS = ["nama_perusahaan", "alamat_perusahaan", "phone_perusahaan", "email_perusahaan", "tagline"];
const LAYANAN_KEYS = ["layanan", "service", "jenis_layanan"];

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
};

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
};

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

function extractImgSrc(html: string): string {
  const m = html.match(/src=["']([^"']+)["']/i);
  return m ? m[1] : "";
}


function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char] || char);
}

function lineItemsToHtml(items: LineItem[]): string {
  if (items.length === 0) return "";
  const rows = items.map((item, i) => {
    const subtotal = item.qty * item.price;
    return `<tr><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb">${i + 1}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb">${escapeHtml(item.name)}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb">${escapeHtml(item.description)}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:center">${item.qty}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right">${formatRupiah(item.price)}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600">${formatRupiah(subtotal)}</td></tr>`;
  }).join("");
  const total = items.reduce((s, i) => s + i.qty * i.price, 0);
  return `<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#f3f4f6"><th style="padding:8px;text-align:left">No</th><th style="padding:8px;text-align:left">Item</th><th style="padding:8px;text-align:left">Deskripsi</th><th style="padding:8px;text-align:center">Qty</th><th style="padding:8px;text-align:right">Harga</th><th style="padding:8px;text-align:right">Subtotal</th></tr></thead><tbody>${rows}</tbody><tfoot><tr style="background:#fef3c7"><td colspan="5" style="padding:8px;text-align:right;font-weight:bold">Total</td><td style="padding:8px;text-align:right;font-weight:bold">${formatRupiah(total)}</td></tr></tfoot></table>`;
}

export default function DocumentNewPage() {
  const [step, setStep] = useState(0);
  const [templates, setTemplates] = useState<DocTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<DocTemplate | null>(null);
  const [targetType, setTargetType] = useState<"empty" | "lead" | "contact" | "project">("empty");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [targetSearch, setTargetSearch] = useState("");
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [lineItems, setLineItems] = useState<Record<string, LineItem[]>>({});
  const [productPickerForKey, setProductPickerForKey] = useState<string | null>(null);
  const [productPickerMode, setProductPickerMode] = useState<"line_item" | "single">("line_item");
  const [productSearch, setProductSearch] = useState("");
  const [showSeqEditor, setShowSeqEditor] = useState(false);
  const [seqStartFrom, setSeqStartFrom] = useState("");
  const [generating, setGenerating] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [generatedDoc, setGeneratedDoc] = useState<GeneratedDoc | null>(null);
  const [emailModal, setEmailModal] = useState(false);
  const [emailTo, setEmailTo] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [klienSearch, setKlienSearch] = useState("");
  const [klienDropdownOpen, setKlienDropdownOpen] = useState(false);
  const klienRef = useRef<HTMLDivElement>(null);
  const [fieldTemplateOpen, setFieldTemplateOpen] = useState<string | null>(null);
  const [fieldTemplates, setFieldTemplates] = useState<Record<string, string[]>>({});

  useEffect(() => {
    // Sequential fetches to avoid overloading shared hosting (max 6 workers)
    async function loadData() {
      try { const r = await apiFetch("/api/document-templates"); if (r.ok) setTemplates(await r.json()); } catch {}
      try { const r = await apiFetch("/api/leads"); if (r.ok) setLeads(await r.json()); } catch {}
      try { const r = await apiFetch("/api/contacts"); if (r.ok) setContacts(await r.json()); } catch {}
      try { const r = await apiFetch("/api/products?active_only=true"); if (r.ok) setProducts(await r.json()); } catch {}
      try { const r = await apiFetch("/api/projects"); if (r.ok) setProjects(await r.json()); } catch {}
      try { const r = await apiFetch("/api/finance/payment-methods"); if (r.ok) { const d: PaymentMethod[] = await r.json(); setPaymentMethods(d.filter(m => m.is_active)); } } catch {}
    }
    loadData();
  }, []);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  function selectTemplate(t: DocTemplate) {
    setSelectedTemplate(t);
    const vars: Record<string, string> = {};
    const items: Record<string, LineItem[]> = {};
    t.variables.forEach(v => {
      if (isLineItemKey(v)) {
        items[v] = [];
        vars[v] = "";
      } else {
        vars[v] = "";
      }
    });
    setVariables(vars);
    setLineItems(items);
    // Auto-fill defaults immediately when template is picked
    fetchAndApplyDefaults(t, "empty", null);
  }

  async function fetchAndApplyDefaults(template: DocTemplate, ttype: "lead" | "contact" | "project" | "empty", tid: number | string | null) {
    try {
      const params = new URLSearchParams();
      if (ttype !== "empty") params.set("target_type", ttype);
      if (tid !== null) params.set("target_id", String(tid));
      const res = await apiFetch(`/api/document-templates/${template.id}/defaults?${params}`);
      if (!res.ok) return;
      const data = await res.json();
      const defs: Record<string, string> = data.defaults || {};
      setVariables(prev => {
        const merged: Record<string, string> = { ...prev };
        for (const [k, v] of Object.entries(defs)) {
          if (isInvoiceNumberKey(k) && ["invoice", "receipt", "surat_penawaran"].includes(template.type)) merged[k] = v as string;
          else if (k in merged && merged[k] === "") merged[k] = v as string;
          else if (!(k in merged)) merged[k] = v as string;
        }
        return merged;
      });
    } catch { /* silent */ }
  }

  function pickLead(lead: Lead) {
    setSelectedLead(lead);
    setSelectedContact(null);
    setSelectedProject(null);
    setVariables(prev => ({
      ...prev,
      klien: lead.business_name,
      nama: lead.business_name,
      alamat: lead.address || "",
      layanan: lead.product_interest || "",
      phone: lead.phone_number,
    }));
    if (selectedTemplate) fetchAndApplyDefaults(selectedTemplate, "lead", lead.id);
  }

  function pickContact(contact: Contact) {
    setSelectedContact(contact);
    setSelectedLead(null);
    setSelectedProject(null);
    setVariables(prev => ({
      ...prev,
      klien: contact.business_name,
      nama: contact.business_name,
      phone: contact.phone_number,
      layanan: contact.purchased_product || "",
    }));
    if (selectedTemplate) fetchAndApplyDefaults(selectedTemplate, "contact", contact.id);
  }

  function pickProject(project: Project) {
    const lead = leads.find(item => item.id === project.lead_id) || null;
    setSelectedProject(project);
    setSelectedLead(null);
    setSelectedContact(null);
    setVariables(prev => ({
      ...prev,
      klien: lead?.business_name || prev.klien || "",
      nama: lead?.business_name || prev.nama || "",
      alamat: lead?.address || prev.alamat || "",
      phone: lead?.phone_number || prev.phone || "",
      layanan: project.name || project.service_type || prev.layanan || "",
      nilai_kontrak: project.nominal ? formatRupiah(project.nominal) : prev.nilai_kontrak || "",
      tanggal_mulai: project.start_date ? formatDateForDisplay(project.start_date) : prev.tanggal_mulai || "",
      tanggal_akhir: project.end_date ? formatDateForDisplay(project.end_date) : prev.tanggal_akhir || "",
      durasi: project.contract_months ? `${project.contract_months} bulan` : prev.durasi || "",
    }));
    if (selectedTemplate) fetchAndApplyDefaults(selectedTemplate, "project", project.id);
  }

  // Convert ISO date input → Indonesian display, or pass-through
  function formatDateForInput(val: string): string {
    if (!val) return "";
    // Try parse "DD MMMM YYYY" Indonesian → ISO
    const months: Record<string, string> = { januari: "01", februari: "02", maret: "03", april: "04", mei: "05", juni: "06", juli: "07", agustus: "08", september: "09", oktober: "10", november: "11", desember: "12" };
    const m = val.match(/^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$/);
    if (m) {
      const month = months[m[2].toLowerCase()];
      if (month) return `${m[3]}-${month}-${m[1].padStart(2, "0")}`;
    }
    // Already ISO?
    if (/^\d{4}-\d{2}-\d{2}/.test(val)) return val.slice(0, 10);
    return "";
  }

  function formatDateForDisplay(iso: string): string {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
  }

  // Line items helpers
  function syncTotalVariable(items: LineItem[]) {
    const total = items.reduce((s, it) => s + it.qty * it.price, 0);
    setVariables(v => {
      const updated = { ...v };
      for (const k of Object.keys(updated)) {
        if (isTotalKey(k)) updated[k] = formatRupiah(total);
      }
      return updated;
    });
  }

  function addLineItemFromProduct(key: string, product: Product) {
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
      syncTotalVariable(items);
      return { ...prev, [key]: items };
    });
    setProductPickerForKey(null);
    setProductSearch("");
  }

  function pickProductForSingleField(key: string, product: Product) {
    setVariables(prev => ({
      ...prev,
      [key]: product.name,
      scope: key === "layanan" && !prev.scope
        ? (product.description || product.features?.join("\n") || "")
        : prev.scope,
    }));
    setProductPickerForKey(null);
    setProductSearch("");
  }

  function openProductPicker(key: string, mode: "line_item" | "single") {
    setProductPickerMode(mode);
    setProductPickerForKey(key);
    setProductSearch("");
  }

  function addEmptyLineItem(key: string) {
    const newItem: LineItem = { id: crypto.randomUUID(), name: "", description: "", qty: 1, price: 0 };
    setLineItems(prev => {
      const items = [...(prev[key] || []), newItem];
      const html = lineItemsToHtml(items);
      setVariables(v => ({ ...v, [key]: html }));
      syncTotalVariable(items);
      return { ...prev, [key]: items };
    });
  }

  function updateLineItem(key: string, id: string, patch: Partial<LineItem>) {
    setLineItems(prev => {
      const items = (prev[key] || []).map(it => it.id === id ? { ...it, ...patch } : it);
      const html = lineItemsToHtml(items);
      setVariables(v => ({ ...v, [key]: html }));
      syncTotalVariable(items);
      return { ...prev, [key]: items };
    });
  }

  function deleteLineItem(key: string, id: string) {
    setLineItems(prev => {
      const items = (prev[key] || []).filter(it => it.id !== id);
      const html = lineItemsToHtml(items);
      setVariables(v => ({ ...v, [key]: html }));
      syncTotalVariable(items);
      return { ...prev, [key]: items };
    });
  }

  // Invoice sequence editor
  async function loadCurrentSequence() {
    try {
      const res = await apiFetch("/api/documents/invoice-sequence");
      if (res.ok) {
        const data = await res.json();
        setSeqStartFrom(String(data.next_seq));
      }
    } catch { /* silent */ }
  }

  async function saveSequence() {
    const start = parseInt(seqStartFrom);
    if (!start || start < 1) {
      setToast({ message: "Nomor awal harus angka >= 1", type: "error" });
      return;
    }
    try {
      const res = await apiFetch("/api/documents/invoice-sequence", {
        method: "PUT",
        body: JSON.stringify({ start_from: start, template_type: "invoice" }),
      });
      if (!res.ok) throw new Error("Gagal simpan");
      setToast({ message: `Nomor invoice berikutnya: ${start}`, type: "success" });
      setShowSeqEditor(false);
      // Refresh the invoice number variable
      if (selectedTemplate) {
        const ttype = selectedProject ? "project" : selectedLead ? "lead" : selectedContact ? "contact" : "empty";
        const tid = selectedProject?.id ?? selectedLead?.id ?? selectedContact?.id ?? null;
        await fetchAndApplyDefaults(selectedTemplate, ttype, tid);
      }
    } catch (e: unknown) {
      setToast({ message: e instanceof Error ? e.message : "Gagal simpan", type: "error" });
    }
  }

  function buildDocumentPayload() {
    const ttype = selectedProject ? "project" : selectedLead ? "lead" : selectedContact ? "contact" : null;
    const tid = selectedProject?.id ?? selectedLead?.id ?? selectedContact?.id ?? null;
    return {
      template_id: selectedTemplate?.id,
      target_type: ttype,
      target_id: tid !== null ? String(tid) : null,
      variables,
    };
  }

  async function handlePreview() {
    if (!selectedTemplate) return;
    setPreviewing(true);

    // Add timeout to prevent indefinite loading state
    const timeoutId = setTimeout(() => {
      setPreviewing(false);
      setToast({ message: "Preview timeout. Silakan coba lagi.", type: "error" });
    }, 30000); // 30 second timeout

    try {
      const res = await apiFetch("/api/documents/preview", {
        method: "POST",
        body: JSON.stringify(buildDocumentPayload()),
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Preview gagal");
      }
      const nextUrl = URL.createObjectURL(await res.blob());
      setPreviewUrl(prev => {
        if (prev) URL.revokeObjectURL(prev);
        return nextUrl;
      });
      setStep(3);
    } catch (e: unknown) {
      clearTimeout(timeoutId);
      setToast({ message: e instanceof Error ? e.message : "Preview gagal", type: "error" });
    } finally {
      setPreviewing(false);
    }
  }

  async function handleGenerate() {
    if (!selectedTemplate) return;
    setGenerating(true);
    try {
      const res = await apiFetch("/api/documents/generate", {
        method: "POST",
        body: JSON.stringify(buildDocumentPayload()),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Generate gagal");
      }
      const data = await res.json();
      setGeneratedDoc({ id: data.document_id, file_url: data.file_url, template_name: data.template_name, display_filename: data.display_filename });
      setStep(4);
    } catch (e: unknown) {
      setToast({ message: e instanceof Error ? e.message : "Generate gagal", type: "error" });
    } finally { setGenerating(false); }
  }

  async function handleSendEmail() {
    if (!generatedDoc || !emailTo) return;
    setSendingEmail(true);
    try {
      const res = await apiFetch(`/api/documents/${generatedDoc.id}/email`, {
        method: "POST",
        body: JSON.stringify({ to_email: emailTo, subject: emailSubject || undefined }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Gagal kirim email");
      }
      setToast({ message: `Email terkirim ke ${emailTo}`, type: "success" });
      setEmailModal(false);
    } catch (e: unknown) {
      setToast({ message: e instanceof Error ? e.message : "Gagal kirim email", type: "error" });
    } finally { setSendingEmail(false); }
  }

  // Filtered lists for search
  const filteredLeads = useMemo(() => {
    const q = targetSearch.toLowerCase().trim();
    if (!q) return leads;
    return leads.filter(l =>
      (l.business_name || "").toLowerCase().includes(q) ||
      (l.phone_number || "").toLowerCase().includes(q) ||
      (l.product_interest || "").toLowerCase().includes(q)
    );
  }, [leads, targetSearch]);

  const filteredContacts = useMemo(() => {
    const q = targetSearch.toLowerCase().trim();
    if (!q) return contacts;
    return contacts.filter(c =>
      (c.business_name || "").toLowerCase().includes(q) ||
      (c.phone_number || "").toLowerCase().includes(q) ||
      (c.purchased_product || "").toLowerCase().includes(q)
    );
  }, [contacts, targetSearch]);

  const filteredProjects = useMemo(() => {
    const q = targetSearch.toLowerCase().trim();
    if (!q) return projects;
    return projects.filter(project =>
      (project.name || "").toLowerCase().includes(q) ||
      (project.service_type || "").toLowerCase().includes(q)
    );
  }, [projects, targetSearch]);

  const filteredProducts = useMemo(() => {
    const q = productSearch.toLowerCase().trim();
    if (!q) return products;
    return products.filter(p =>
      (p.name || "").toLowerCase().includes(q) ||
      (p.description || "").toLowerCase().includes(q)
    );
  }, [products, productSearch]);

  const klienCandidates = useMemo(() => {
    const q = klienSearch.toLowerCase().trim();
    const fromLeads = leads.map(l => ({ label: l.business_name, sub: l.product_interest || l.phone_number, onPick: () => pickLead(l) }));
    const fromContacts = contacts.map(c => ({ label: c.business_name, sub: c.purchased_product || c.phone_number, onPick: () => pickContact(c) }));
    const all = [...fromLeads, ...fromContacts];
    if (!q) return all.slice(0, 20);
    return all.filter(x => x.label.toLowerCase().includes(q) || x.sub.toLowerCase().includes(q)).slice(0, 20);
  }, [leads, contacts, klienSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (klienRef.current && !klienRef.current.contains(e.target as Node)) {
        setKlienDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Generate Dokumen</h1>
        <p className="text-sm text-gray-500 mt-1">Buat PDF dari template dalam beberapa langkah.</p>
      </div>

      {/* Stepper */}
      <TemplateStepper step={step} />

      {/* Step 0: Pick Template */}
      {step === 0 && (
        <TemplatePicker
          templates={templates}
          selectedTemplate={selectedTemplate}
          onSelect={selectTemplate}
          onNext={() => setStep(1)}
        />
      )}

      {/* Step 1: Pick Target */}
      {step === 1 && (
        <TargetPicker
          targetType={targetType}
          targetSearch={targetSearch}
          leads={filteredLeads}
          contacts={filteredContacts}
          projects={filteredProjects}
          selectedLead={selectedLead}
          selectedContact={selectedContact}
          selectedProject={selectedProject}
          onTargetTypeChange={t => { setTargetType(t); setSelectedLead(null); setSelectedContact(null); setSelectedProject(null); }}
          onSearchChange={setTargetSearch}
          onPickLead={pickLead}
          onPickContact={pickContact}
          onPickProject={pickProject}
        />
      )}

      {/* Step 2: Fill Variables */}
      {step === 2 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Isi Variabel</h2>
          <p className="text-xs text-gray-500">Identitas perusahaan, logo, dan tagline diambil otomatis dari Brand Kit.</p>
          {Object.keys(variables).length === 0 && <p className="text-sm text-gray-400">Template ini tidak punya variabel.</p>}
          <div className="space-y-4">
            {(() => {
              // Dedupe auto-number aliases such as nomor_invoice and no_invoice.
              const allKeys = Object.keys(variables);
              const usesAutoNumber = ["invoice", "receipt", "surat_penawaran"].includes(selectedTemplate?.type || "");
              const numberKeys = usesAutoNumber ? allKeys.filter(k => isInvoiceNumberKey(k)) : [];
              const primaryNumberKey = numberKeys[0] || null;
              const renderedKeys = new Set<string>();

              // Build dedup suppression set from DEDUP_PAIRS
              const suppressedKeys = new Set<string>();
              for (const [primary, secondary] of DEDUP_PAIRS) {
                if (allKeys.includes(primary) && allKeys.includes(secondary)) {
                  suppressedKeys.add(secondary);
                }
              }

              return Object.entries(variables).map(([key, val]) => {
                if (renderedKeys.has(key)) return null;
                // Skip duplicate document number aliases.
                if (numberKeys.includes(key) && key !== primaryNumberKey) return null;
                // Skip dedup-suppressed secondary keys.
                if (suppressedKeys.has(key)) return null;
                renderedKeys.add(key);

                const label = FIELD_LABELS[key.toLowerCase()] || key.replace(/_/g, " ");

                // Logo field — show image preview from brand kit
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

                // Final number is allocated by the backend when the document is generated.
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
                          <button
                            type="button"
                            onClick={() => { setShowSeqEditor(true); loadCurrentSequence(); }}
                            className="text-[11px] text-amber-600 hover:text-amber-700 font-semibold">
                            Atur nomor awal
                          </button>
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

                // Total — read-only, auto-calculated from line items
                if (isTotalKey(key)) {
                  if (selectedTemplate?.type === "invoice") return null;
                  return (
                    <div key={key}>
                      <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label} (otomatis)</label>
                      <input
                        type="text"
                        value={val}
                        readOnly
                        placeholder="Akan terisi otomatis dari line items"
                        className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-gray-50 dark:bg-neutral-800/50 text-amber-700 font-bold"
                      />
                    </div>
                  );
                }

                // Line item editor — card-based: row of inputs + description below
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
                              <input
                                type="text"
                                value={it.name}
                                placeholder="Nama item"
                                onChange={e => updateLineItem(key, it.id, { name: e.target.value })}
                                className="flex-1 px-2 py-1.5 text-xs border border-gray-200 dark:border-neutral-700 rounded bg-white dark:bg-neutral-900"
                              />
                              <button onClick={() => deleteLineItem(key, it.id)} className="text-gray-400 hover:text-red-500 shrink-0 p-1">
                                <Trash2 size={14} />
                              </button>
                            </div>
                            <div className="grid grid-cols-3 gap-2">
                              <div>
                                <label className="text-[10px] font-bold text-gray-400 uppercase">Qty</label>
                                <input
                                  type="number"
                                  min="1"
                                  value={it.qty}
                                  onChange={e => updateLineItem(key, it.id, { qty: Math.max(1, parseInt(e.target.value) || 1) })}
                                  className="w-full mt-0.5 px-2 py-1.5 text-xs border border-gray-200 dark:border-neutral-700 rounded bg-white dark:bg-neutral-900 text-center"
                                />
                              </div>
                              <div>
                                <label className="text-[10px] font-bold text-gray-400 uppercase">Harga Satuan</label>
                                <input
                                  type="number"
                                  min="0"
                                  value={it.price}
                                  onChange={e => updateLineItem(key, it.id, { price: Math.max(0, parseInt(e.target.value) || 0) })}
                                  className="w-full mt-0.5 px-2 py-1.5 text-xs border border-gray-200 dark:border-neutral-700 rounded bg-white dark:bg-neutral-900 text-right"
                                />
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
                              <textarea
                                value={it.description}
                                placeholder="Deskripsi paket / fitur..."
                                onChange={e => updateLineItem(key, it.id, { description: e.target.value })}
                                rows={2}
                                className="w-full mt-0.5 px-2 py-1.5 text-xs border border-gray-200 dark:border-neutral-700 rounded bg-white dark:bg-neutral-900 resize-y"
                              />
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
                        <button
                          type="button"
                          onClick={() => openProductPicker(key, "line_item")}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-amber-500 hover:bg-amber-600 text-white rounded-lg">
                          <Plus size={14} /> Tambah dari Paket
                        </button>
                        <button
                          type="button"
                          onClick={() => addEmptyLineItem(key)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border border-gray-200 dark:border-neutral-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-neutral-800">
                          <Plus size={14} /> Item Manual
                        </button>
                      </div>
                    </div>
                  );
                }

                // Read-only company info (from Brand Kit)
                if (isReadonlyCompanyKey(key)) {
                  return null;
                }

                // Rupiah-formatted field
                if (isRupiahKey(key)) {
                  return (
                    <div key={key}>
                      <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                      <input
                        type="text"
                        inputMode="numeric"
                        value={val}
                        onChange={e => setVariables(prev => ({ ...prev, [key]: toRupiahRaw(e.target.value) }))}
                        placeholder="Rp 0"
                        className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 font-semibold"
                      />
                      <p className="text-[11px] text-gray-400 mt-1">{FIELD_HINTS[key.toLowerCase()] || "Format Rupiah otomatis"}</p>
                    </div>
                  );
                }

                // Phone field
                if (isPhoneKey(key)) {
                  return (
                    <div key={key}>
                      <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                      <input
                        type="tel"
                        value={val}
                        onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                        placeholder="0812-3456-7890"
                        className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800"
                      />
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
                      <input
                        type="email"
                        value={val}
                        onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                        placeholder="klien@email.com"
                        className={`mt-1 w-full px-3 py-2 text-sm border rounded-lg bg-white dark:bg-neutral-800 ${valid ? "border-gray-200 dark:border-neutral-700" : "border-red-400"}`}
                      />
                      {!valid && <p className="text-[11px] text-red-500 mt-1">Format email tidak valid</p>}
                    </div>
                  );
                }

                // Klien field — searchable combobox from leads+contacts
                if (KLIEN_KEYS.includes(key.toLowerCase())) {
                  const templates_for_key = fieldTemplates[key] || loadFieldTemplates(key);
                  return (
                    <div key={key} ref={klienRef}>
                      <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                      <div className="relative mt-1">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                        <input
                          type="text"
                          value={klienDropdownOpen ? klienSearch : val}
                          onFocus={() => { setKlienSearch(val); setKlienDropdownOpen(true); }}
                          onChange={e => {
                            setKlienSearch(e.target.value);
                            setVariables(prev => ({ ...prev, [key]: e.target.value }));
                          }}
                          onBlur={() => setTimeout(() => setKlienDropdownOpen(false), 150)}
                          placeholder="Ketik atau cari dari leads/klien..."
                          className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800"
                        />
                        {klienDropdownOpen && klienCandidates.length > 0 && (
                          <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-700 rounded-xl shadow-lg max-h-52 overflow-y-auto">
                            {klienCandidates.map((c, i) => (
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

                // Payment method field — dropdown from active payment methods
                if (key.toLowerCase() === PAYMENT_METHOD_KEY) {
                  return (
                    <div key={key}>
                      <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                      <select
                        value={val}
                        onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                        className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800"
                      >
                        <option value="">— Pilih metode pembayaran —</option>
                        {paymentMethods.map(m => (
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

                // Layanan field — combobox (type or pick from products)
                if (isLayananKey(key)) {
                  const datalistId = `layanan-${key}`;
                  return (
                    <div key={key}>
                      <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                      <input
                        type="text"
                        list={datalistId}
                        value={val}
                        onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                        placeholder="Ketik manual atau pilih dari paket"
                        className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800"
                      />
                      <datalist id={datalistId}>
                        {products.map(p => <option key={p.id} value={p.name}>{formatRupiah(p.base_price)}</option>)}
                      </datalist>
                      <button type="button" onClick={() => openProductPicker(key, "single")}
                        className="mt-2 flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border border-amber-300 text-amber-700 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-950/20">
                        <Plus size={13} /> Pilih paket layanan
                      </button>
                      <p className="text-[11px] text-gray-400 mt-1">{FIELD_HINTS[key.toLowerCase()] || "Ketik atau pilih dari paket yang tersedia"}</p>
                    </div>
                  );
                }

                // Large text → textarea with saveable templates
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
                          {savedTpls.map((tpl, i) => (
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
                      <textarea
                        value={val}
                        onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                        rows={4}
                        placeholder={FIELD_HINTS[key.toLowerCase()] || `{{${key}}}`}
                        className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 resize-y"
                      />
                      {FIELD_HINTS[key.toLowerCase()] && <p className="text-[11px] text-gray-400 mt-1">{FIELD_HINTS[key.toLowerCase()]}</p>}
                    </div>
                  );
                }

                // Default: text input
                return (
                  <div key={key}>
                    <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                    <input
                      type="text"
                      value={val}
                      onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                      placeholder={FIELD_HINTS[key.toLowerCase()] || `{{${key}}}`}
                      className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800"
                    />
                    {FIELD_HINTS[key.toLowerCase()] && <p className="text-[11px] text-gray-400 mt-1">{FIELD_HINTS[key.toLowerCase()]}</p>}
                  </div>
                );
              });
            })()}
          </div>
          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(1)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-xl">
              <ChevronLeft size={16} /> Kembali
            </button>
            <button onClick={handlePreview} disabled={previewing}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl disabled:opacity-50">
              {previewing ? "Menyiapkan Preview..." : "Preview PDF"} <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Preview + Generate */}
      {step === 3 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Preview &amp; Generate</h2>
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{selectedTemplate?.name}{selectedProject ? ` · ${selectedProject.name}` : selectedLead ? ` · ${selectedLead.business_name}` : selectedContact ? ` · ${selectedContact.business_name}` : ""}</span>
            <button onClick={handlePreview} disabled={previewing}
              className="px-3 py-1.5 border border-gray-200 dark:border-neutral-700 rounded-lg font-semibold hover:bg-gray-50 dark:hover:bg-neutral-800 disabled:opacity-50">
              {previewing ? "Memuat..." : "Refresh Preview"}
            </button>
          </div>
          <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-neutral-700 bg-gray-100 dark:bg-neutral-800">
            {previewUrl ? (
              <iframe src={previewUrl} title="Preview PDF" className="w-full h-[72vh] bg-white" />
            ) : (
              <div className="flex h-80 items-center justify-center text-sm text-gray-400">Preview PDF belum tersedia.</div>
            )}
          </div>
          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(2)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-xl">
              <ChevronLeft size={16} /> Kembali
            </button>
            <button onClick={handleGenerate} disabled={generating}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl disabled:opacity-50">
              {generating ? "Generating..." : "Generate PDF"}
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Done */}
      {step === 4 && generatedDoc && (
        <div className="space-y-4 text-center">
          <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto">
            <Check size={28} className="text-green-600" />
          </div>
          <h2 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">PDF Berhasil Dibuat!</h2>
          <p className="text-sm text-gray-500">{generatedDoc.template_name}</p>
          <div className="flex gap-3 justify-center pt-2">
            <a href={`${API_BASE}/api/documents/${generatedDoc.id}/download`} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl">
              <Download size={16} /> Download PDF
            </a>
            <button onClick={() => setEmailModal(true)}
              className="flex items-center gap-2 px-5 py-2.5 border-2 border-gray-200 hover:border-gray-400 text-gray-700 dark:text-neutral-200 text-sm font-semibold rounded-xl">
              <Mail size={16} /> Kirim Email
            </button>
          </div>
          <button onClick={() => {
              if (previewUrl) URL.revokeObjectURL(previewUrl);
              setPreviewUrl(null);
              setStep(0);
              setSelectedTemplate(null);
              setSelectedLead(null);
              setSelectedContact(null);
              setSelectedProject(null);
              setVariables({});
              setLineItems({});
              setGeneratedDoc(null);
              setTargetType("empty");
              setTargetSearch("");
            }}
            className="text-xs text-gray-400 hover:text-gray-600 underline mt-2">
            Generate dokumen lain
          </button>
        </div>
      )}

      {/* Product Picker Modal */}
      {productPickerForKey && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-neutral-900 rounded-2xl p-6 w-full max-w-lg shadow-xl max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">Pilih dari Paket</h3>
                <p className="text-xs text-gray-400 mt-0.5">{productPickerMode === "single" ? "Klik paket untuk mengisi field layanan" : "Klik paket untuk menambah ke daftar item"}</p>
              </div>
              <button onClick={() => { setProductPickerForKey(null); setProductSearch(""); }} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <div className="relative mb-3">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={productSearch}
                onChange={e => setProductSearch(e.target.value)}
                placeholder="Cari nama paket..."
                autoFocus
                className="w-full pl-10 pr-3 py-2.5 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-800"
              />
            </div>
            <div className="flex-1 overflow-y-auto space-y-2">
              {filteredProducts.length === 0 && <p className="text-sm text-gray-400 text-center py-4">Tidak ada paket. Tambahkan di Master Produk dulu.</p>}
              {filteredProducts.map(p => (
                <button
                  key={p.id}
                  onClick={() => productPickerMode === "single"
                    ? pickProductForSingleField(productPickerForKey, p)
                    : addLineItemFromProduct(productPickerForKey, p)}
                  className="w-full text-left p-3 rounded-xl border border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300 transition-colors">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{p.name}</p>
                    <p className="text-sm font-bold text-amber-600">{formatRupiah(p.base_price)}</p>
                  </div>
                  {p.description && <p className="text-xs text-gray-500 mt-1 line-clamp-2">{p.description}</p>}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Sequence Editor Modal */}
      {showSeqEditor && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-neutral-900 rounded-2xl p-6 w-full max-w-sm shadow-xl">
            <h3 className="text-lg font-bold text-neutral-800 dark:text-neutral-100 mb-2">Atur Nomor Invoice Awal</h3>
            <p className="text-xs text-gray-500 mb-4">Nomor invoice berikutnya akan dimulai dari angka ini.</p>
            <input
              type="number"
              min="1"
              value={seqStartFrom}
              onChange={e => setSeqStartFrom(e.target.value)}
              placeholder="1"
              className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 font-mono"
            />
            <div className="flex gap-3 mt-4">
              <button onClick={() => setShowSeqEditor(false)} className="flex-1 py-2.5 rounded-xl border border-gray-200 text-sm font-semibold text-gray-600">Batal</button>
              <button onClick={saveSequence}
                className="flex-1 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold">
                Simpan
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Email Modal */}
      {emailModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-neutral-900 rounded-2xl p-6 w-full max-w-md shadow-xl">
            <h3 className="text-lg font-bold text-neutral-800 dark:text-neutral-100 mb-4">Kirim via Email</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Alamat Email</label>
                <input type="email" value={emailTo} onChange={e => setEmailTo(e.target.value)}
                  placeholder="klien@email.com"
                  className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" />
              </div>
              <div>
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Subject (opsional)</label>
                <input type="text" value={emailSubject} onChange={e => setEmailSubject(e.target.value)}
                  placeholder={`${generatedDoc?.template_name} dari Teman UMKM Kita`}
                  className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setEmailModal(false)} className="flex-1 py-2.5 rounded-xl border border-gray-200 text-sm font-semibold text-gray-600">Batal</button>
              <button onClick={handleSendEmail} disabled={sendingEmail || !emailTo}
                className="flex-1 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold disabled:opacity-50">
                {sendingEmail ? "Mengirim..." : "Kirim"}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
