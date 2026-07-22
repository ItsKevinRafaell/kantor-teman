"use client";
import NativeSelect from "./ui/NativeSelect";

import { useState } from "react";
import { useLeadsTable } from "../hooks/useLeads";
import { apiFetch } from "../lib/api";
import { downloadBlob } from "../utils/download";
import Toast from "./Toast";
import Modal from "./Modal";
import Pagination from "./Pagination";
import LeadsFilterBar from "./leads/LeadsFilterBar";
import LeadsTableBody from "./leads/LeadsTableBody";

const DEFAULT_TEMPLATE =
  "Halo {{business_name}}, kami baru saja menyiapkan audit digital singkat untuk bisnis Anda. Ada beberapa peluang perbaikan yang mungkin relevan untuk membantu calon pelanggan lebih mudah menemukan dan menghubungi bisnis Anda.\n\nLaporan ringkasnya dapat dilihat di sini:\n{{proposal_link}}\n\nApakah saya boleh menjelaskan poin yang paling priority?";

export default function LeadsTable({ initialBatch }: { initialBatch?: string }) {
  const {
    leads, leadsLoading, batches, blastTemplates, blastCategories, followUpTemplates,
    filters, setFilterStatus, setFilterBatch, setFilterScore, setFilterRating,
    showArchived, setShowArchived, refresh, recalculate,
    deleteLead, restoreLead, updateStatus, updateProduct, startBlast,
    saveSalesAction, convertLead, createLead, updateLead,
  } = useLeadsTable(initialBatch);

  const [searchQuery, setSearchQuery] = useState("");
  const [leadsPage, setLeadsPage] = useState(1);
  const LEADS_PAGE_SIZE = 25;
  const [recalculating, setRecalculating] = useState(false);
  const [updating, setUpdating] = useState<number | null>(null);
  const [savingLead, setSavingLead] = useState(false);

  // Delete / Convert
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; id: number | null; name: string }>({ open: false, id: null, name: "" });
  const [deleteBatchModal, setDeleteBatchModal] = useState(false);
  const [convertModal, setConvertModal] = useState<{ open: boolean; lead: any | null }>({ open: false, lead: null });

  // Sales modal (inline)
  const [salesModal, setSalesModal] = useState<{ open: boolean; lead: any | null }>({ open: false, lead: null });
  const [salesForm, setSalesForm] = useState({ sales_owner: "", next_action_at: "", loss_reason: "", do_not_contact: false });
  const [scoreModal, setScoreModal] = useState<{ open: boolean; lead: any | null }>({ open: false, lead: null });
  const [scoreForm, setScoreForm] = useState({ adjustment: 0, reason: "" });

  // Add/Edit lead
  const [addLeadModal, setAddLeadModal] = useState(false);
  const [editLeadModal, setEditLeadModal] = useState<{ open: boolean; lead: any | null }>({ open: false, lead: null });
  const emptyLeadForm = {
    business_name: "",
    phone_number: "",
    address: "",
    product_interest: "",
    website_url: "",
    original_url: "",
    instagram_url: "",
    facebook_url: "",
    tiktok_url: "",
    google_rating: "" as string | number,
    review_count: "" as string | number,
  };
  const [leadForm, setLeadForm] = useState({ ...emptyLeadForm });

  // Preview modals (inline)
  const [followUpPreview, setFollowUpPreview] = useState<{ open: boolean; lead: any | null; message: string; templates: any[] }>({ open: false, lead: null, message: "", templates: [] });
  const [waPreview, setWaPreview] = useState<{ open: boolean; lead: any | null; message: string; reportLink: string }>({ open: false, lead: null, message: "", reportLink: "" });

  // Blast modal (inline)
  const [blastOpen, setBlastOpen] = useState(false);
  const [blastBatch, setBlastBatch] = useState("");
  const [blastCategoryId, setBlastCategoryId] = useState("");
  const [blastMinRating, setBlastMinRating] = useState(0);
  const [blastTemplateId, setBlastTemplateId] = useState("");
  const [blastSendMode, setBlastSendMode] = useState<"instant" | "scheduled">("instant");
  const [blastScheduledFor, setBlastScheduledFor] = useState("");
  const [blasting, setBlasting] = useState(false);

  // Toast
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);
  function showToast(message: string, type: "success" | "error" | "info" = "success") { setToast({ message, type }); }

  // ─── Action handlers ──────────────────────────────────────────────────────

  async function handleRecalculateAll() {
    setRecalculating(true);
    try { await recalculate(); showToast("Score berhasil dihitung ulang."); }
    catch { showToast("Gagal menghitung ulang score", "error"); }
    finally { setRecalculating(false); }
  }

  async function handleChatWA(lead: any) {
    let reportLink = "";
    try {
      const reportRes = await apiFetch(`/api/leads/${lead.id}/generate-report?force=1`, { method: "POST" });
      if (reportRes.ok) { const d = await reportRes.json(); if (d.report_url) reportLink = d.report_url; }
    } catch {}
    const msg = DEFAULT_TEMPLATE.replace(/\{\{business_name\}\}/g, lead.business_name).replace(/\{\{proposal_link\}\}/g, reportLink);
    setWaPreview({ open: true, lead, message: msg, reportLink });
  }

  async function handleViewReport(lead: any) {
    try {
      const reportRes = await apiFetch(`/api/leads/${lead.id}/generate-report?force=1`, { method: "POST" });
      if (reportRes.ok) {
        const d = await reportRes.json();
        if (d.report_url) {
          window.open(d.report_url, "_blank");
        }
      } else {
        showToast("Gagal generate report.", "error");
      }
    } catch { showToast("Gagal generate report.", "error"); }
  }

  async function sendWaPreview() {
    if (!waPreview.lead) return;
    try {
      const res = await apiFetch("/api/wa/send", { method: "POST", body: JSON.stringify({ lead_id: waPreview.lead.id, message: waPreview.message }) });
      if (res.ok) showToast("Pesan terkirim!", "success");
      else { const d = await res.json().catch(() => ({})); showToast(d.detail || "Gagal mengirim pesan.", "error"); }
    } catch { showToast("Gagal mengirim pesan.", "error"); }
    setWaPreview({ open: false, lead: null, message: "", reportLink: "" });
  }

  function handleFollowUp(lead: any) {
    const leadCategoryId = blastCategories.find(c => c.name === lead.product_interest)?.id;
    const matchingTemplates = followUpTemplates.filter((t: any) => !t.category_id || t.category_id === leadCategoryId);
    const allTemplates = matchingTemplates.length > 0 ? matchingTemplates : followUpTemplates;
    const tmpl = allTemplates[Math.floor(Math.random() * allTemplates.length)] ?? null;
    const message = tmpl
      ? tmpl.content.replace(/\{\{client_name\}\}/g, lead.business_name).replace(/\{\{business_name\}\}/g, lead.business_name).replace(/\{\{product_name\}\}/g, lead.product_interest || "layanan kami")
      : `Halo ${lead.business_name}, kami ingin follow up terkait penawaran sebelumnya. Apakah ada yang bisa kami bantu?`;
    setFollowUpPreview({ open: true, lead, message, templates: followUpTemplates });
  }

  async function sendFollowUp() {
    if (!followUpPreview.lead) return;
    try {
      const res = await apiFetch("/api/wa/send", { method: "POST", body: JSON.stringify({ lead_id: followUpPreview.lead.id, message: followUpPreview.message }) });
      if (res.ok) showToast("Follow up terkirim!", "success");
      else { const d = await res.json().catch(() => ({})); showToast(d.detail || "Gagal mengirim follow up.", "error"); }
    } catch { showToast("Gagal mengirim follow up.", "error"); }
    setFollowUpPreview({ open: false, lead: null, message: "", templates: [] });
  }

  async function startSequence(lead: any) {
    try {
      const res = await apiFetch("/api/followup/start", { method: "POST", body: JSON.stringify({ lead_id: lead.id, delays: [1, 3, 7] }) });
      if (res.ok) setToast({ message: `Sequence follow-up dimulai untuk ${lead.business_name}`, type: "success" });
      else { const d = await res.json().catch(() => ({})); setToast({ message: d.detail || "Gagal memulai sequence", type: "error" }); }
    } catch { setToast({ message: "Gagal memulai sequence", type: "error" }); }
  }

  async function handleUpdateStatus(id: number, status: string) {
    setUpdating(id);
    try { await updateStatus(id, status as any); showToast("Status diupdate."); }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : "Gagal update status.", "error"); }
    finally { setUpdating(null); }
  }

  async function handleUpdateProduct(id: number, product_interest: string) {
    setUpdating(id);
    try { await updateProduct(id, product_interest); showToast("Layanan diupdate."); }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : "Gagal update layanan.", "error"); }
    finally { setUpdating(null); }
  }

  function openScoreModal(lead: any) {
    setScoreForm({ adjustment: lead.score_adjustment || 0, reason: lead.score_adjustment_reason || "" });
    setScoreModal({ open: true, lead });
  }

  async function saveScoreAdjustment() {
    if (!scoreModal.lead) return;
    try {
      const res = await apiFetch(`/api/leads/${scoreModal.lead.id}/score-adjustment`, {
        method: "PATCH",
        body: JSON.stringify({ adjustment: Number(scoreForm.adjustment) || 0, reason: scoreForm.reason }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || "Gagal menyimpan adjustment score.");
      }
      showToast("Adjustment score tersimpan.");
      setScoreModal({ open: false, lead: null });
      await refresh();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Gagal menyimpan adjustment score.", "error");
    }
  }

  function openSalesModal(lead: any) {
    setSalesForm({ sales_owner: lead.sales_owner || "", next_action_at: lead.next_action_at ? lead.next_action_at.slice(0, 16) : "", loss_reason: lead.loss_reason || "", do_not_contact: lead.do_not_contact });
    setSalesModal({ open: true, lead });
  }

  async function handleSaveSalesAction() {
    if (!salesModal.lead) return;
    try {
      await saveSalesAction(salesModal.lead.id, { sales_owner: salesForm.sales_owner, next_action_at: salesForm.next_action_at, loss_reason: salesForm.loss_reason, do_not_contact: salesForm.do_not_contact });
      setSalesModal({ open: false, lead: null });
      showToast("Tindak lanjut sales diperbarui.");
    } catch { showToast("Gagal menyimpan tindak lanjut.", "error"); }
  }

  async function handleConvert(lead: any) {
    setUpdating(lead.id);
    try { await convertLead(lead.id); setConvertModal({ open: false, lead: null }); showToast(`${lead.business_name} berhasil dijadikan klien!`); }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : "Gagal konversi.", "error"); }
    finally { setUpdating(null); }
  }

  async function handleDelete(id: number) {
    setDeleteModal({ open: false, id: null, name: "" });
    setUpdating(id);
    try { await deleteLead(id); showToast("Lead berhasil diarsipkan."); }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : "Gagal archive lead.", "error"); }
    finally { setUpdating(null); }
  }

  async function handleRestore(id: number) {
    try { await restoreLead(id); showToast("Lead berhasil dikembalikan."); }
    catch (err: unknown) { showToast(err instanceof Error ? err.message : "Gagal restore.", "error"); }
  }

  async function handleDeleteBatch() {
    setDeleteBatchModal(false);
    showToast("Batch berhasil diarsipkan.");
  }

  function payloadFromLeadForm() {
    const ratingRaw = leadForm.google_rating === "" ? null : Number(leadForm.google_rating);
    const reviewsRaw = leadForm.review_count === "" ? null : Number(leadForm.review_count);
    return {
      business_name: leadForm.business_name,
      phone_number: leadForm.phone_number,
      address: leadForm.address || undefined,
      product_interest: leadForm.product_interest || undefined,
      website_url: leadForm.website_url || undefined,
      original_url: leadForm.original_url || undefined,
      instagram_url: leadForm.instagram_url || undefined,
      facebook_url: leadForm.facebook_url || undefined,
      tiktok_url: leadForm.tiktok_url || undefined,
      google_rating: ratingRaw != null && !Number.isNaN(ratingRaw) ? ratingRaw : null,
      review_count: reviewsRaw != null && !Number.isNaN(reviewsRaw) ? reviewsRaw : null,
    };
  }

  async function handleCreateLead() {
    if (!leadForm.business_name || !leadForm.phone_number) return;
    setSavingLead(true);
    try {
      await createLead(payloadFromLeadForm());
      setAddLeadModal(false);
      setLeadForm({ ...emptyLeadForm });
      showToast("Lead berhasil ditambahkan.");
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : "Gagal menambah lead.", "error"); }
    finally { setSavingLead(false); }
  }

  async function handleEditLead() {
    if (!editLeadModal.lead || !leadForm.business_name || !leadForm.phone_number) return;
    setSavingLead(true);
    try {
      await updateLead(editLeadModal.lead.id, payloadFromLeadForm());
      setEditLeadModal({ open: false, lead: null });
      setLeadForm({ ...emptyLeadForm });
      showToast("Lead berhasil diperbarui.");
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : "Gagal memperbarui lead.", "error"); }
    finally { setSavingLead(false); }
  }

  function openEditLead(lead: any) {
    setLeadForm({
      business_name: lead.business_name,
      phone_number: lead.phone_number,
      address: lead.address || "",
      product_interest: lead.product_interest || "",
      website_url: lead.website_url || "",
      original_url: lead.original_url || "",
      instagram_url: lead.instagram_url || "",
      facebook_url: lead.facebook_url || "",
      tiktok_url: lead.tiktok_url || "",
      google_rating: lead.google_rating ?? "",
      review_count: lead.review_count ?? "",
    });
    setEditLeadModal({ open: true, lead });
  }

  async function exportCSV() {
    try {
      const res = await apiFetch("/api/export/leads");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      downloadBlob(await res.blob(), "leads_export.csv");
      showToast("CSV berhasil diunduh.", "success");
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : "Gagal export CSV.", "error"); }
  }

  async function handleStartBlast() {
    if (!blastBatch || !blastTemplateId) return;
    setBlasting(true);
    try {
      await startBlast(blastBatch, blastCategoryId, blastMinRating, blastTemplateId, blastSendMode, blastScheduledFor);
      setBlastOpen(false);
      showToast(blastSendMode === "scheduled" ? "Blast dijadwalkan." : "Campaign WA Blast berjalan di background!", "info");
    } catch (err: unknown) { showToast(err instanceof Error ? err.message : "Gagal memulai blast.", "error"); }
    finally { setBlasting(false); }
  }

  // ─── JSX ───────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-4">
      <Toast message={toast?.message ?? null} type={toast?.type} onClose={() => setToast(null)} />

      {/* Delete Lead */}
      <Modal open={deleteModal.open} title="Arsipkan Lead"
        message={`Pindahkan "${deleteModal.name}" ke arsip?`}
        confirmLabel="Arsipkan" confirmClass="bg-amber-500 hover:bg-amber-600"
        onConfirm={() => deleteModal.id != null && handleDelete(deleteModal.id)} onCancel={() => setDeleteModal({ open: false, id: null, name: "" })} />

      {/* Delete Batch */}
      <Modal open={deleteBatchModal} title="Arsipkan Batch"
        message={`Pindahkan semua lead dalam batch "${filters.batch}" ke arsip?`}
        confirmLabel="Arsipkan Semua" confirmClass="bg-amber-500 hover:bg-amber-600"
        onConfirm={handleDeleteBatch} onCancel={() => setDeleteBatchModal(false)} />

      {/* Convert */}
      <Modal open={convertModal.open} title="Jadikan Klien"
        message={`Pindahkan "${convertModal.lead?.business_name}" ke Buku Klien?`}
        confirmLabel="Jadikan Klien" confirmClass="bg-amber-500 hover:bg-amber-600 text-white font-bold"
        onConfirm={() => convertModal.lead && handleConvert(convertModal.lead)} onCancel={() => setConvertModal({ open: false, lead: null })} />

      {/* Sales Modal */}
      {salesModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setSalesModal({ open: false, lead: null })} />
          <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 w-full max-w-md p-6 space-y-4">
            <div>
              <h3 className="text-sm font-bold text-neutral-800 dark:text-neutral-200">Tindak Lanjut Sales</h3>
              <p className="text-xs text-gray-400 mt-1">{salesModal.lead?.business_name}</p>
            </div>
            <div>
              <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">PIC Sales</label>
              <input value={salesForm.sales_owner} onChange={e => setSalesForm(p => ({ ...p, sales_owner: e.target.value }))}
                className="w-full text-sm px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200" placeholder="Nama sales..." />
            </div>
            <div>
              <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Next Action</label>
              <input type="datetime-local" value={salesForm.next_action_at} onChange={e => setSalesForm(p => ({ ...p, next_action_at: e.target.value }))}
                className="w-full text-sm px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200" />
            </div>
            <div>
              <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Alasan Lost / Catatan</label>
              <textarea value={salesForm.loss_reason} onChange={e => setSalesForm(p => ({ ...p, loss_reason: e.target.value }))}
                rows={3} className="w-full text-sm px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200 resize-none" placeholder="Isi bila lead tidak dilanjutkan..." />
            </div>
            <label className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-300">
              <input type="checkbox" checked={salesForm.do_not_contact} onChange={e => setSalesForm(p => ({ ...p, do_not_contact: e.target.checked }))} />
              Jangan hubungi lagi nomor ini
            </label>
            <div className="flex justify-end gap-2">
              <button onClick={() => setSalesModal({ open: false, lead: null })} className="px-4 py-2 text-xs font-semibold text-gray-600 bg-gray-100 dark:bg-gray-800 rounded-xl">Batal</button>
              <button onClick={handleSaveSalesAction} className="px-4 py-2 text-xs font-bold bg-amber-500 hover:bg-amber-600 text-white rounded-xl">Simpan</button>
            </div>
          </div>
        </div>
      )}

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
                  const t = followUpPreview.templates.find((t2: any) => t2.id === e.target.value);
                  if (t && followUpPreview.lead) {
                    setFollowUpPreview(prev => ({ ...prev, message: t.content.replace(/\{\{client_name\}\}/g, prev.lead!.business_name).replace(/\{\{business_name\}\}/g, prev.lead!.business_name).replace(/\{\{product_name\}\}/g, prev.lead!.product_interest || "layanan kami") }));
                  }
                }} className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200 outline-none focus:ring-1 focus:ring-amber-300">
                  <option value="">— Pilih template lain —</option>
                  {followUpPreview.templates.map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}
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
                  const t = blastTemplates.find((t2: any) => t2.id === e.target.value);
                  if (t && waPreview.lead) {
                    const msg = t.content.replace(/\{\{business_name\}\}/g, waPreview.lead.business_name).replace(/\{\{proposal_link\}\}/g, `\n${waPreview.reportLink}\n`).replace(/\{\{product_name\}\}/g, waPreview.lead.product_interest || "layanan kami");
                    setWaPreview(prev => ({ ...prev, message: msg }));
                  }
                }} className="w-full text-xs px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-200 outline-none focus:ring-1 focus:ring-green-300">
                  <option value="">— Pilih template lain —</option>
                  {blastTemplates.map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}
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
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-2.5">
              <p className="text-sm font-semibold text-amber-700 dark:text-amber-300">
                Target: {leads.filter((l: any) => l.status === "Scraped" && !l.is_archived && !l.do_not_contact && (blastMinRating === 0 || l.rating >= blastMinRating) && (!blastBatch || l.batch_name === blastBatch)).length} Leads akan menerima pesan.
              </p>
              <p className="text-[11px] text-amber-500 dark:text-amber-400 mt-0.5">
                Batch: {blastBatch || "Semua"} · Min. Rating: {blastMinRating || "Semua"} · Kategori: {blastCategoryId ? blastCategories.find((c: any) => c.id === blastCategoryId)?.name : "Semua"}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Batch</label>
                <NativeSelect value={blastBatch} onChange={setBlastBatch} placeholder="Pilih batch" searchPlaceholder="Cari batch…" options={batches.filter(Boolean).map((b: string) => ({ value: b, label: b }))} />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Kategori</label>
                <NativeSelect value={blastCategoryId} onChange={v => { setBlastCategoryId(v); setBlastTemplateId(""); }} placeholder="Pilih kategori" searchPlaceholder="Cari kategori…" options={blastCategories.map((c: any) => ({ value: String(c.id), label: c.name }))} />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Min. Rating</label>
                <NativeSelect value={String(blastMinRating)} onChange={v => setBlastMinRating(Number(v || 0))} clearable={false} options={[{value:"0",label:"Semua rating"},{value:"4",label:"Min 4★"},{value:"4.5",label:"Min 4.5★"},{value:"5",label:"5★"}]} />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-gray-500 uppercase mb-1">Template</label>
                <NativeSelect value={blastTemplateId} onChange={setBlastTemplateId} placeholder="Pilih template" searchPlaceholder="Cari template…" options={blastTemplates.filter((t: any) => !blastCategoryId || t.category_id === blastCategoryId).map((t: any) => ({ value: t.id, label: t.name }))} />
              </div>
            </div>
            {blastTemplates.length === 0 && (
              <p className="text-[11px] text-amber-500">Belum ada template WA Blast. <a href="/master/templates" className="underline">Buat di Master Data</a>.</p>
            )}
            <p className="text-xs text-gray-400">Hanya lead Scraped tanpa opt-out yang masuk antrean. Delay 5 detik antar pesan.</p>
            <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Waktu Pengiriman</label>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="sendMode" checked={blastSendMode === "instant"} onChange={() => setBlastSendMode("instant")} className="w-4 h-4 text-amber-600 focus:ring-amber-500" />
                  <span className="text-sm text-neutral-700 dark:text-neutral-300">Kirim Sekarang</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="sendMode" checked={blastSendMode === "scheduled"} onChange={() => setBlastSendMode("scheduled")} className="w-4 h-4 text-amber-600 focus:ring-amber-500" />
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
              <button onClick={handleStartBlast} disabled={blasting || !blastBatch || !blastTemplateId || (blastSendMode === "scheduled" && !blastScheduledFor)}
                className="px-4 py-2 text-sm font-semibold bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-xl transition-all disabled:opacity-50">
                {blasting ? "Mengirim..." : "Mulai Kirim Blast"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <LeadsFilterBar
        searchQuery={searchQuery} onSearchChange={setSearchQuery}
        filters={filters} batches={batches}
        onStatusChange={setFilterStatus} onBatchChange={setFilterBatch}
        onScoreChange={setFilterScore} onRatingChange={setFilterRating}
        onAddLead={() => { setLeadForm({ ...emptyLeadForm }); setAddLeadModal(true); }}
        onExportCSV={exportCSV} onOpenBlast={() => { setBlastBatch(filters.batch); setBlastOpen(true); }}
        onRecalculate={handleRecalculateAll} onRefresh={refresh}
        recalculating={recalculating} showArchived={showArchived}
        onShowArchivedChange={setShowArchived} onDeleteBatch={() => setDeleteBatchModal(true)}
      />

      {/* Loading skeleton */}
      {leadsLoading && (
        <div className="bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-gray-100 dark:border-gray-700 shadow-card overflow-hidden">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="flex gap-4 px-6 py-4 border-b border-gray-50 dark:border-gray-800 last:border-0 animate-pulse">
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/4" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/3" />
              <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6" /><div className="h-4 bg-gray-100 dark:bg-gray-800 rounded w-1/6 ml-auto" />
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!leadsLoading && leads.length === 0 && (
        <div className="text-center py-12 text-gray-400 text-sm bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-gray-100 dark:border-gray-700">
          Belum ada prospek. Gunakan <span className="font-semibold text-gray-600">Penyisir Maps</span> untuk mencari bisnis baru.
        </div>
      )}

      {/* Table */}
      {!leadsLoading && leads.length > 0 && (
        <div className="overflow-x-auto rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
          <table className="w-full min-w-[1250px] bg-white dark:bg-[var(--bg-canvas)] text-sm">
            <thead className="bg-gray-50 dark:bg-[var(--bg-surface)] border-b border-gray-100 dark:border-gray-700">
              <tr>
                {["#", "Nama Bisnis", "Alamat", "Nomor WA", "Layanan", "Website", "Google Rating", "Score", "Next Action", "Status", "Aksi"].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              <LeadsTableBody
                showArchived={showArchived}
                leads={leads} filters={filters} searchQuery={searchQuery}
                blastCategories={blastCategories} updating={updating}
                page={leadsPage} pageSize={LEADS_PAGE_SIZE}
                onUpdateStatus={handleUpdateStatus} onUpdateProduct={handleUpdateProduct}
                onChatWA={handleChatWA} onViewReport={handleViewReport}
                onFollowUp={handleFollowUp} onStartSequence={startSequence}
                onOpenSales={openSalesModal} onConvert={lead => setConvertModal({ open: true, lead })}
                onAdjustScore={openScoreModal}
                onEdit={openEditLead} onArchive={lead => setDeleteModal({ open: true, id: lead.id, name: lead.business_name })}
                onRestore={handleRestore}
              />
            </tbody>
          </table>
          <Pagination page={leadsPage} pageSize={LEADS_PAGE_SIZE} total={leads.length} onPageChange={p => setLeadsPage(p)} itemLabel="prospek" />
          <div className="px-4 py-2 bg-gray-50 dark:bg-[var(--bg-surface)] border-t border-gray-100 dark:border-gray-700 text-xs text-gray-400">
            {leads.length} prospek
            {filters.batch && <span className="ml-2 text-amber-400">· {filters.batch}</span>}
            {filters.rating > 0 && <span className="ml-2 text-amber-400">· Min. {filters.rating} Bintang</span>}
          </div>
        </div>
      )}

      {/* Add Lead */}
      <Modal open={addLeadModal} title="Tambah Prospek Baru" confirmLabel={savingLead ? "Menyimpan..." : "Simpan"} onConfirm={handleCreateLead} onCancel={() => { setAddLeadModal(false); setLeadForm({ ...emptyLeadForm }); }}>
        <div className="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
          <input type="text" placeholder="Nama Bisnis *" value={leadForm.business_name} onChange={e => setLeadForm(f => ({ ...f, business_name: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="text" placeholder="Nomor WhatsApp * (cth: 6281234567890)" value={leadForm.phone_number} onChange={e => setLeadForm(f => ({ ...f, phone_number: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="text" placeholder="Alamat" value={leadForm.address} onChange={e => setLeadForm(f => ({ ...f, address: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <NativeSelect value={leadForm.product_interest} onChange={v => setLeadForm(f => ({ ...f, product_interest: v }))} placeholder="Pilih minat produk" options={blastCategories.map((c: any) => ({ value: c.name, label: c.name }))} />
          <p className="pt-1 text-[10px] font-bold uppercase tracking-widest text-gray-400">Jejak digital (opsional)</p>
          <input type="url" placeholder="Website (https://...)" value={leadForm.website_url} onChange={e => setLeadForm(f => ({ ...f, website_url: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="url" placeholder="Google Business / Maps URL" value={leadForm.original_url} onChange={e => setLeadForm(f => ({ ...f, original_url: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="url" placeholder="Instagram URL" value={leadForm.instagram_url} onChange={e => setLeadForm(f => ({ ...f, instagram_url: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="url" placeholder="Facebook URL" value={leadForm.facebook_url} onChange={e => setLeadForm(f => ({ ...f, facebook_url: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="url" placeholder="TikTok URL" value={leadForm.tiktok_url} onChange={e => setLeadForm(f => ({ ...f, tiktok_url: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <div className="grid grid-cols-2 gap-2">
            <input type="number" step="0.1" min="0" max="5" placeholder="Rating Maps" value={leadForm.google_rating} onChange={e => setLeadForm(f => ({ ...f, google_rating: e.target.value }))}
              className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
            <input type="number" min="0" placeholder="Jumlah ulasan" value={leadForm.review_count} onChange={e => setLeadForm(f => ({ ...f, review_count: e.target.value }))}
              className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          </div>
        </div>
      </Modal>

      {/* Edit Lead */}
      <Modal open={editLeadModal.open} title="Edit Lead" confirmLabel={savingLead ? "Menyimpan..." : "Simpan"} onConfirm={handleEditLead} onCancel={() => { setEditLeadModal({ open: false, lead: null }); setLeadForm({ ...emptyLeadForm }); }}>
        <div className="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
          <input type="text" placeholder="Nama Bisnis *" value={leadForm.business_name} onChange={e => setLeadForm(f => ({ ...f, business_name: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="text" placeholder="Nomor WhatsApp *" value={leadForm.phone_number} onChange={e => setLeadForm(f => ({ ...f, phone_number: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="text" placeholder="Alamat" value={leadForm.address} onChange={e => setLeadForm(f => ({ ...f, address: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <NativeSelect value={leadForm.product_interest} onChange={v => setLeadForm(f => ({ ...f, product_interest: v }))} placeholder="Pilih minat produk" options={blastCategories.map((c: any) => ({ value: c.name, label: c.name }))} />
          <p className="pt-1 text-[10px] font-bold uppercase tracking-widest text-gray-400">Jejak digital (opsional)</p>
          <input type="url" placeholder="Website (https://...)" value={leadForm.website_url} onChange={e => setLeadForm(f => ({ ...f, website_url: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="url" placeholder="Google Business / Maps URL" value={leadForm.original_url} onChange={e => setLeadForm(f => ({ ...f, original_url: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="url" placeholder="Instagram URL" value={leadForm.instagram_url} onChange={e => setLeadForm(f => ({ ...f, instagram_url: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="url" placeholder="Facebook URL" value={leadForm.facebook_url} onChange={e => setLeadForm(f => ({ ...f, facebook_url: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <input type="url" placeholder="TikTok URL" value={leadForm.tiktok_url} onChange={e => setLeadForm(f => ({ ...f, tiktok_url: e.target.value }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <div className="grid grid-cols-2 gap-2">
            <input type="number" step="0.1" min="0" max="5" placeholder="Rating Maps" value={leadForm.google_rating} onChange={e => setLeadForm(f => ({ ...f, google_rating: e.target.value }))}
              className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
            <input type="number" min="0" placeholder="Jumlah ulasan" value={leadForm.review_count} onChange={e => setLeadForm(f => ({ ...f, review_count: e.target.value }))}
              className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          </div>
        </div>
      </Modal>

      <Modal open={scoreModal.open} title="Adjustment Score" confirmLabel="Simpan" onConfirm={saveScoreAdjustment} onCancel={() => setScoreModal({ open: false, lead: null })}>
        <div className="space-y-3">
          <p className="text-xs text-gray-500">{scoreModal.lead?.business_name}</p>
          <label className="block text-xs font-semibold text-gray-500">Adjustment (-50 sampai +50)</label>
          <input type="number" min={-50} max={50} value={scoreForm.adjustment} onChange={e => setScoreForm(f => ({ ...f, adjustment: Number(e.target.value) }))}
            className="w-full px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition" />
          <label className="block text-xs font-semibold text-gray-500">Alasan</label>
          <textarea value={scoreForm.reason} onChange={e => setScoreForm(f => ({ ...f, reason: e.target.value }))}
            className="w-full min-h-[90px] px-3 py-2.5 border border-gray-200 dark:border-gray-700 rounded-xl text-sm bg-white dark:bg-neutral-800 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-amber-300 transition"
            placeholder="Contoh: prospek sudah minta proposal lewat WA." />
        </div>
      </Modal>
    </div>
  );
}
