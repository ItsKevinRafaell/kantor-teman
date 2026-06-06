"use client";
import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { apiFetch } from "../lib/api";
import { formatRupiah } from "../utils/formatter";

export interface DocTemplate { id: string; name: string; type: string; variables: string[]; }
export interface Lead { id: number; business_name: string; phone_number: string; address: string | null; product_interest: string | null; }
export interface Contact { id: number; business_name: string; owner_name: string | null; phone_number: string; purchased_product: string | null; }
export interface Product { id: string; name: string; description: string | null; base_price: number; features: string[]; }
export interface Project { id: string; lead_id: number | null; name: string; nominal: number; start_date: string | null; end_date: string | null; service_type: string | null; contract_months: number | null; }
export interface GeneratedDoc { id: string; file_url: string; template_name: string; display_filename?: string; }
export interface LineItem { id: string; name: string; description: string; qty: number; price: number; }
export interface PaymentMethod { id: number; name: string; account_number: string; account_name: string; notes: string | null; is_active: boolean; }
export interface Toast { message: string; type: "success" | "error"; }

const LINE_ITEM_KEYS = ["items_rows", "items_table", "line_items", "items"];
const TOTAL_KEYS = ["total", "total_harga", "grand_total", "total_bayar", "total_amount", "jumlah_total", "total_tagihan"];
const INVOICE_NUMBER_KEYS = ["nomor_invoice", "no_invoice", "nomor"];

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  })[char] || char);
}

function lineItemsToHtml(items: LineItem[]): string {
  if (items.length === 0) return "";
  const rows = items.map((item, i) => {
    const subtotal = item.qty * item.price;
    const description = item.description
      ? `<div style="margin-top:3px;color:#6b7280;font-size:11px;line-height:1.45">${escapeHtml(item.description)}</div>`
      : "";
    return `<tr><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb"><strong>${i + 1}. ${escapeHtml(item.name)}</strong>${description}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:center">${item.qty}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right">${formatRupiah(item.price)}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600">${formatRupiah(subtotal)}</td></tr>`;
  }).join("");
  const total = items.reduce((s, i) => s + i.qty * i.price, 0);
  return `<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#f3f4f6"><th style="padding:8px;text-align:left">Layanan</th><th style="padding:8px;text-align:center">Jumlah</th><th style="padding:8px;text-align:right">Harga</th><th style="padding:8px;text-align:right">Total</th></tr></thead><tbody>${rows}</tbody><tfoot><tr style="background:#fef3c7"><td colspan="3" style="padding:8px;text-align:right;font-weight:bold">Total Tagihan</td><td style="padding:8px;text-align:right;font-weight:bold">${formatRupiah(total)}</td></tr></tfoot></table>`;
}

function syncTotalVariable(variables: Record<string, string>, items: LineItem[], setVariables: React.Dispatch<React.SetStateAction<Record<string, string>>>) {
  const total = items.reduce((s, it) => s + it.qty * it.price, 0);
  setVariables(prev => {
    const updated = { ...prev };
    for (const k of Object.keys(updated)) {
      if (TOTAL_KEYS.includes(k)) updated[k] = formatRupiah(total);
    }
    return updated;
  });
}

