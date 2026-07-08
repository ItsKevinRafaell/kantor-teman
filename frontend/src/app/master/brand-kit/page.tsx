"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import { Plus, Trash2, Copy, Upload, Check, Download } from "lucide-react";
import ConfirmModal from "../../../components/ConfirmModal";
import { CompanyInfoSection, ColorSection, FontSection, TemplateSection } from "../../../components/documents/brand-kit/BrandKitSections";

interface BrandAsset {
  id: string;
  asset_type: string;
  name: string;
  value: string | null;
  file_url: string | null;
  position: number;
  asset_metadata: string | null;
}

interface BrandKit {
  id: string;
  kit_name: string;
  is_active: boolean;
  created_at: string;
  assets: BrandAsset[];
  default_document_asset_id?: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Six canonical logo slots — three shapes × two colour variants. Each
// identity should pick a default that Document Generator uses for PDFs.
const LOGO_SLOTS: Array<{ type: string; label: string; desc: string; shape: "primary" | "secondary" | "icon"; color: "yellow" | "white" }> = [
  { type: "logo_primary_yellow",   shape: "primary",   color: "yellow", label: "Primary lockup — kuning",  desc: "Stacked lockup di latar terang (form, dokumen, marketing)" },
  { type: "logo_primary_white",    shape: "primary",   color: "white",  label: "Primary lockup — putih",   desc: "Versi putih untuk latar gelap (header kontras tinggi)" },
  { type: "logo_secondary_yellow", shape: "secondary", color: "yellow", label: "Secondary lockup — kuning",desc: "Horizontal lockup untuk sidebar / navbar sempit" },
  { type: "logo_secondary_white",  shape: "secondary", color: "white",  label: "Secondary lockup — putih", desc: "Horizontal lockup versi putih" },
  { type: "brandmark_yellow",      shape: "icon",      color: "yellow", label: "Brandmark icon — kuning",  desc: "Ikon saja untuk favicon, avatar, watermark" },
  { type: "brandmark_white",       shape: "icon",      color: "white",  label: "Brandmark icon — putih",   desc: "Brandmark putih untuk latar gelap" },
];

export default function BrandKitPage() {
  const [kit, setKit] = useState<BrandKit | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [confirmState, setConfirmState] = useState<{ open: boolean; title: string; message: string; onConfirm: () => void }>({ open: false, title: "", message: "", onConfirm: () => {} });

  const fetchKit = useCallback(async () => {
    try {
      const res = await apiFetch("/api/brand-kit");
      if (res.ok) setKit(await res.json());
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchKit(); }, [fetchKit]);

  function showToast(message: string, type: "success" | "error" = "success") {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }

  async function uploadLogo(file: File, type: string, label: string) {
    if (file.size > 2 * 1024 * 1024) { showToast("File terlalu besar (max 2MB)", "error"); return; }
    const existing = kit?.assets.find(a => a.asset_type === type);
    const fd = new FormData();
    fd.append("file", file); fd.append("asset_type", type); fd.append("name", label);
    if (existing) fd.append("asset_id", existing.id);
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/brand-assets/upload`, { method: "POST", body: fd, credentials: "include" });
      if (!res.ok) throw new Error();
      await fetchKit(); showToast("Logo diupload");
    } catch { showToast("Upload gagal", "error"); } finally { setSaving(false); }
  }

  async function saveAsset(asset: Partial<BrandAsset> & { asset_type: string; name: string }, id?: string) {
    setSaving(true);
    try {
      const url = id ? `/api/brand-assets/${id}` : `/api/brand-assets`;
      const method = id ? "PUT" : "POST";
      const res = await apiFetch(url, { method, body: JSON.stringify(asset) });
      if (!res.ok) throw new Error();
      await fetchKit();
    } catch { showToast("Gagal simpan", "error"); } finally { setSaving(false); }
  }

  async function setDefaultAsset(id: string) {
    setSaving(true);
    try {
      const res = await apiFetch("/api/brand-kit", {
        method: "PUT",
        body: JSON.stringify({ default_document_asset_id: id }),
      });
      if (!res.ok) throw new Error();
      await fetchKit();
      showToast("Default logo untuk dokumen diperbarui");
    } catch {
      showToast("Gagal set default", "error");
    } finally {
      setSaving(false);
    }
  }

  async function deleteAsset(id: string) {
    setConfirmState({
      open: true, title: "Hapus Asset", message: "Yakin mau hapus asset ini?",
      onConfirm: async () => {
        try {
          const res = await apiFetch(`/api/brand-assets/${id}`, { method: "DELETE" });
          if (!res.ok && res.status !== 204) throw new Error();
          await fetchKit(); showToast("Dihapus");
        } catch { showToast("Gagal hapus", "error"); }
      },
    });
  }

  function copy(value: string, id: string) {
    navigator.clipboard.writeText(value); setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  }

  if (loading) return <div className="p-8 text-sm text-gray-500">Memuat brand kit...</div>;
  if (!kit) return <div className="p-8 text-sm text-gray-500">Brand kit tidak ditemukan.</div>;

  const logos = kit.assets.filter(a =>
    ["logo_primary_yellow", "logo_primary_white",
     "logo_secondary_yellow", "logo_secondary_white",
     "brandmark_yellow", "brandmark_white"].includes(a.asset_type),
  );
  const colors = kit.assets.filter(a => a.asset_type === "color").sort((a, b) => a.position - b.position);
  const fonts = kit.assets.filter(a => a.asset_type === "font").sort((a, b) => a.position - b.position);
  const templates = kit.assets.filter(a => ["template_sosmed", "template_proposal", "tagline", "custom"].includes(a.asset_type));

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Brand Kit</h1>
        <p className="text-sm text-gray-500 mt-1">{kit.kit_name} — single source of truth untuk semua tools.</p>
      </div>

      {/* LOGO SECTION — 6 slots + default selector */}
      <section className="bg-white dark:bg-neutral-900 rounded-2xl border border-[var(--border-default)] p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-neutral-700 dark:text-neutral-300">Logo (6 slot)</h2>
            <p className="text-xs text-gray-500 mt-1">Upload keenam varian, lalu pilih satu sebagai default untuk dokumen PDF.</p>
          </div>
          <div className="text-xs text-gray-500">
            Default saat ini: <span className="font-semibold text-neutral-800 dark:text-neutral-100">
              {logos.find(l => l.id === kit.default_document_asset_id)?.name ?? "— otomatis"}
            </span>
          </div>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {LOGO_SLOTS.map(slot => {
            const asset = logos.find(a => a.asset_type === slot.type);
            const isDefault = kit.default_document_asset_id === asset?.id;
            return (
              <div key={slot.type} className={`border rounded-xl p-4 ${isDefault ? "border-amber-500 ring-1 ring-amber-200" : "border-[var(--border-default)]"}`}>
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{slot.label}</div>
                  {isDefault && (
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500 text-white">Default</span>
                  )}
                </div>
                <div className="text-xs text-gray-500 mb-3">{slot.desc}</div>
                <div className={`aspect-square rounded-lg border border-dashed flex items-center justify-center mb-3 overflow-hidden ${
                  slot.color === "white"
                    ? "bg-neutral-800 dark:bg-neutral-950 border-gray-600"
                    : "bg-[var(--bg-canvas)] dark:bg-neutral-800 border-gray-300 dark:border-neutral-700"
                }`}>
                  {asset?.file_url ? (
                    <img src={`${API_BASE}${asset.file_url}`} alt={slot.label} className="max-w-full max-h-full object-contain p-2" />
                  ) : (
                    <span className={`text-xs ${slot.color === "white" ? "text-neutral-500" : "text-gray-400"}`}>Belum diupload</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <label className="flex-1 cursor-pointer text-xs font-bold py-2 px-3 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-center transition-colors">
                    <Upload size={12} className="inline mr-1" />
                    {asset?.file_url ? "Ganti" : "Upload"}
                    <input type="file" accept=".png,.jpg,.jpeg,.svg,.webp,.ico" className="hidden"
                      onChange={e => e.target.files?.[0] && uploadLogo(e.target.files[0], slot.type, slot.label)} />
                  </label>
                  {asset?.file_url && (
                    <>
                      <a href={`${API_BASE}${asset.file_url}`} download
                        className="text-xs font-bold py-2 px-3 rounded-lg border border-gray-300 dark:border-neutral-700 hover:bg-gray-100 dark:hover:bg-neutral-800 transition-colors">
                        <Download size={12} />
                      </a>
                      <button
                        onClick={() => setDefaultAsset(asset.id)}
                        disabled={isDefault || saving}
                        className={`text-xs font-bold py-2 px-3 rounded-lg transition-colors ${
                          isDefault
                            ? "bg-amber-100 text-amber-700 cursor-default"
                            : "border border-amber-300 text-amber-700 hover:bg-amber-50"
                        }`}>
                        {isDefault ? "Default" : "Set Default"}
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Extracted sections */}
      <CompanyInfoSection assets={kit.assets} onSave={saveAsset} saving={saving} />
      <ColorSection colors={colors} copiedId={copiedId} onCopy={copy} onSave={saveAsset} onDelete={deleteAsset} saving={saving} />
      <FontSection fonts={fonts} onSave={saveAsset} saving={saving} />
      <TemplateSection templates={templates} copiedId={copiedId} onCopy={copy} onSave={saveAsset} onDelete={deleteAsset} saving={saving} />

      {toast && (
        <div className={`fixed bottom-6 right-6 px-4 py-3 rounded-xl shadow-lg text-sm font-semibold z-50 ${toast.type === "success" ? "bg-green-500 text-white" : "bg-red-500 text-white"}`}>
          {toast.message}
        </div>
      )}
      <ConfirmModal open={confirmState.open} onClose={() => setConfirmState(s => ({ ...s, open: false }))}
        onConfirm={confirmState.onConfirm} title={confirmState.title} message={confirmState.message} />
    </div>
  );
}