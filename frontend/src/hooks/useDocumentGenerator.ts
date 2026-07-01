"use client";
import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { apiFetch } from "../lib/api";
import { formatRupiah } from "../utils/formatter";

export interface DocTemplate { id: string; name: string; type: string; variables: string[]; }
export interface Lead { id: number; business_name: string; phone_number: string; address: string | null; product_interest: string | null; }
export interface Contact { id: number; business_name: string; owner_name: string | null; phone_number: string; purchased_product: string | null; }
export interface Product { id: string; name: string; description: string | null; base_price: number; features: string[]; }
export interface Project { id: string; lead_id: number | null; name: string; nominal: number; start_date: string | null; end_date: string | null; service_type: string | null; contract_months: number | null; }
export interface GeneratedDoc { id: string; file_url: string; template_name: string; display_filename?: string; is_edited?: boolean; }
export interface LineItem { id: string; name: string; description: string; qty: number; price: number; }
export interface PaymentMethod { id: number; name: string; account_number: string; account_name: string; notes: string | null; is_active: boolean; }
export interface Toast { message: string; type: "success" | "error"; }
export interface Draft {
  id: string; template_id: string | null; template_name: string | null;
  target_type: string | null; target_id: string | null;
  variables_json: Record<string, string>; line_items_json?: Record<string, LineItem[]>;
  created_at: string; updated_at: string | null;
}
export interface DocumentVersion {
  id: string; version_number: number; variables_json: Record<string, string>;
  html_content: string | null; change_summary: string; created_at: string; created_by: string | null;
}

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
    return `<tr><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb"><strong>${escapeHtml(item.name)}</strong>${description}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:center">${item.qty}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right">${formatRupiah(item.price)}</td><td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600">${formatRupiah(subtotal)}</td></tr>`;
  }).join("");
  const total = items.reduce((s, i) => s + i.qty * i.price, 0);
  return `<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#f3f4f6"><th style="padding:8px;text-align:left">Layanan</th><th style="padding:8px;text-align:center">Jumlah</th><th style="padding:8px;text-align:right">Harga</th><th style="padding:8px;text-align:right">Total</th></tr></thead><tbody>${rows}</tbody><tfoot><tr style="background:#fef3c7"><td colspan="3" style="padding:8px;text-align:right;font-weight:bold">Total Tagihan</td><td style="padding:8px;text-align:right;font-weight:bold">${formatRupiah(total)}</td></tr></tfoot></table>`;
}

function parseRupiah(value: string): number {
  const cleaned = value.replace(/[^0-9]/g, "");
  const parsed = parseInt(cleaned, 10);
  return isNaN(parsed) ? 0 : parsed;
}