export function useDocumentGenerator() {
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
  const [toast, setToast] = useState<Toast | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [klienSearch, setKlienSearch] = useState("");
  const [klienDropdownOpen, setKlienDropdownOpen] = useState(false);
  const klienRef = useRef<HTMLDivElement>(null);

  // Load data
  useEffect(() => {
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

  // Cleanup preview URL
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  // Click outside handler for klien dropdown
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (klienRef.current && !klienRef.current.contains(e.target as Node)) {
        setKlienDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // --- Filtered lists ---
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
    return projects.filter(p =>
      (p.name || "").toLowerCase().includes(q) ||
      (p.service_type || "").toLowerCase().includes(q)
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

  // --- Template selection ---
  const selectTemplate = useCallback((t: DocTemplate) => {
    setSelectedTemplate(t);
    const vars: Record<string, string> = {};
    const items: Record<string, LineItem[]> = {};
    t.variables.forEach(v => {
      if (LINE_ITEM_KEYS.includes(v.toLowerCase())) { items[v] = []; vars[v] = ""; }
      else vars[v] = "";
    });
    setVariables(vars);
    setLineItems(items);
    fetchAndApplyDefaults(t, "empty", null);
  }, []);

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
          if (INVOICE_NUMBER_KEYS.includes(k.toLowerCase()) && ["invoice", "receipt", "surat_penawaran"].includes(template.type)) merged[k] = v as string;
          else if (k in merged && merged[k] === "") merged[k] = v as string;
          else if (!(k in merged)) merged[k] = v as string;
        }
        return merged;
      });
    } catch { /* silent */ }
  }

  // --- Target selection ---
  const pickLead = useCallback((lead: Lead) => {
    setSelectedLead(lead); setSelectedContact(null); setSelectedProject(null);
    setVariables(prev => ({ ...prev, klien: lead.business_name, nama: lead.business_name, alamat: lead.address || "", layanan: lead.product_interest || "", phone: lead.phone_number }));
    if (selectedTemplate) fetchAndApplyDefaults(selectedTemplate, "lead", lead.id);
  }, [selectedTemplate]);

  const pickContact = useCallback((contact: Contact) => {
    setSelectedContact(contact); setSelectedLead(null); setSelectedProject(null);
    setVariables(prev => ({ ...prev, klien: contact.business_name, nama: contact.business_name, phone: contact.phone_number, layanan: contact.purchased_product || "" }));
    if (selectedTemplate) fetchAndApplyDefaults(selectedTemplate, "contact", contact.id);
  }, [selectedTemplate]);

  const pickProject = useCallback((project: Project) => {
    const lead = leads.find(item => item.id === project.lead_id) || null;
    setSelectedProject(project); setSelectedLead(null); setSelectedContact(null);
    const formatDate = (d: string) => d ? new Date(d).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" }) : "";
    setVariables(prev => ({
      ...prev, klien: lead?.business_name || prev.klien || "", nama: lead?.business_name || prev.nama || "",
      alamat: lead?.address || prev.alamat || "", phone: lead?.phone_number || prev.phone || "",
      layanan: project.name || project.service_type || prev.layanan || "",
      nilai_kontrak: project.nominal ? formatRupiah(project.nominal) : prev.nilai_kontrak || "",
      tanggal_mulai: formatDate(project.start_date || ""), tanggal_akhir: formatDate(project.end_date || ""),
      durasi: project.contract_months ? `${project.contract_months} bulan` : prev.durasi || "",
    }));
    if (selectedTemplate) fetchAndApplyDefaults(selectedTemplate, "project", project.id);
  }, [leads, selectedTemplate]);

  // --- Line item operations ---
  const addLineItemFromProduct = useCallback((key: string, product: Product) => {
    const newItem: LineItem = { id: crypto.randomUUID(), name: product.name, description: product.description || (product.features?.join(", ") || ""), qty: 1, price: product.base_price };
    setLineItems(prev => {
      const items = [...(prev[key] || []), newItem];
      setVariables(v => ({ ...v, [key]: lineItemsToHtml(items) }));
      syncTotalVariable(variables, items, setVariables);
      return { ...prev, [key]: items };
    });
    setProductPickerForKey(null); setProductSearch("");
  }, [variables]);

  const pickProductForSingleField = useCallback((key: string, product: Product) => {
    setVariables(prev => ({ ...prev, [key]: product.name, scope: key === "layanan" && !prev.scope ? (product.description || product.features?.join("\n") || "") : prev.scope }));
    setProductPickerForKey(null); setProductSearch("");
  }, []);

  // --- Invoice sequence ---
  async function loadCurrentSequence() {
    try { const res = await apiFetch("/api/documents/invoice-sequence"); if (res.ok) { const data = await res.json(); setSeqStartFrom(String(data.next_seq)); } } catch {}
  }

  async function saveSequence() {
    const start = parseInt(seqStartFrom);
    if (!start || start < 1) { setToast({ message: "Nomor awal harus angka >= 1", type: "error" }); return; }
    try {
      const res = await apiFetch("/api/documents/invoice-sequence", { method: "PUT", body: JSON.stringify({ start_from: start, template_type: "invoice" }) });
      if (!res.ok) throw new Error("Gagal simpan");
      setToast({ message: `Nomor invoice berikutnya: ${start}`, type: "success" });
      setShowSeqEditor(false);
      if (selectedTemplate) { const ttype = selectedProject ? "project" : selectedLead ? "lead" : selectedContact ? "contact" : "empty"; await fetchAndApplyDefaults(selectedTemplate, ttype, selectedProject?.id ?? selectedLead?.id ?? selectedContact?.id ?? null); }
    } catch (e: unknown) { setToast({ message: e instanceof Error ? e.message : "Gagal simpan", type: "error" }); }
  }

  // --- Document operations ---
  function buildDocumentPayload() {
    const ttype = selectedProject ? "project" : selectedLead ? "lead" : selectedContact ? "contact" : null;
    const tid = selectedProject?.id ?? selectedLead?.id ?? selectedContact?.id ?? null;
    return { template_id: selectedTemplate?.id, target_type: ttype, target_id: tid !== null ? String(tid) : null, variables };
  }

  async function handlePreview() {
    if (!selectedTemplate) return;
    setPreviewing(true);
    const timeoutId = setTimeout(() => { setPreviewing(false); setToast({ message: "Preview timeout. Silakan coba lagi.", type: "error" }); }, 30000);
    try {
      const res = await apiFetch("/api/documents/preview", { method: "POST", body: JSON.stringify(buildDocumentPayload()) });
      clearTimeout(timeoutId);
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || "Preview gagal"); }
      const blob = await res.blob();
      const reader = new FileReader();
      const dataUrl: string = await new Promise((resolve) => {
        reader.onloadend = () => resolve(reader.result as string);
        reader.readAsDataURL(blob);
      });
      setPreviewUrl(prev => { if (prev && prev.startsWith('blob:')) URL.revokeObjectURL(prev); return dataUrl; });
      setStep(3);
    } catch (e: unknown) { clearTimeout(timeoutId); setToast({ message: e instanceof Error ? e.message : "Preview gagal", type: "error" }); }
    finally { setPreviewing(false); }
  }

  async function handleGenerate() {
    if (!selectedTemplate) return;
    setGenerating(true);
    try {
      const res = await apiFetch("/api/documents/generate", { method: "POST", body: JSON.stringify(buildDocumentPayload()) });
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || "Generate gagal"); }
      const data = await res.json();
      setGeneratedDoc({ id: data.document_id, file_url: data.file_url, template_name: data.template_name, display_filename: data.display_filename });
      setStep(4);
    } catch (e: unknown) { setToast({ message: e instanceof Error ? e.message : "Generate gagal", type: "error" }); }
    finally { setGenerating(false); }
  }

  async function handleSendEmail() {
    if (!generatedDoc || !emailTo) return;
    setSendingEmail(true);
    try {
      const res = await apiFetch(`/api/documents/${generatedDoc.id}/email`, { method: "POST", body: JSON.stringify({ to_email: emailTo, subject: emailSubject || undefined }) });
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || "Gagal kirim email"); }
      setToast({ message: `Email terkirim ke ${emailTo}`, type: "success" });
      setEmailModal(false);
    } catch (e: unknown) { setToast({ message: e instanceof Error ? e.message : "Gagal kirim email", type: "error" }); }
    finally { setSendingEmail(false); }
  }

  return {
    // State
    step, setStep, templates, selectedTemplate, targetType, setTargetType,
    leads, contacts, products, projects,
    selectedLead, selectedContact, selectedProject,
    targetSearch, setTargetSearch,
    variables, setVariables, lineItems, setLineItems,
    productPickerForKey, setProductPickerForKey, productPickerMode, setProductPickerMode,
    productSearch, setProductSearch,
    showSeqEditor, setShowSeqEditor, seqStartFrom, setSeqStartFrom,
    generating, previewing, previewUrl, setPreviewUrl,
    generatedDoc, setGeneratedDoc,
    emailModal, setEmailModal, emailTo, setEmailTo, emailSubject, setEmailSubject, sendingEmail,
    toast, setToast, paymentMethods,
    klienSearch, setKlienSearch, klienDropdownOpen, setKlienDropdownOpen, klienRef,
    // Filtered
    filteredLeads, filteredContacts, filteredProjects, filteredProducts, klienCandidates,
    // Actions
    selectTemplate, fetchAndApplyDefaults, pickLead, pickContact, pickProject,
    addLineItemFromProduct, pickProductForSingleField,
    loadCurrentSequence, saveSequence, buildDocumentPayload,
    handlePreview, handleGenerate, handleSendEmail,
  };
}
