"use client";

import { useState, useEffect, useMemo } from "react";
import { apiFetch } from "../../../../lib/api";
import { ChevronRight, ChevronLeft, Download, Mail, Check, Search, Plus, Trash2, X } from "lucide-react";
import Toast from "../../../../components/Toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DocTemplate { id: string; name: string; type: string; variables: string[]; }
interface Lead { id: number; business_name: string; phone_number: string; address: string | null; product_interest: string | null; }
interface Contact { id: number; business_name: string; owner_name: string | null; phone_number: string; purchased_product: string | null; }
interface Product { id: string; name: string; description: string | null; base_price: number; features: string[]; }
interface GeneratedDoc { id: string; file_url: string; template_name: string; display_filename?: string; }

interface LineItem {
  id: string;
  name: string;
  description: string;
  qty: number;
  price: number;
}

const STEPS = ["Pilih Template", "Pilih Target", "Isi Variabel", "Preview", "Selesai"];

const DATE_KEY_PATTERNS = ["tanggal", "due_date", "valid_until", "tanggal_mulai", "tanggal_akhir", "expired", "expiry"];
const INVOICE_NUMBER_KEYS = ["nomor_invoice", "no_invoice", "nomor"];
const LINE_ITEM_KEYS = ["items_rows", "items_table", "line_items", "items"];
const TOTAL_KEYS = ["total", "total_harga", "grand_total", "total_bayar", "total_amount", "jumlah_total", "total_tagihan"];
const LOGO_KEYS = ["logo", "logo_perusahaan", "company_logo"];
const LARGE_TEXT_PATTERNS = ["html", "body", "scope", "terms", "rows"];

function isDateKey(key: string): boolean {
  const k = key.toLowerCase();
  return DATE_KEY_PATTERNS.some(p => k === p || k.startsWith(p + "_") || k.endsWith("_" + p));
}

