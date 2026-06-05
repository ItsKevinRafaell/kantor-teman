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
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const LOGO_SLOTS = [
  { type: "logo_primary", label: "Primary (Stacked)", desc: "Logo utama untuk konteks formal" },
  { type: "logo_secondary", label: "Secondary (Horizontal)", desc: "Untuk navbar / header sempit" },
  { type: "brandmark", label: "Brandmark / Icon", desc: "Untuk favicon, avatar sosmed" },
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

  const logos = kit.assets.filter(a => ["logo_primary", "logo_secondary", "brandmark"].includes(a.asset_type));
  const colors = kit.assets.filter(a => a.asset_type === "color").sort((a, b) => a.position - b.position);
  const fonts = kit.assets.filter(a => a.asset_type === "font").sort((a, b) => a.position - b.position);
  const templates = kit.assets.filter(a => ["template_sosmed", "template_proposal", "tagline", "custom"].includes(a.asset_type));

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Brand Kit</h1>
        <p className="text-sm text-gray-500 mt-1">{kit.kit_name} — single source of truth untuk semua tools.</p>
      </div>

      {/* LOGO SECTION */}
      <section className="bg-white dark:bg-neutral-900 rounded-2xl border border-[var(--border-default)] p-6">
        <h2 className="text-sm font-bold uppercase tracking-wider text-neutral-700 dark:text-neutral-300 mb-4">Logo</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {LOGO_SLOTS.map(slot => {
            const asset = logos.find(a => a.asset_type === slot.type);
            return (
              <div key={slot.type} className="border border-[var(--border-default)] rounded-xl p-4">
                <div className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{slot.label}</div>
                <div className="text-xs text-gray-500 mb-3">{slot.desc}</div>
                <div className="aspect-square bg-[var(--bg-canvas)] dark:bg-neutral-800 rounded-lg border border-dashed border-gray-300 dark:border-neutral-700 flex items-center justify-center mb-3 overflow-hidden">
                  {asset?.file_url ? (
                    <img src={`${API_BASE}${asset.file_url}`} alt={slot.label} className="max-w-full max-h-full object-contain" />
                  ) : (
                    <span className="text-xs text-gray-400">Belum diupload</span>
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
                    <a href={`${API_BASE}${asset.file_url}`} download
                      className="text-xs font-bold py-2 px-3 rounded-lg border border-gray-300 dark:border-neutral-700 hover:bg-gray-100 dark:hover:bg-neutral-800 transition-colors">
                      <Download size={12} />
                    </a>
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