function parseLineItemsFromHtml(html: string): LineItem[] {
  if (!html || !html.includes("<tr")) return [];
  const items: LineItem[] = [];
  const rowRegex = /<tr[^>]*>([\s\S]*?)<\/tr>/g;
  let match;
  while ((match = rowRegex.exec(html)) !== null) {
    const rowHtml = match[1];
    // Skip header and footer rows
    if (rowHtml.includes("<th") || rowHtml.includes("Total Tagihan") || rowHtml.includes("<tfoot")) continue;
    // Parse first <td> for name and description
    const nameMatch = rowHtml.match(/<strong[^>]*>([\s\S]*?)<\/strong>/);
    const descMatch = rowHtml.match(/<div[^>]*>([\s\S]*?)<\/div>/);
    // Parse qty (second td with text-align:center)
    const qtyMatch = rowHtml.match(/text-align:center[^>]*>(\d+)/);
    // Parse price (third td with text-align:right)
    const priceMatches = Array.from(rowHtml.matchAll(/text-align:right[^>]*>([\s\S]*?)</g));
    if (nameMatch) {
      const name = nameMatch[1].trim();
      const description = descMatch ? descMatch[1].replace(/<[^>]*>/g, "").trim() : "";
      const qty = qtyMatch ? parseInt(qtyMatch[1], 10) : 1;
      const price = priceMatches.length >= 1 ? parseRupiah(priceMatches[0][1]) : 0;
      if (name) items.push({ id: `item-${items.length}`, name, description, qty, price });
    }
  }
  return items;
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
  const [scopeTemplates, setScopeTemplates] = useState<Array<{service_type: string; name: string; scope: string}>>([]);
  const [klienSearch, setKlienSearch] = useState("");
  const [klienDropdownOpen, setKlienDropdownOpen] = useState(false);
  const klienRef = useRef<HTMLDivElement>(null);

  // ── Draft auto-save refs (avoid stale closures) ──
  const draftStateRef = useRef({
    selectedTemplate: null as DocTemplate | null,
    step: 0,
    selectedProject: null as Project | null,
    selectedLead: null as Lead | null,
    selectedContact: null as Contact | null,
    variables: {} as Record<string, string>,
    lineItems: {} as Record<string, LineItem[]>,
  });

  // Keep refs in sync
  useEffect(() => {
    draftStateRef.current.selectedTemplate = selectedTemplate;
    draftStateRef.current.step = step;
    draftStateRef.current.selectedProject = selectedProject;
    draftStateRef.current.selectedLead = selectedLead;
    draftStateRef.current.selectedContact = selectedContact;
    draftStateRef.current.variables = variables;
    draftStateRef.current.lineItems = lineItems;
  });

  // ── Draft state ──
  const [draftId, setDraftId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [showDraftLoader, setShowDraftLoader] = useState(false);
  const [draftSaving, setDraftSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const autoSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasUnsavedChangesRef = useRef(false);
  const saveDraftRef = useRef<(() => Promise<void>) | null>(null);

  // ── Version history state ──
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [showVersions, setShowVersions] = useState(false);
  const [versionsLoading, setVersionsLoading] = useState(false);

  // ── Edit mode ──
  const [editDocId, setEditDocId] = useState<string | null>(null);

  // Load data
  useEffect(() => {
    async function loadData() {
      try { const r = await apiFetch("/api/document-templates"); if (r.ok) setTemplates(await r.json()); } catch {}
      try { const r = await apiFetch("/api/leads"); if (r.ok) setLeads(await r.json()); } catch {}
      try { const r = await apiFetch("/api/contacts"); if (r.ok) setContacts(await r.json()); } catch {}
      try { const r = await apiFetch("/api/products?active_only=true"); if (r.ok) setProducts(await r.json()); } catch {}
      try { const r = await apiFetch("/api/projects"); if (r.ok) setProjects(await r.json()); } catch {}
      try { const r = await apiFetch("/api/finance/payment-methods"); if (r.ok) { const d: PaymentMethod[] = await r.json(); setPaymentMethods(d.filter(m => m.is_active)); } } catch {}
      try { const r = await apiFetch("/api/document-scope-templates"); if (r.ok) { setScopeTemplates(await r.json()); } } catch {}
    }
    loadData();
  }, []);

  // Load drafts on mount
  useEffect(() => {
    async function loadDrafts() {
      try {
        const r = await apiFetch("/api/document-drafts");
        if (r.ok) {
          const data: Draft[] = await r.json();
          setDrafts(data);
          if (data.length > 0) setShowDraftLoader(true);
        }
      } catch {}
    }
    loadDrafts();
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

  // ── Draft auto-save ──
  async function saveDraftFn() {
    const ctx = draftStateRef.current;
    // SKIP auto-save in edit mode
    if (editDocId) return;
    if (!ctx.selectedTemplate || ctx.step < 1 || ctx.step > 2) return;
    setDraftSaving(true);
    const ttype = ctx.selectedProject ? "project" : ctx.selectedLead ? "lead" : ctx.selectedContact ? "contact" : "empty";
    const tid = ctx.selectedProject?.id ?? ctx.selectedLead?.id ?? ctx.selectedContact?.id ?? null;
    try {
      const liJson: Record<string, unknown> = {};
      for (const [key, items] of Object.entries(ctx.lineItems)) {
        liJson[key] = items.map(it => ({ id: it.id, name: it.name, description: it.description, qty: it.qty, price: it.price }));
      }
      const body = {
        id: draftId || undefined,
        template_id: ctx.selectedTemplate.id,
        template_name: ctx.selectedTemplate.name,
        target_type: ttype !== "empty" ? ttype : null,
        target_id: tid,
        variables_json: ctx.variables,
        line_items_json: Object.keys(liJson).length > 0 ? liJson : null,
      };
      const res = await apiFetch("/api/document-drafts", { method: "POST", body: JSON.stringify(body) });
      if (!res.ok) {
        const errText = await res.text();
        setToast({ message: `Gagal simpan draft: ${res.status}`, type: "error" });
      }
      if (res.ok) {
        const data = await res.json();
        setDraftId(data.id);
        setLastSaved(new Date());
        hasUnsavedChangesRef.current = false;
        // Update draft list from POST response (no extra GET call)
        setDrafts(prev => {
          const idx = prev.findIndex(d => d.id === data.id);
          const entry = { ...data, line_items_json: data.line_items_json || {} };
          if (idx >= 0) { const next = [...prev]; next[idx] = entry; return next; }
          return [entry, ...prev];
        });
      }
    } catch (e: unknown) {
      setToast({ message: `Gagal simpan draft: ${e instanceof Error ? e.message : 'Unknown'}`, type: "error" });
    }
    finally { setDraftSaving(false); }
  }

  // Keep ref pointing to latest saveDraftFn
  saveDraftRef.current = saveDraftFn;

  // Stable markUnsaved — always calls latest saveDraftFn via ref
  const markUnsaved = useCallback(() => {
    hasUnsavedChangesRef.current = true;
    if (autoSaveTimerRef.current) clearTimeout(autoSaveTimerRef.current);
    autoSaveTimerRef.current = setTimeout(() => {
      saveDraftRef.current?.();
    }, 5000);
  }, []);

  async function loadDraft(draft: Draft) {
    setSelectedTemplate({ id: draft.template_id!, name: draft.template_name || "", type: "", variables: [] });
    setVariables(draft.variables_json || {});
    if (draft.line_items_json) {
      setLineItems(draft.line_items_json);
    } else {
      // Fallback: parse line items from HTML in variables (for backward compat)
      const items: Record<string, LineItem[]> = {};
      for (const key of LINE_ITEM_KEYS) {
        if (draft.variables_json?.[key]) {
          const parsed = parseLineItemsFromHtml(draft.variables_json[key]);
          if (parsed.length > 0) items[key] = parsed;
        }
      }
      if (Object.keys(items).length > 0) setLineItems(items);
    }
    setDraftId(draft.id);
    setShowDraftLoader(false);
    setStep(2);
    setToast({ message: "Draft dimuat", type: "success" });
  }

  async function deleteDraft(draftIdToDelete: string) {
    try { await apiFetch(`/api/document-drafts/${draftIdToDelete}`, { method: "DELETE" }); } catch {}
    setDrafts(prev => prev.filter(d => d.id !== draftIdToDelete));
    if (draftId === draftIdToDelete) setDraftId(null);
  }

  async function deleteCurrentDraft() {
    if (draftId) {
      await deleteDraft(draftId);
    }
  }

  // ── Version history ──
  async function loadVersions(docId: string) {
    setVersionsLoading(true);
    try {
      const r = await apiFetch(`/api/documents/generated/${docId}/versions`);
      if (r.ok) setVersions(await r.json());
    } catch {}
    finally { setVersionsLoading(false); }
  }

  async function rollbackVersion(docId: string, versionId: string) {
    const res = await apiFetch(`/api/documents/generated/${docId}/versions/${versionId}/rollback`, { method: "POST" });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail || "Gagal rollback");
    }
    // Refresh versions list
    await loadVersions(docId);
  }

  // ── Edit document ──
  async function editDocument(docId: string, updatedVariables: Record<string, string>, changeSummary: string) {
    const res = await apiFetch(`/api/documents/generated/${docId}/edit`, {
      method: "POST",
      body: JSON.stringify({ variables: updatedVariables, change_summary: changeSummary }),
    });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail || "Gagal edit dokumen");
    }
    return await res.json();
  }

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
    markUnsaved();
    if (selectedTemplate) fetchAndApplyDefaults(selectedTemplate, "lead", lead.id);
  }, [selectedTemplate]);

  const pickContact = useCallback((contact: Contact) => {
    setSelectedContact(contact); setSelectedLead(null); setSelectedProject(null);
    setVariables(prev => ({ ...prev, klien: contact.business_name, nama: contact.business_name, phone: contact.phone_number, layanan: contact.purchased_product || "" }));
    markUnsaved();
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
    markUnsaved();
    if (selectedTemplate) fetchAndApplyDefaults(selectedTemplate, "project", project.id);
  }, [leads, selectedTemplate]);

  // --- Line item operations ---
  const addLineItemFromProduct = useCallback((key: string, product: Product) => {
    const description = product.features?.length
      ? product.features.join("\n")
      : (product.description || "");
    const newItem: LineItem = { id: crypto.randomUUID(), name: product.name, description, qty: 1, price: product.base_price };
    setLineItems(prev => {
      const items = [...(prev[key] || []), newItem];
      setVariables(v => ({ ...v, [key]: lineItemsToHtml(items) }));
      syncTotalVariable(variables, items, setVariables);
      return { ...prev, [key]: items };
    });
    markUnsaved();
    setProductPickerForKey(null); setProductSearch("");
  }, [variables]);

  const pickProductForSingleField = useCallback((key: string, product: Product) => {
    const scopeValue = product.features?.length
      ? product.features.join("\n")
      : (product.description || "");
    setVariables(prev => ({ ...prev, [key]: product.name, scope: key === "layanan" && !prev.scope ? scopeValue : prev.scope }));
    markUnsaved();
    setProductPickerForKey(null); setProductSearch("");
  }, []);

  // --- Document sequence (supports all template types) ---
  async function loadCurrentSequence() {
    if (!selectedTemplate) return;
    const templateType = selectedTemplate.type || "invoice";
    try {
      const res = await apiFetch(`/api/documents/invoice-sequence?template_type=${templateType}`);
      if (res.ok) {
        const data = await res.json();
        setSeqStartFrom(String(data.next_seq));
      }
    } catch {}
  }

  async function saveSequence() {
    if (!selectedTemplate) return;
    const start = parseInt(seqStartFrom);
    if (!start || start < 1) { setToast({ message: "Nomor awal harus angka >= 1", type: "error" }); return; }
    const templateType = selectedTemplate.type || "invoice";
    try {
      const res = await apiFetch("/api/documents/invoice-sequence", { method: "PUT", body: JSON.stringify({ start_from: start, template_type: templateType }) });
      if (!res.ok) throw new Error("Gagal simpan");
      const docTypeName = templateType.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
      setToast({ message: `Nomor ${docTypeName} berikutnya: ${start}`, type: "success" });
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
      // Edit mode: update existing document instead of creating new
      if (editDocId) {
        // Merge defaults before sending edit to ensure all template placeholders are filled
        try {
          const ttype = selectedProject ? "project" : selectedLead ? "lead" : selectedContact ? "contact" : "empty";
          const tid = selectedProject?.id ?? selectedLead?.id ?? selectedContact?.id ?? null;
          const defParams = new URLSearchParams();
          if (ttype !== "empty") defParams.set("target_type", ttype);
          if (tid !== null) defParams.set("target_id", String(tid));
          const defRes = await apiFetch(`/api/document-templates/${selectedTemplate.id}/defaults?${defParams}`);
          if (defRes.ok) {
            const defData = await defRes.json();
            const defaults = defData.defaults || {};
            // Merge: user values override defaults
            const merged = { ...defaults, ...variables };
            const res = await apiFetch(`/api/documents/generated/${editDocId}/edit`, {
              method: "POST",
              body: JSON.stringify({ variables: merged, change_summary: "Edit via form generator" }),
            });
            if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || "Edit gagal"); }
            const data = await res.json();
            setGeneratedDoc({ id: data.id, file_url: data.file_url, template_name: selectedTemplate.name, display_filename: selectedTemplate.name });
            setEditDocId(null);
            setStep(4);
            await deleteCurrentDraft();
            return;
          }
        } catch (e) { /* fallback to raw variables */ }
        // Fallback: send variables as-is if defaults fetch fails
        const res = await apiFetch(`/api/documents/generated/${editDocId}/edit`, {
          method: "POST",
          body: JSON.stringify({ variables, change_summary: "Edit via form generator" }),
        });
        if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || "Edit gagal"); }
        const data = await res.json();
        setGeneratedDoc({ id: data.id, file_url: data.file_url, template_name: selectedTemplate.name, display_filename: selectedTemplate.name });
        setEditDocId(null);
        setStep(4);
        await deleteCurrentDraft();
        return;
      }

      // Normal mode: create new document
      const res = await apiFetch("/api/documents/generate", { method: "POST", body: JSON.stringify(buildDocumentPayload()) });
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || "Generate gagal"); }
      const data = await res.json();
      setGeneratedDoc({ id: data.document_id, file_url: data.file_url, template_name: data.template_name, display_filename: data.display_filename });
      setStep(4);
      // Clean up current draft after successful generation
      await deleteCurrentDraft();
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

  // Wrap setVariables to mark unsaved changes
  const setVariablesAndMark = useCallback((updater: React.SetStateAction<Record<string, string>>) => {
    setVariables(updater);
    if (step >= 1 && step <= 2) markUnsaved();
  }, [step]);

  const setLineItemsAndMark = useCallback((updater: React.SetStateAction<Record<string, LineItem[]>>) => {
    setLineItems(updater);
    if (step >= 1 && step <= 2) markUnsaved();
  }, [step]);

  return {
    // State
    step, setStep, templates, selectedTemplate, setSelectedTemplate, targetType, setTargetType,
    leads, contacts, products, projects,
    selectedLead, selectedContact, selectedProject,
    targetSearch, setTargetSearch,
    variables, setVariables: setVariablesAndMark, lineItems, setLineItems: setLineItemsAndMark,
    productPickerForKey, setProductPickerForKey, productPickerMode, setProductPickerMode,
    productSearch, setProductSearch,
    showSeqEditor, setShowSeqEditor, seqStartFrom, setSeqStartFrom,
    generating, previewing, previewUrl, setPreviewUrl,
    generatedDoc, setGeneratedDoc,
    emailModal, setEmailModal, emailTo, setEmailTo, emailSubject, setEmailSubject, sendingEmail,
    toast, setToast, paymentMethods, scopeTemplates,
    klienSearch, setKlienSearch, klienDropdownOpen, setKlienDropdownOpen, klienRef,
    // Edit mode
    editDocId, setEditDocId,
    // Filtered
    filteredLeads, filteredContacts, filteredProjects, filteredProducts, klienCandidates,
    // Actions
    selectTemplate, fetchAndApplyDefaults, pickLead, pickContact, pickProject,
    addLineItemFromProduct, pickProductForSingleField,
    loadCurrentSequence, saveSequence, buildDocumentPayload,
    handlePreview, handleGenerate, handleSendEmail,
    // Draft
    draftId, drafts, showDraftLoader, setShowDraftLoader, draftSaving, lastSaved,
    loadDraft, deleteDraft,
    // Version history
    versions, showVersions, setShowVersions, versionsLoading,
    loadVersions, rollbackVersion, editDocument,
  };
}