function isInvoiceNumberKey(key: string): boolean {
  return INVOICE_NUMBER_KEYS.includes(key.toLowerCase());
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

function formatRupiah(num: number): string {
  return "Rp " + new Intl.NumberFormat("id-ID").format(num);
}

function lineItemsToHtml(items: LineItem[]): string {
  if (items.length === 0) return "";
  const rows = items.map((item, i) => {
    const subtotal = item.qty * item.price;
    return `<tr><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb">${i + 1}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb">${item.name}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb">${item.description}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:center">${item.qty}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right">${formatRupiah(item.price)}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600">${formatRupiah(subtotal)}</td></tr>`;
  }).join("");
  const total = items.reduce((s, i) => s + i.qty * i.price, 0);
  return `<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#f3f4f6"><th style="padding:8px;text-align:left">No</th><th style="padding:8px;text-align:left">Item</th><th style="padding:8px;text-align:left">Deskripsi</th><th style="padding:8px;text-align:center">Qty</th><th style="padding:8px;text-align:right">Harga</th><th style="padding:8px;text-align:right">Subtotal</th></tr></thead><tbody>${rows}</tbody><tfoot><tr style="background:#fef3c7"><td colspan="5" style="padding:8px;text-align:right;font-weight:bold">Total</td><td style="padding:8px;text-align:right;font-weight:bold">${formatRupiah(total)}</td></tr></tfoot></table>`;
}

export default function DocumentNewPage() {
  const [step, setStep] = useState(0);
  const [templates, setTemplates] = useState<DocTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<DocTemplate | null>(null);
  const [targetType, setTargetType] = useState<"empty" | "lead" | "contact">("empty");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
  const [targetSearch, setTargetSearch] = useState("");
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [lineItems, setLineItems] = useState<Record<string, LineItem[]>>({});
  const [productPickerForKey, setProductPickerForKey] = useState<string | null>(null);
  const [productSearch, setProductSearch] = useState("");
  const [showSeqEditor, setShowSeqEditor] = useState(false);
  const [seqStartFrom, setSeqStartFrom] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generatedDoc, setGeneratedDoc] = useState<GeneratedDoc | null>(null);
  const [emailModal, setEmailModal] = useState(false);
  const [emailTo, setEmailTo] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  useEffect(() => {
    apiFetch("/api/document-templates").then(r => r.ok ? r.json() : []).then(setTemplates).catch(() => {});
    apiFetch("/api/leads").then(r => r.ok ? r.json() : []).then(setLeads).catch(() => {});
    apiFetch("/api/contacts").then(r => r.ok ? r.json() : []).then(setContacts).catch(() => {});
    apiFetch("/api/products?active_only=true").then(r => r.ok ? r.json() : []).then(setProducts).catch(() => {});
  }, []);

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
  }

  async function fetchAndApplyDefaults(template: DocTemplate, ttype: "lead" | "contact" | "empty", tid: number | null) {
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
          if (k in merged && merged[k] === "") merged[k] = v as string;
          else if (!(k in merged)) merged[k] = v as string;
        }
        return merged;
      });
    } catch { /* silent */ }
  }

  function pickLead(lead: Lead) {
    setSelectedLead(lead);
    setSelectedContact(null);
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
    setVariables(prev => ({
      ...prev,
      klien: contact.business_name,
      nama: contact.business_name,
      phone: contact.phone_number,
      layanan: contact.purchased_product || "",
    }));
    if (selectedTemplate) fetchAndApplyDefaults(selectedTemplate, "contact", contact.id);
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
        const ttype = selectedLead ? "lead" : selectedContact ? "contact" : "empty";
        const tid = selectedLead?.id ?? selectedContact?.id ?? null;
        await fetchAndApplyDefaults(selectedTemplate, ttype, tid);
      }
    } catch (e: unknown) {
      setToast({ message: e instanceof Error ? e.message : "Gagal simpan", type: "error" });
    }
  }

  async function handleGenerate() {
    if (!selectedTemplate) return;
    setGenerating(true);
    try {
      const ttype = selectedLead ? "lead" : selectedContact ? "contact" : null;
      const tid = selectedLead?.id ?? selectedContact?.id ?? null;
      const res = await apiFetch("/api/documents/generate", {
        method: "POST",
        body: JSON.stringify({
          template_id: selectedTemplate.id,
          target_type: ttype,
          target_id: tid !== null ? String(tid) : null,
          variables,
        }),
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

  const filteredProducts = useMemo(() => {
    const q = productSearch.toLowerCase().trim();
    if (!q) return products;
    return products.filter(p =>
      (p.name || "").toLowerCase().includes(q) ||
      (p.description || "").toLowerCase().includes(q)
    );
  }, [products, productSearch]);

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Generate Dokumen</h1>
        <p className="text-sm text-gray-500 mt-1">Buat PDF dari template dalam beberapa langkah.</p>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-1">
        {STEPS.map((s, i) => (
          <div key={i} className="flex items-center gap-1">
            <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold transition-colors ${i < step ? "bg-green-500 text-white" : i === step ? "bg-amber-500 text-white" : "bg-gray-200 dark:bg-neutral-700 text-gray-500"}`}>
              {i < step ? <Check size={12} /> : i + 1}
            </div>
            <span className={`text-xs font-medium hidden sm:block ${i === step ? "text-amber-600" : "text-gray-400"}`}>{s}</span>
            {i < STEPS.length - 1 && <div className="w-4 h-px bg-gray-200 dark:bg-neutral-700 mx-1" />}
          </div>
        ))}
      </div>

      {/* Step 0: Pick Template */}
      {step === 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Pilih Template</h2>
          {templates.length === 0 && <p className="text-sm text-gray-400">Belum ada template. Buat di halaman Templates dulu.</p>}
          {templates.map(t => (
            <button key={t.id} onClick={() => selectTemplate(t)}
              className={`w-full text-left p-4 rounded-xl border-2 transition-colors ${selectedTemplate?.id === t.id ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20" : "border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300"}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{t.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Variabel: {t.variables.join(", ") || "—"}</p>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 font-bold uppercase">{t.type}</span>
              </div>
            </button>
          ))}
          <div className="flex justify-end pt-2">
            <button onClick={() => setStep(1)} disabled={!selectedTemplate}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl disabled:opacity-50">
              Lanjut <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Step 1: Pick Target */}
      {step === 1 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Pilih Target (opsional)</h2>
          <div className="flex gap-2">
            <button onClick={() => { setTargetType("empty"); setSelectedLead(null); setSelectedContact(null); }}
              className={`flex-1 p-3 rounded-xl border-2 text-sm font-semibold transition-colors ${targetType === "empty" ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20 text-amber-700" : "border-[var(--border-default)] text-gray-600 hover:border-amber-300"}`}>
              Tanpa Target
            </button>
            <button onClick={() => setTargetType("lead")}
              className={`flex-1 p-3 rounded-xl border-2 text-sm font-semibold transition-colors ${targetType === "lead" ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20 text-amber-700" : "border-[var(--border-default)] text-gray-600 hover:border-amber-300"}`}>
              Dari Lead
            </button>
            <button onClick={() => setTargetType("contact")}
              className={`flex-1 p-3 rounded-xl border-2 text-sm font-semibold transition-colors ${targetType === "contact" ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20 text-amber-700" : "border-[var(--border-default)] text-gray-600 hover:border-amber-300"}`}>
              Dari Klien
            </button>
          </div>

          {(targetType === "lead" || targetType === "contact") && (
            <>
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={targetSearch}
                  onChange={e => setTargetSearch(e.target.value)}
                  placeholder={`Cari ${targetType === "lead" ? "lead" : "klien"} berdasarkan nama, telepon, atau layanan...`}
                  className="w-full pl-10 pr-3 py-2.5 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-800"
                />
              </div>

              {targetType === "lead" && (
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {filteredLeads.length === 0 && <p className="text-sm text-gray-400 text-center py-4">Tidak ada lead.</p>}
                  {filteredLeads.map(l => (
                    <button key={l.id} onClick={() => pickLead(l)}
                      className={`w-full text-left p-3 rounded-xl border transition-colors ${selectedLead?.id === l.id ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20" : "border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300"}`}>
                      <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{l.business_name}</p>
                      <p className="text-xs text-gray-500">{l.product_interest || "—"} · {l.phone_number}</p>
                    </button>
                  ))}
                </div>
              )}

              {targetType === "contact" && (
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {filteredContacts.length === 0 && <p className="text-sm text-gray-400 text-center py-4">Tidak ada klien.</p>}
                  {filteredContacts.map(c => (
                    <button key={c.id} onClick={() => pickContact(c)}
                      className={`w-full text-left p-3 rounded-xl border transition-colors ${selectedContact?.id === c.id ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20" : "border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300"}`}>
                      <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{c.business_name}</p>
                      <p className="text-xs text-gray-500">{c.purchased_product || "—"} · {c.phone_number}</p>
                    </button>
                  ))}
                </div>
              )}
            </>
          )}

          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(0)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-xl">
              <ChevronLeft size={16} /> Kembali
            </button>
            <button onClick={() => {
                if (selectedTemplate) {
                  const ttype = selectedLead ? "lead" : selectedContact ? "contact" : "empty";
                  const tid = selectedLead?.id ?? selectedContact?.id ?? null;
                  fetchAndApplyDefaults(selectedTemplate, ttype, tid);
                }
                setStep(2);
              }}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl">
              Lanjut <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Fill Variables */}
      {step === 2 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Isi Variabel</h2>
          {Object.keys(variables).length === 0 && <p className="text-sm text-gray-400">Template ini tidak punya variabel.</p>}
          <div className="space-y-4">
            {(() => {
              // Dedupe invoice keys: only show the first one as editable
              const allKeys = Object.keys(variables);
              const invoiceKeys = allKeys.filter(k => isInvoiceNumberKey(k));
              const primaryInvoiceKey = invoiceKeys[0] || null;
              const renderedKeys = new Set<string>();

              return Object.entries(variables).map(([key, val]) => {
                if (renderedKeys.has(key)) return null;
                // Skip duplicate invoice keys
                if (isInvoiceNumberKey(key) && key !== primaryInvoiceKey) return null;
                renderedKeys.add(key);

                const label = key.replace(/_/g, " ");

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

                // Invoice number with sequence editor + auto-sync to other invoice keys
                if (isInvoiceNumberKey(key)) {
                  return (
                    <div key={key}>
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Nomor Invoice</label>
                        <button
                          type="button"
                          onClick={() => { setShowSeqEditor(true); loadCurrentSequence(); }}
                          className="text-[11px] text-amber-600 hover:text-amber-700 font-semibold">
                          Atur nomor awal
                        </button>
                      </div>
                      <input
                        type="text"
                        value={val}
                        onChange={e => {
                          const newVal = e.target.value;
                          setVariables(prev => {
                            const updated = { ...prev };
                            for (const k of invoiceKeys) updated[k] = newVal;
                            return updated;
                          });
                        }}
                        placeholder={`{{${key}}}`}
                        className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 font-mono"
                      />
                    </div>
                  );
                }

                // Total — read-only, auto-calculated from line items
                if (isTotalKey(key)) {
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
                          onClick={() => setProductPickerForKey(key)}
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

                // Large text → textarea
                if (isLargeTextKey(key)) {
                  return (
                    <div key={key}>
                      <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{label}</label>
                      <textarea
                        value={val}
                        onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                        rows={4}
                        placeholder={`{{${key}}}`}
                        className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 resize-y"
                      />
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
                      placeholder={`{{${key}}}`}
                      className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800"
                    />
                  </div>
                );
              });
            })()}
          </div>
          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(1)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-xl">
              <ChevronLeft size={16} /> Kembali
            </button>
            <button onClick={() => setStep(3)}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl">
              Preview <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Preview + Generate */}
      {step === 3 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Preview &amp; Generate</h2>
          <div className="bg-gray-50 dark:bg-neutral-800 rounded-xl p-4 text-sm space-y-2">
            <p><span className="font-semibold">Template:</span> {selectedTemplate?.name}</p>
            {selectedLead && <p><span className="font-semibold">Target Lead:</span> {selectedLead.business_name}</p>}
            {selectedContact && <p><span className="font-semibold">Target Klien:</span> {selectedContact.business_name}</p>}
            <div>
              <p className="font-semibold mb-1">Variabel:</p>
              <ul className="text-xs space-y-1">
                {Object.entries(variables).map(([k, v]) => {
                  if (isLineItemKey(k)) {
                    const items = lineItems[k] || [];
                    return <li key={k} className="text-gray-600 dark:text-gray-400">{k}: <span className="font-medium">{items.length} item(s), total {formatRupiah(items.reduce((s, it) => s + it.qty * it.price, 0))}</span></li>;
                  }
                  return <li key={k} className="text-gray-600 dark:text-gray-400">{k}: <span className="font-medium">{v ? (v.length > 60 ? v.slice(0, 60) + "..." : v) : <em className="text-gray-400">kosong</em>}</span></li>;
                })}
              </ul>
            </div>
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
          <button onClick={() => { setStep(0); setSelectedTemplate(null); setSelectedLead(null); setSelectedContact(null); setVariables({}); setLineItems({}); setGeneratedDoc(null); setTargetType("empty"); setTargetSearch(""); }}
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
              <h3 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">Pilih dari Paket</h3>
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
                  onClick={() => addLineItemFromProduct(productPickerForKey, p)}
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
                  placeholder={`${generatedDoc?.template_name} dari Kantor Teman`}
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
