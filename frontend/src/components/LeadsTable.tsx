"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "../lib/api";
import StarRating from "./StarRating";
import { getScoreLabel, getScoreColor, getScoreIcon } from "../lib/leadScore";
import { Search, Download, Plus, Pencil, Trash2 } from "lucide-react";

import Modal from "./Modal";
import Toast from "./Toast";
import Pagination from "./Pagination";

const STATUSES = ["Scraped", "Contacted", "Replied", "Closed/Lost", "Closed/Client"] as const;
type Status = (typeof STATUSES)[number];

const STATUS_COLORS: Record<Status, string> = {
  Scraped: "bg-gray-100 text-gray-700",
  Contacted: "bg-blue-100 text-blue-700",
  Replied: "bg-yellow-100 text-yellow-700",
  "Closed/Lost": "bg-green-100 text-green-700",
  "Closed/Client": "bg-amber-100 text-amber-700",
};

interface Lead {
  id: number;
  business_name: string;
  phone_number: string;
  address: string | null;
  original_url: string | null;
  status: Status;
  product_interest: string | null;
  batch_name: string | null;
  rating: number;
  is_archived: boolean;
  deleted_at: string | null;
  lead_score: number;
  is_ghost_viewer: boolean;
  website_url?: string | null;
  google_rating?: number | null;
  review_count?: number | null;
}

const DEFAULT_TEMPLATE =
  "Halo {{business_name}}, saya baru saja menjalankan audit digital gratis untuk bisnis Anda dan hasilnya cukup mengkhawatirkan — ada beberapa masalah kritis yang membuat calon pelanggan Anda lari ke kompetitor setiap harinya.\n\nSaya sudah buatkan laporan lengkapnya di sini:\n{{proposal_link}}\n\nLaporan ini hanya berlaku 24 jam karena slot optimasi wilayah Anda terbatas. Setelah itu harga kembali normal.\n\nBisa saya jelaskan lebih detail, Pak?";

export default function LeadsTable({ initialBatch }: { initialBatch?: string }) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<Status | "">("");
  const [filterBatch, setFilterBatch] = useState(initialBatch || "");
  const [filterScore, setFilterScore] = useState<"hot" | "warm" | "cold" | "">("");
  const [recalculating, setRecalculating] = useState(false);
  const [batches, setBatches] = useState<string[]>([]);
  const [updating, setUpdating] = useState<number | null>(null);
  const [fallbackTemplate, setFallbackTemplate] = useState(DEFAULT_TEMPLATE);
  const [hasTemplates, setHasTemplates] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Modal state
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; id: number | null; name: string }>({ open: false, id: null, name: "" });
  const [deleteBatchModal, setDeleteBatchModal] = useState(false);
  const [convertModal, setConvertModal] = useState<{ open: boolean; lead: Lead | null }>({ open: false, lead: null });

  // Blast panel
  const [blastOpen, setBlastOpen] = useState(false);
  const [blastBatch, setBlastBatch] = useState("");
  const [blastCategoryId, setBlastCategoryId] = useState("");
  const [blastMinRating, setBlastMinRating] = useState(0);
  const [blasting, setBlasting] = useState(false);
  const [blastTemplateMode, setBlastTemplateMode] = useState<"rotate" | "specific">("rotate");
  const [blastTemplateId, setBlastTemplateId] = useState("");
  const [blastTemplates, setBlastTemplates] = useState<{ id: string; name: string; content: string; category_id: string | null }[]>([]);
  const [blastCategories, setBlastCategories] = useState<{ id: string; name: string }[]>([]);
  const [blastSendMode, setBlastSendMode] = useState<"instant" | "scheduled">("instant");
  const [blastScheduledFor, setBlastScheduledFor] = useState("");

  // Follow-up templates
  const [followUpTemplates, setFollowUpTemplates] = useState<{ id: string; name: string; content: string; category_id: string | null }[]>([]);

  // Follow-up preview modal
  const [followUpPreview, setFollowUpPreview] = useState<{ open: boolean; lead: Lead | null; message: string; templates: { id: string; name: string; content: string }[] }>({ open: false, lead: null, message: "", templates: [] });

  // WA manual preview modal
  const [waPreview, setWaPreview] = useState<{ open: boolean; lead: Lead | null; message: string; reportLink: string }>({ open: false, lead: null, message: "", reportLink: "" });

  // Rating filter
  const [filterRating, setFilterRating] = useState(0);
  // Search
  const [searchQuery, setSearchQuery] = useState("");
  // Pagination
  const [leadsPage, setLeadsPage] = useState(1);
  const LEADS_PAGE_SIZE = 25;

  // Add/Edit lead modal
  const [addLeadModal, setAddLeadModal] = useState(false);
  const [editLeadModal, setEditLeadModal] = useState<{ open: boolean; lead: Lead | null }>({ open: false, lead: null });
  const [leadForm, setLeadForm] = useState({ business_name: "", phone_number: "", address: "", product_interest: "" });
  const [savingLead, setSavingLead] = useState(false);

  // Toast
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  function showToast(message: string, type: "success" | "error" | "info" = "success") {
    setToast({ message, type });
  }

  function getScoreBreakdown(lead: Lead): string[] {
    const parts: string[] = [];
    if (lead.google_rating != null) {
      if (lead.google_rating >= 4.5) parts.push("Rating ≥4.5 +15");
      else if (lead.google_rating >= 4.0) parts.push("Rating 4.0-4.4 +10");
      else if (lead.google_rating >= 3.5) parts.push("Rating 3.5-3.9 +5");
      else parts.push("Rating <3.5 -10");
    }
    const rc = lead.review_count || 0;
    if (rc > 100) parts.push("Reviews >100 +15");
    else if (rc >= 20) parts.push("Reviews 20-100 +10");
    const pi = (lead.product_interest || "").toLowerCase();
    if (lead.website_url) {
      if (pi.includes("seo") || pi.includes("maintenance")) parts.push("Has website (SEO) +5");
      else parts.push("Has website -5");
    } else if (pi.includes("web")) parts.push("No website (WebDev) +10");
    const bn = (lead.batch_name || "").toLowerCase();
    if (bn.includes("web form")) parts.push("Web Form +20");
    else if (bn.includes("·") || bn.includes("scrape")) parts.push("Maps scraper -5");
    if (lead.status === "Replied") parts.push("Replied +15");
    else if (lead.status === "Contacted") parts.push("Contacted -10");
    const addr = (lead.address || "").toLowerCase();
    if (["jakarta","surabaya","bandung","bali","denpasar"].some(c => addr.includes(c))) parts.push("Tier 1 city +5");
    const name = (lead.business_name || "").toUpperCase();
    if (["PT ","PT."," CV ","CV.","GROUP","GRUP"].some(k => name.includes(k))) parts.push("PT/CV/Group +10");
    return parts;
  }

  async function recalculateAll() {
    setRecalculating(true);
    try {
      const res = await apiFetch("/api/leads/recalculate-scores", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        showToast(`Score diupdate: ${data.updated}/${data.total} leads`);
        fetchLeads();
      }
    } catch { showToast("Gagal recalculate", "error"); }
    finally { setRecalculating(false); }
  }

  const fetchBatches = useCallback(async () => {
    try {
      const res = await apiFetch("/api/leads/batches");
      if (res.ok) setBatches(await res.json());
    } catch { /* non-critical */ }
  }, []);

  const fetchLeads = useCallback(async () => {
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filterStatus) params.set("status", filterStatus);
      if (filterBatch) params.set("batch_name", filterBatch);
      if (showArchived) params.set("include_archived", "true");
      params.set("archived_only", showArchived ? "true" : "false");
      const res = await apiFetch(`/api/leads?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setLeads(await res.json());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal memuat leads.");
    } finally {
      setLoading(false);
    }
  }, [filterStatus, filterBatch, showArchived]);

  useEffect(() => {
    apiFetch("/api/templates")
      .then((r) => r.json())
      .then((data) => setHasTemplates(Array.isArray(data) && data.length > 0))
      .catch(() => {});
    apiFetch("/api/dynamic-templates?type=WA_BLAST")
      .then((r) => r.json())
      .then((data) => { if (Array.isArray(data)) setBlastTemplates(data.map((t: { id: string; name: string; content: string; category_id: string | null }) => ({ id: t.id, name: t.name, content: t.content, category_id: t.category_id }))); })
      .catch(() => {});
    apiFetch("/api/categories?active_only=true")
      .then((r) => r.json())
      .then((data) => { if (Array.isArray(data)) setBlastCategories(data.map((c: { id: string; name: string }) => ({ id: c.id, name: c.name }))); })
      .catch(() => {});
    apiFetch("/api/dynamic-templates?type=FOLLOW_UP")
      .then((r) => r.json())
      .then((data) => { if (Array.isArray(data)) setFollowUpTemplates(data.map((t: { id: string; name: string; content: string; category_id: string | null }) => ({ id: t.id, name: t.name, content: t.content, category_id: t.category_id }))); })
      .catch(() => {});
  }, []);

  useEffect(() => { fetchBatches(); }, [fetchBatches]);
  useEffect(() => {
    fetchLeads();
    intervalRef.current = setInterval(fetchLeads, 30000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchLeads]);

  async function handleChatWA(lead: Lead) {
    let reportLink = "";
    try {
      const reportRes = await apiFetch(`/api/leads/${lead.id}/generate-report`, { method: "POST" });
      if (reportRes.ok) {
        const data = await reportRes.json();
        if (data.report_url) reportLink = data.report_url;
      }
    } catch { /* report generation failed */ }

    const defaultMsg = DEFAULT_TEMPLATE
      .replace(/\{\{business_name\}\}/g, lead.business_name)
      .replace(/\{\{proposal_link\}\}/g, reportLink);
    setWaPreview({ open: true, lead, message: defaultMsg, reportLink });
  }

  async function sendWaPreview() {
    if (!waPreview.lead) return;
    try {
      const res = await apiFetch("/api/wa/send", {
        method: "POST",
        body: JSON.stringify({ lead_id: waPreview.lead.id, message: waPreview.message }),
      });
      if (res.ok) {
        showToast("Pesan terkirim via Fonnte!", "success");
        if (waPreview.lead.status === "Scraped") {
          setLeads(prev => prev.map(l => l.id === waPreview.lead!.id ? { ...l, status: "Contacted" } : l));
        }
      } else {
        const data = await res.json().catch(() => ({}));
        showToast(data.detail || "Gagal mengirim pesan.", "error");
      }
    } catch {
      showToast("Gagal mengirim pesan.", "error");
    }
    setWaPreview({ open: false, lead: null, message: "", reportLink: "" });
  }

  function handleFollowUp(lead: Lead) {
    const leadCategoryId = blastCategories.find(c => c.name === lead.product_interest)?.id;
    const matchingTemplates = followUpTemplates.filter(t => !t.category_id || t.category_id === leadCategoryId);
    const allTemplates = matchingTemplates.length > 0 ? matchingTemplates : followUpTemplates;
    const tmpl = allTemplates.length > 0 ? allTemplates[Math.floor(Math.random() * allTemplates.length)] : null;
    let message: string;
    if (tmpl) {
      message = tmpl.content
        .replace(/\{\{client_name\}\}/g, lead.business_name)
        .replace(/\{\{business_name\}\}/g, lead.business_name)
        .replace(/\{\{product_name\}\}/g, lead.product_interest || "layanan kami");
    } else {
      message = `Halo ${lead.business_name}, kami ingin follow up terkait penawaran sebelumnya. Apakah ada yang bisa kami bantu?`;
    }
    setFollowUpPreview({ open: true, lead, message, templates: followUpTemplates });
  }

  async function sendFollowUp() {
    if (!followUpPreview.lead) return;
    try {
      const res = await apiFetch("/api/wa/send", {
        method: "POST",
        body: JSON.stringify({ lead_id: followUpPreview.lead.id, message: followUpPreview.message }),
      });
      if (res.ok) {
        showToast("Follow up terkirim via Fonnte!", "success");
      } else {
        const data = await res.json().catch(() => ({}));
        showToast(data.detail || "Gagal mengirim follow up.", "error");
      }
    } catch {
      showToast("Gagal mengirim follow up.", "error");
    }
    setFollowUpPreview({ open: false, lead: null, message: "", templates: [] });
  }

  async function startSequence(lead: Lead) {
    try {
      const res = await apiFetch("/api/followup/start", {
        method: "POST",
        body: JSON.stringify({ lead_id: lead.id, delays: [1, 3, 7] }),
      });
      if (res.ok) {
        setToast({ message: `Sequence follow-up dimulai untuk ${lead.business_name}`, type: "success" });
      } else {
        const d = await res.json().catch(() => ({}));
        setToast({ message: d.detail || "Gagal memulai sequence", type: "error" });
      }
    } catch {
      setToast({ message: "Gagal memulai sequence", type: "error" });
    }
  }

  async function updateStatus(id: number, status: Status) {
    setUpdating(id);
    try {
      const res = await apiFetch(`/api/leads/${id}/status`, {
        method: "PATCH", body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setLeads((prev) => prev.map((l) => (l.id === id ? { ...l, status } : l)));
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal update status.", "error");
    } finally { setUpdating(null); }
  }

  async function updateProduct(id: number, product_interest: string) {
    setUpdating(id);
    try {
      const res = await apiFetch(`/api/leads/${id}/product`, {
        method: "PATCH", body: JSON.stringify({ product_interest }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setLeads((prev) => prev.map((l) => (l.id === id ? { ...l, product_interest } : l)));
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal update layanan.", "error");
    } finally { setUpdating(null); }
  }

  async function confirmConvert() {
    const lead = convertModal.lead;
    if (!lead) return;
    setUpdating(lead.id);
    setConvertModal({ open: false, lead: null });
    try {
      const res = await apiFetch(`/api/leads/${lead.id}/convert`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setLeads((prev) => prev.map((l) => (l.id === lead.id ? { ...l, status: "Closed/Client" } : l)));
      showToast(`${lead.business_name} berhasil dijadikan klien!`);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal konversi.", "error");
    } finally { setUpdating(null); }
  }

  async function confirmDelete() {
    const id = deleteModal.id;
    if (!id) return;
    setDeleteModal({ open: false, id: null, name: "" });
    setUpdating(id);
    try {
      const res = await apiFetch(`/api/leads/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const detail = await res.text().catch(() => "");
        throw new Error(detail || `HTTP ${res.status}`);
      }
      setLeads((prev) => prev.filter((l) => l.id !== id));
      showToast("Lead berhasil di-archive.");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal archive lead.", "error");
    } finally {
      setUpdating(null);
    }
  }

  async function restoreLead(id: number) {
    try {
      const res = await apiFetch(`/api/leads/restore/${id}`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      showToast("Lead berhasil di-restore.");
      fetchLeads();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal restore.", "error");
    }
  }

  async function confirmDeleteBatch() {
    setDeleteBatchModal(false);
    try {
      const res = await apiFetch(`/api/leads/batch/${encodeURIComponent(filterBatch)}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setFilterBatch("");
      await fetchBatches();
      await fetchLeads();
      showToast("Batch berhasil dihapus.");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal menghapus batch.", "error");
    }
  }

  async function handleCreateLead() {
    if (!leadForm.business_name || !leadForm.phone_number) return;
    setSavingLead(true);
    try {
      const res = await apiFetch("/api/leads", {
        method: "POST",
        body: JSON.stringify(leadForm),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setAddLeadModal(false);
      setLeadForm({ business_name: "", phone_number: "", address: "", product_interest: "" });
      showToast("Lead berhasil ditambahkan.");
      fetchLeads();
      fetchBatches();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal menambah lead.", "error");
    } finally { setSavingLead(false); }
  }

  async function handleEditLead() {
    if (!editLeadModal.lead || !leadForm.business_name || !leadForm.phone_number) return;
    setSavingLead(true);
    try {
      const res = await apiFetch(`/api/leads/${editLeadModal.lead.id}`, {
        method: "PUT",
        body: JSON.stringify(leadForm),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setEditLeadModal({ open: false, lead: null });
      setLeadForm({ business_name: "", phone_number: "", address: "", product_interest: "" });
      showToast("Lead berhasil diperbarui.");
      fetchLeads();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal memperbarui lead.", "error");
    } finally { setSavingLead(false); }
  }

  function openEditLead(lead: Lead) {
    setLeadForm({
      business_name: lead.business_name,
      phone_number: lead.phone_number,
      address: lead.address || "",
      product_interest: lead.product_interest || "",
    });
    setEditLeadModal({ open: true, lead });
  }

  async function exportCSV() {
    try {
      const res = await apiFetch("/api/export/leads");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "leads_export.csv";
      a.click();
      URL.revokeObjectURL(url);
      showToast("CSV berhasil diunduh.", "success");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal export CSV.", "error");
    }
  }

  async function startBlast() {
    if (!blastBatch || !blastTemplateId) return;
    setBlasting(true);
    try {
      if (blastSendMode === "scheduled") {
        if (!blastScheduledFor) { showToast("Pilih waktu pengiriman.", "error"); setBlasting(false); return; }
        const payload = {
          name: `Blast ${blastBatch} - ${new Date(blastScheduledFor).toLocaleString("id-ID")}`,
          template_id: blastTemplateId,
          filter_criteria: { status: "Scraped", batch_name: blastBatch, min_rating: blastMinRating },
          scheduled_for: new Date(blastScheduledFor).toISOString(),
        };
        const res = await apiFetch("/api/campaign/blast/schedule", { method: "POST", body: JSON.stringify(payload) });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setBlastOpen(false);
        showToast(`Blast dijadwalkan untuk ${new Date(blastScheduledFor).toLocaleString("id-ID")}`, "info");
      } else {
        const payload: Record<string, unknown> = { batch_name: blastBatch, product_category: blastCategoryId ? blastCategories.find(c => c.id === blastCategoryId)?.name || "" : "", min_rating: blastMinRating, template_id: blastTemplateId };
        const res = await apiFetch("/api/campaign/blast", { method: "POST", body: JSON.stringify(payload) });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setBlastOpen(false);
        localStorage.setItem("blast_batch", blastBatch);
        window.dispatchEvent(new StorageEvent("storage", { key: "blast_batch", newValue: blastBatch }));
        showToast("Campaign WA Blast berjalan di background!", "info");
      }
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal memulai blast.", "error");
    } finally { setBlasting(false); }
  }

  return (
    <div className="space-y-4">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />

      {/* Modals */}
      <Modal open={deleteModal.open} title="Hapus Lead"
        message={`Hapus "${deleteModal.name}" dari database? Tindakan ini tidak bisa dibatalkan.`}
        confirmLabel="Hapus" confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={confirmDelete} onCancel={() => setDeleteModal({ open: false, id: null, name: "" })} />

      <Modal open={deleteBatchModal} title="Hapus Batch"
        message={`Hapus semua lead dalam batch "${filterBatch}"? Tindakan ini tidak bisa dibatalkan.`}
        confirmLabel="Hapus Semua" confirmClass="bg-red-600 hover:bg-red-700"
        onConfirm={confirmDeleteBatch} onCancel={() => setDeleteBatchModal(false)} />

      <Modal open={convertModal.open} title="Jadikan Klien"
        message={`Pindahkan "${convertModal.lead?.business_name}" ke Buku Klien dan ubah status menjadi Closed/Client?`}
        confirmLabel="Jadikan Klien" confirmClass="bg-amber-500 hover:bg-amber-600 text-white font-bold"
        onConfirm={confirmConvert} onCancel={() => setConvertModal({ open: false, lead: null })} />

      {/* Follow-up Preview Modal */}
      {followUpPreview.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setFollowUpPreview({ open: false, lead: null, message: "", templates: [] })} />
          <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 w-full max-w-md p-6 space-y-4">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Follow Up: {followUpPreview.lead?.business_name}</h3>
            {followUpPreview.templates.length > 0 && (
              <div>
                <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Pilih Template</label>
                <select onChange={(e) => {
                  const t = followUpPreview.templates.find(t => t.id === e.target.value);
                  if (t && followUpPreview.lead) {
                    setFollowUpPreview(prev => ({ ...prev, message: t.content.replace(/\{\{client_name\}\}/g, prev.lead!.business_name).replace(/\{\{business_name\}\}/g, prev.lead!.business_name).replace(/\{\{product_name\}\}/g, prev.lead!.product_interest || "layanan kami") }));
                  }
                }} className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200 outline-none focus:ring-1 focus:ring-amber-300">
                  <option value="">— Pilih template lain —</option>
                  {followUpPreview.templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
            )}
            <div>
              <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Pesan</label>
              <textarea value={followUpPreview.message} onChange={(e) => setFollowUpPreview(prev => ({ ...prev, message: e.target.value }))}
                rows={5} className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200 outline-none focus:ring-1 focus:ring-amber-300 resize-none" />
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setFollowUpPreview({ open: false, lead: null, message: "", templates: [] })} className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={sendFollowUp} className="px-4 py-2 text-xs font-bold bg-amber-500 hover:bg-amber-600 text-white rounded-xl transition-colors">Kirim via WA</button>
            </div>
          </div>
        </div>
      )}

      {/* WA Manual Preview Modal */}
      {waPreview.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setWaPreview({ open: false, lead: null, message: "", reportLink: "" })} />
          <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 w-full max-w-md p-6 space-y-4">
            <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Chat WA: {waPreview.lead?.business_name}</h3>
            {blastTemplates.length > 0 && (
              <div>
                <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Pilih Template</label>
                <select onChange={(e) => {
                  const t = blastTemplates.find(t => t.id === e.target.value);
                  if (t && waPreview.lead) {
                    const msg = t.content
                      .replace(/\{\{business_name\}\}/g, waPreview.lead.business_name)
                      .replace(/\{\{proposal_link\}\}/g, `\n${waPreview.reportLink}\n`)
                      .replace(/\{\{product_name\}\}/g, waPreview.lead.product_interest || "layanan kami");
                    setWaPreview(prev => ({ ...prev, message: msg }));
                  }
                }} className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200 outline-none focus:ring-1 focus:ring-green-300">
                  <option value="">— Pilih template lain —</option>
                  {blastTemplates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
            )}
            <div>
              <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Pesan</label>
              <textarea value={waPreview.message} onChange={(e) => setWaPreview(prev => ({ ...prev, message: e.target.value }))}
                rows={7} className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200 outline-none focus:ring-1 focus:ring-green-300 resize-none" />
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setWaPreview({ open: false, lead: null, message: "", reportLink: "" })} className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={sendWaPreview} className="px-4 py-2 text-xs font-bold bg-green-500 hover:bg-green-600 text-white rounded-xl transition-colors">Kirim via WA</button>
            </div>
          </div>
        </div>
      )}

      {/* Blast Modal */}
      {blastOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setBlastOpen(false)} />
          <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 w-full max-w-md p-5 space-y-3 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-gray-900 dark:text-gray-100">Eksekusi WA Blast</h3>
              <button onClick={() => setBlastOpen(false)} className="p-1 text-gray-400 hover:text-gray-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            </div>

            {/* Target Info - realtime based on filters */}
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-2.5">
              <p className="text-sm font-semibold text-amber-700 dark:text-amber-300">
                Target: {leads.filter(l => l.status === "Scraped" && !l.is_archived && (blastMinRating === 0 || l.rating >= blastMinRating) && (!blastBatch || l.batch_name === blastBatch)).length} Leads akan menerima pesan.
              </p>
              <p className="text-[11px] text-amber-500 dark:text-amber-400 mt-0.5">
                Batch: {blastBatch || "Semua"} · Min. Rating: {blastMinRating || "Semua"} · Kategori: {blastCategoryId ? blastCategories.find(c => c.id === blastCategoryId)?.name : "Semua"}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Batch</label>
                <select value={blastBatch} onChange={(e) => setBlastBatch(e.target.value)}
                  className="w-full px-2.5 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-xs bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition">
                  <option value="">— Semua —</option>
                  {batches.map((b) => <option key={b} value={b}>{b}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Kategori</label>
                <select value={blastCategoryId} onChange={(e) => { setBlastCategoryId(e.target.value); setBlastTemplateId(""); }}
                  className="w-full px-2.5 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-xs bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition">
                  <option value="">— Semua —</option>
                  {blastCategories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Min. Rating</label>
                <select value={blastMinRating} onChange={(e) => setBlastMinRating(Number(e.target.value))}
                  className="w-full px-2.5 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-xs bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition">
                  <option value={0}>Semua</option>
                  <option value={1}>Min. 1</option>
                  <option value={2}>Min. 2</option>
                  <option value={3}>Min. 3</option>
                  <option value={4}>Min. 4</option>
                  <option value={5}>5 saja</option>
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Template</label>
                <select value={blastTemplateId} onChange={(e) => setBlastTemplateId(e.target.value)}
                  className="w-full px-2.5 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-xs bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition">
                  <option value="">— pilih —</option>
                  {blastTemplates.filter(t => !blastCategoryId || t.category_id === blastCategoryId).map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
            </div>
            {blastTemplates.length === 0 && (
              <p className="text-[11px] text-amber-500">Belum ada template WA Blast. <a href="/master/templates" className="underline">Buat di Master Data</a>.</p>
            )}

            <p className="text-xs text-gray-400">Hanya lead berstatus "Scraped" yang akan dikirim pesan. Delay 5 detik antar pesan.</p>

            {/* Send Mode */}
            <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Waktu Pengiriman</label>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="sendMode" checked={blastSendMode === "instant"} onChange={() => setBlastSendMode("instant")}
                    className="w-4 h-4 text-amber-600 focus:ring-amber-500" />
                  <span className="text-sm text-neutral-700 dark:text-neutral-300">Kirim Sekarang</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="sendMode" checked={blastSendMode === "scheduled"} onChange={() => setBlastSendMode("scheduled")}
                    className="w-4 h-4 text-amber-600 focus:ring-amber-500" />
                  <span className="text-sm text-neutral-700 dark:text-neutral-300">Jadwalkan</span>
                </label>
              </div>
              {blastSendMode === "scheduled" && (
                <div className="mt-2">
                  <input type="datetime-local" value={blastScheduledFor} onChange={e => setBlastScheduledFor(e.target.value)}
                    className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-gray-50 dark:bg-[var(--bg-surface)] dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setBlastOpen(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-xl transition-colors">Batal</button>
              <button onClick={startBlast} disabled={blasting || !blastBatch || !blastTemplateId}
                className="px-4 py-2 text-sm font-semibold bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-xl transition-all disabled:opacity-50">
                {blasting ? "Mengirim..." : "Mulai Kirim Blast"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search & Actions bar */}
      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[150px] max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Cari nama, alamat, atau nomor..."
            className="w-full pl-9 pr-3 py-1.5 border border-gray-200 dark:border-gray-700 rounded-lg text-xs bg-white dark:bg-[var(--bg-surface)] dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-amber-300/50 transition" />
        </div>
        <button onClick={() => { setLeadForm({ business_name: "", phone_number: "", address: "", product_interest: "" }); setAddLeadModal(true); }}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-yellow hover:bg-amber-600 text-white text-xs font-semibold rounded-lg transition-colors">
          <Plus size={12} /> <span className="hidden sm:inline">Tambah Lead</span><span className="sm:hidden">Tambah</span>
        </button>
        <button onClick={exportCSV}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-neutral-800 hover:bg-gray-200 dark:hover:bg-neutral-700 text-gray-700 dark:text-neutral-200 text-xs font-semibold rounded-lg transition-colors">
          <Download size={12} /> <span className="hidden sm:inline">Export CSV</span><span className="sm:hidden">Export</span>
        </button>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Status:</span>
        <button onClick={() => setFilterStatus("")}
          className={`px-2.5 sm:px-3 py-1 rounded-full text-xs font-semibold transition-colors ${filterStatus === "" ? "bg-amber-500 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"}`}>
          Semua
        </button>
        {STATUSES.map((s) => (
          <button key={s} onClick={() => setFilterStatus(s)}
            className={`px-2.5 sm:px-3 py-1 rounded-full text-xs font-semibold transition-colors ${filterStatus === s ? "bg-amber-500 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"}`}>
            {s}
          </button>
        ))}

        <div className="flex items-center gap-2 w-full sm:w-auto sm:ml-2">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Batch:</span>
          <select value={filterBatch} onChange={(e) => setFilterBatch(e.target.value)}
            className="text-xs border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 bg-white dark:bg-[var(--bg-surface)] text-gray-700 dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition max-w-[200px] flex-1 sm:flex-none">
            <option value="">Semua Batch</option>
            {batches.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
          {filterBatch && (
            <button onClick={() => setDeleteBatchModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500 hover:bg-red-600 text-white text-xs font-semibold rounded-lg transition-colors whitespace-nowrap">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14H6L5 6" /><path d="M10 11v6" /><path d="M14 11v6" /><path d="M9 6V4h6v2" />
              </svg>
              Hapus Batch
            </button>
          )}
        </div>

        {/* Blast button */}
        <button onClick={() => { setBlastBatch(filterBatch); setBlastOpen(true); }}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-lg transition-all shadow-sm whitespace-nowrap">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
          WA Blast
        </button>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Rating:</span>
          <select value={filterRating} onChange={(e) => setFilterRating(Number(e.target.value))}
            className="text-xs border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 bg-white dark:bg-[var(--bg-surface)] text-gray-700 dark:text-neutral-50 focus:outline-none focus:ring-2 focus:ring-amber-300 transition">
            <option value={0}>Semua</option>
            <option value={5}>5 Bintang</option>
            <option value={4}>Min. 4 Bintang</option>
            <option value={3}>Min. 3 Bintang</option>
            <option value={2}>Min. 2 Bintang</option>
            <option value={1}>Min. 1 Bintang</option>
          </select>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Score:</span>
          {([["", "Semua"], ["hot", "🎯 Siap Closing"], ["warm", "📞 Perlu Pendekatan"], ["cold", "💤 Belum Match"]] as const).map(([val, label]) => (
            <button key={val} onClick={() => setFilterScore(val as typeof filterScore)}
              className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors ${filterScore === val ? "bg-amber-500 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"}`}>
              {label}
            </button>
          ))}
        </div>

        <button onClick={recalculateAll} disabled={recalculating}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-neutral-800 hover:bg-gray-200 dark:hover:bg-neutral-700 text-gray-700 dark:text-neutral-200 text-xs font-semibold rounded-lg transition-colors disabled:opacity-50 whitespace-nowrap">
          {recalculating ? "..." : "Recalculate Scores"}
        </button>

        <button onClick={() => { fetchLeads(); fetchBatches(); }}
          className="sm:ml-auto px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-[var(--bg-surface)] border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
          ↻ Refresh
        </button>

        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={showArchived} onChange={e => setShowArchived(e.target.checked)} className="w-3.5 h-3.5 rounded border-gray-300 text-brand-yellow focus:ring-brand-yellow/50" />
          <span className="text-xs text-gray-500 font-medium">Archived</span>
        </label>
      </div>

      {error && <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 rounded-xl px-4 py-3 text-sm">{error}</div>}

      {loading && (
        <div className="bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-gray-100 dark:border-gray-700 shadow-card overflow-hidden">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="flex gap-4 px-6 py-4 border-b border-gray-50 dark:border-gray-800 last:border-0 animate-pulse">
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/4" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/3" />
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6 ml-auto" />
            </div>
          ))}
        </div>
      )}

      {!loading && !error && leads.length === 0 && (
        <div className="text-center py-12 text-gray-400 text-sm bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-gray-100 dark:border-gray-700">
          Belum ada leads. Gunakan <span className="font-semibold text-gray-600">Maps Scraper</span> untuk mencari bisnis.
        </div>
      )}

      {!loading && leads.length > 0 && (
        <div className="overflow-x-auto rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
          <table className="w-full min-w-[1100px] bg-white dark:bg-[var(--bg-canvas)] text-sm">
            <thead className="bg-gray-50 dark:bg-[var(--bg-surface)] border-b border-gray-100 dark:border-gray-700">
              <tr>
                {["#", "Nama Bisnis", "Alamat", "Nomor WA", "Layanan", "Website", "Google Rating", "Score", "Status", "Aksi"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {(() => {
                const filtered = leads.filter((l) => {
                  if (filterRating !== 0 && l.rating < filterRating) return false;
                  if (searchQuery && !l.business_name.toLowerCase().includes(searchQuery.toLowerCase()) && !(l.address || "").toLowerCase().includes(searchQuery.toLowerCase()) && !l.phone_number.includes(searchQuery)) return false;
                  const s = l.lead_score ?? 0;
                  if (filterScore === "hot" && s < 80) return false;
                  if (filterScore === "warm" && (s < 50 || s >= 80)) return false;
                  if (filterScore === "cold" && s >= 50) return false;
                  return true;
                }).sort((a, b) => (b.lead_score ?? 0) - (a.lead_score ?? 0));
                const start = (leadsPage - 1) * LEADS_PAGE_SIZE;
                return filtered.slice(start, start + LEADS_PAGE_SIZE).map((lead, i) => (
                <tr key={lead.id} className={`hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${lead.is_archived ? "opacity-70" : ""} ${lead.is_ghost_viewer ? "bg-red-500/10 border-l-4 border-l-red-500 animate-pulse" : ""}`}>
                  <td className="px-4 py-3 text-gray-400 text-xs">{start + i + 1}</td>
                  <td className="px-4 py-3 font-medium text-gray-800 dark:text-neutral-50 max-w-[180px]">
                    <div className="flex items-center gap-1.5">
                      <span>{lead.business_name}{lead.is_archived ? " (Archived)" : ""}</span>
                      {lead.is_ghost_viewer && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 whitespace-nowrap">GHOST VIEWER</span>
                      )}
                    </div>
                    {lead.batch_name && <div className="text-[10px] text-gray-400 mt-0.5 truncate max-w-[160px]">{lead.batch_name}</div>}
                  </td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400 max-w-[180px] text-xs leading-relaxed">{lead.address ?? "—"}</td>
                  <td className="px-4 py-3 font-mono text-gray-600 dark:text-gray-400 text-xs whitespace-nowrap">+{lead.phone_number}</td>
                  <td className="px-4 py-3">
                    <select value={lead.product_interest ?? ""} disabled={updating === lead.id || lead.is_archived}
                      onChange={(e) => updateProduct(lead.id, e.target.value)}
                      className="text-xs border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5 bg-white dark:bg-[var(--bg-surface)] text-gray-700 dark:text-neutral-50 cursor-pointer hover:border-amber-400 focus:outline-none focus:ring-2 focus:ring-amber-300 disabled:opacity-50 transition-colors">
                      <option value="">— pilih —</option>
                      {blastCategories.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {lead.website_url ? (
                      <a href={lead.website_url} target="_blank" rel="noopener" className="text-blue-600 hover:underline truncate block max-w-[120px]" title={lead.website_url}>
                        {lead.website_url.replace(/^https?:\/\//, "").replace(/\/$/, "").slice(0, 20)}...
                      </a>
                    ) : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {lead.google_rating ? (
                      <div className="flex items-center gap-1">
                        <span className="text-yellow-500">★</span>
                        <span className="font-medium">{lead.google_rating.toFixed(1)}</span>
                        {lead.review_count && <span className="text-gray-400">({lead.review_count})</span>}
                      </div>
                    ) : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {(() => {
                      const score = lead.lead_score ?? 0;
                      const color = getScoreColor(score);
                      const icon = getScoreIcon(score);
                      const tierLabel = getScoreLabel(score);
                      const breakdown = getScoreBreakdown(lead);
                      return (
                        <div className="group relative w-28">
                          <div className="flex items-center gap-1.5 mb-1">
                            <span>{icon}</span>
                            <span className="font-bold tabular-nums">{score}</span>
                          </div>
                          <div className="text-[10px] text-gray-500 dark:text-gray-400 mb-1 truncate" title={tierLabel}>{tierLabel}</div>
                          <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                            <div className={`h-full ${color} transition-all`} style={{ width: `${score}%` }}></div>
                          </div>
                          {breakdown.length > 0 && (
                            <div className="absolute left-0 top-full mt-1 z-20 hidden group-hover:block bg-gray-900 text-white text-[10px] rounded-lg px-3 py-2 shadow-xl whitespace-nowrap min-w-[180px]">
                              <div className="font-bold mb-1">Breakdown:</div>
                              {breakdown.map((b, i) => <div key={i}>• {b}</div>)}
                              <div className="mt-1 pt-1 border-t border-gray-700">Base: 50</div>
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-semibold ${STATUS_COLORS[lead.status]}`}>
                      {lead.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 flex-wrap max-w-[220px]">
                      {lead.is_archived ? (
                        <button onClick={() => restoreLead(lead.id)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-[11px] font-semibold rounded-lg transition-all whitespace-nowrap">
                          Restore
                        </button>
                      ) : (
                        <>
                          <button onClick={() => handleChatWA(lead)} disabled={updating === lead.id} title="Chat WhatsApp"
                            className="p-1.5 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-all disabled:opacity-50">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" /></svg>
                          </button>
                          {(lead.status === "Contacted" || lead.status === "Replied") && (
                            <button onClick={() => handleFollowUp(lead)} disabled={updating === lead.id} title="Follow Up Manual"
                              className="p-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg transition-all disabled:opacity-50">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" /></svg>
                            </button>
                          )}
                          {(lead.status === "Contacted" || lead.status === "Replied") && (
                            <button onClick={() => startSequence(lead)} disabled={updating === lead.id} title="Start Auto Follow-up (Hari 1, 3, 7)"
                              className="p-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all disabled:opacity-50">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>
                            </button>
                          )}
                          <select value={lead.status} disabled={updating === lead.id}
                            onChange={(e) => updateStatus(lead.id, e.target.value as Status)}
                            className="text-[11px] border border-neutral-200 dark:border-neutral-700 rounded-lg px-1.5 py-1.5 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 cursor-pointer focus:outline-none focus:ring-1 focus:ring-amber-300 disabled:opacity-50 transition-colors w-[90px]">
                            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                          </select>
                          {lead.status !== "Closed/Client" && (
                            <button onClick={() => setConvertModal({ open: true, lead })} disabled={updating === lead.id} title="Jadikan Klien"
                              className="p-1.5 text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-all disabled:opacity-50">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg>
                            </button>
                          )}
                          <button onClick={() => openEditLead(lead)} disabled={updating === lead.id} title="Edit Lead"
                            className="p-1.5 text-neutral-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-all disabled:opacity-50">
                            <Pencil size={12} />
                          </button>
                          <button onClick={() => setDeleteModal({ open: true, id: lead.id, name: lead.business_name })} disabled={updating === lead.id} title="Archive"
                            className="p-1.5 text-neutral-300 dark:text-neutral-600 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all disabled:opacity-50">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6l-1 14H6L5 6" /><path d="M10 11v6" /><path d="M14 11v6" /><path d="M9 6V4h6v2" /></svg>
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ));
            })()}
            </tbody>
          </table>
          {(() => {
            const filtered = leads.filter((l) => (filterRating === 0 || l.rating >= filterRating) && (!searchQuery || l.business_name.toLowerCase().includes(searchQuery.toLowerCase()) || (l.address || "").toLowerCase().includes(searchQuery.toLowerCase()) || l.phone_number.includes(searchQuery)));
            return <Pagination page={leadsPage} pageSize={LEADS_PAGE_SIZE} total={filtered.length} onPageChange={(p) => setLeadsPage(p)} itemLabel="lead" />;
          })()}
          <div className="px-4 py-2 bg-gray-50 dark:bg-[var(--bg-surface)] border-t border-gray-100 dark:border-gray-700 text-xs text-gray-400">
            {leads.filter((l) => filterRating === 0 || l.rating >= filterRating).length} lead{leads.filter((l) => filterRating === 0 || l.rating >= filterRating).length !== 1 ? "s" : ""}
            {filterBatch && <span className="ml-2 text-amber-400">· {filterBatch}</span>}
            {filterRating > 0 && <span className="ml-2 text-amber-400">· Min. {filterRating} Bintang</span>}
          </div>
        </div>
      )}

      {/* Add Lead Modal */}
      <Modal open={addLeadModal} title="Tambah Lead Baru" confirmLabel={savingLead ? "Menyimpan..." : "Simpan"} onConfirm={handleCreateLead} onCancel={() => setAddLeadModal(false)}>
        <div className="space-y-3">
          <input type="text" placeholder="Nama Bisnis *" value={leadForm.business_name} onChange={e => setLeadForm(f => ({ ...f, business_name: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="text" placeholder="Nomor WhatsApp * (cth: 6281234567890)" value={leadForm.phone_number} onChange={e => setLeadForm(f => ({ ...f, phone_number: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="text" placeholder="Alamat" value={leadForm.address} onChange={e => setLeadForm(f => ({ ...f, address: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <select value={leadForm.product_interest} onChange={e => setLeadForm(f => ({ ...f, product_interest: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition">
            <option value="">— Pilih Layanan —</option>
            {blastCategories.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
          </select>
        </div>
      </Modal>

      {/* Edit Lead Modal */}
      <Modal open={editLeadModal.open} title="Edit Lead" confirmLabel={savingLead ? "Menyimpan..." : "Simpan"} onConfirm={handleEditLead} onCancel={() => setEditLeadModal({ open: false, lead: null })}>
        <div className="space-y-3">
          <input type="text" placeholder="Nama Bisnis *" value={leadForm.business_name} onChange={e => setLeadForm(f => ({ ...f, business_name: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="text" placeholder="Nomor WhatsApp *" value={leadForm.phone_number} onChange={e => setLeadForm(f => ({ ...f, phone_number: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="text" placeholder="Alamat" value={leadForm.address} onChange={e => setLeadForm(f => ({ ...f, address: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <select value={leadForm.product_interest} onChange={e => setLeadForm(f => ({ ...f, product_interest: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition">
            <option value="">— Pilih Layanan —</option>
            {blastCategories.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
          </select>
        </div>
      </Modal>
    </div>
  );
}
