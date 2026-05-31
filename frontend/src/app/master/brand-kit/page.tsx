"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import { Plus, Trash2, Copy, Upload, Check, Download } from "lucide-react";
import ConfirmModal from "../../../components/ConfirmModal";

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
    if (file.size > 2 * 1024 * 1024) {
      showToast("File terlalu besar (max 2MB)", "error");
      return;
    }
    const existing = kit?.assets.find(a => a.asset_type === type);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("asset_type", type);
    fd.append("name", label);
    if (existing) fd.append("asset_id", existing.id);

    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/brand-assets/upload`, {
        method: "POST",
        body: fd,
        credentials: "include",
      });
      if (!res.ok) throw new Error();
      await fetchKit();
      showToast("Logo diupload");
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
      open: true,
      title: "Hapus Asset",
      message: "Yakin mau hapus asset ini?",
      onConfirm: async () => {
        try {
          const res = await apiFetch(`/api/brand-assets/${id}`, { method: "DELETE" });
          if (!res.ok && res.status !== 204) throw new Error();
          await fetchKit();
          showToast("Dihapus");
        } catch { showToast("Gagal hapus", "error"); }
      },
    });
  }

  function copy(value: string, id: string) {
    navigator.clipboard.writeText(value);
    setCopiedId(id);
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
                    <input
                      type="file"
                      accept=".png,.jpg,.jpeg,.svg,.webp,.ico"
                      className="hidden"
                      onChange={e => e.target.files?.[0] && uploadLogo(e.target.files[0], slot.type, slot.label)}
                    />
                  </label>
                  {asset?.file_url && (
                    <a
                      href={`${API_BASE}${asset.file_url}`}
                      download
                      className="text-xs font-bold py-2 px-3 rounded-lg border border-gray-300 dark:border-neutral-700 hover:bg-gray-100 dark:hover:bg-neutral-800 transition-colors"
                    >
                      <Download size={12} />
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* COMPANY INFO */}
      <CompanyInfoSection assets={kit.assets} onSave={saveAsset} saving={saving} />

      {/* COLOR PALETTE */}
      <ColorSection
        colors={colors}
        copiedId={copiedId}
        onCopy={copy}
        onSave={saveAsset}
        onDelete={deleteAsset}
        saving={saving}
      />

      {/* TYPOGRAPHY */}
      <FontSection fonts={fonts} onSave={saveAsset} saving={saving} />

      {/* TEMPLATES */}
      <TemplateSection
        templates={templates}
        copiedId={copiedId}
        onCopy={copy}
        onSave={saveAsset}
        onDelete={deleteAsset}
        saving={saving}
      />

      {toast && (
        <div className={`fixed bottom-6 right-6 px-4 py-3 rounded-xl shadow-lg text-sm font-semibold z-50 ${
          toast.type === "success" ? "bg-green-500 text-white" : "bg-red-500 text-white"
        }`}>
          {toast.message}
        </div>
      )}
      <ConfirmModal
        open={confirmState.open}
        onClose={() => setConfirmState(s => ({ ...s, open: false }))}
        onConfirm={confirmState.onConfirm}
        title={confirmState.title}
        message={confirmState.message}
      />
    </div>
  );
}

function CompanyInfoSection({ assets, onSave, saving }: {
  assets: BrandAsset[];
  onSave: (a: Partial<BrandAsset> & { asset_type: string; name: string }, id?: string) => Promise<void>;
  saving: boolean;
}) {
  const FIELDS = [
    { type: "company_address", label: "Alamat Perusahaan", placeholder: "Jl. Contoh No. 1, Jakarta", multiline: true },
    { type: "company_phone", label: "Telepon Perusahaan", placeholder: "+62 812 3456 7890", multiline: false },
    { type: "company_email", label: "Email Perusahaan", placeholder: "hello@perusahaan.com", multiline: false },
  ];

  async function handleBlur(type: string, label: string, newVal: string) {
    const existing = assets.find(a => a.asset_type === type);
    if (existing) {
      if (newVal !== (existing.value || "")) await onSave({ asset_type: type, name: label, value: newVal, position: existing.position }, existing.id);
    } else if (newVal.trim()) {
      await onSave({ asset_type: type, name: label, value: newVal, position: 0 });
    }
  }

  return (
    <section className="bg-white dark:bg-neutral-900 rounded-2xl border border-[var(--border-default)] p-6">
      <h2 className="text-sm font-bold uppercase tracking-wider text-neutral-700 dark:text-neutral-300 mb-1">Info Perusahaan</h2>
      <p className="text-xs text-gray-500 mb-4">Digunakan otomatis di semua dokumen PDF (invoice, kontrak, proposal, dll).</p>
      <div className="grid md:grid-cols-3 gap-4">
        {FIELDS.map(f => {
          const asset = assets.find(a => a.asset_type === f.type);
          return (
            <div key={f.type}>
              <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{f.label}</label>
              {f.multiline ? (
                <textarea
                  key={asset?.value}
                  defaultValue={asset?.value || ""}
                  onBlur={e => handleBlur(f.type, f.label, e.target.value)}
                  placeholder={f.placeholder}
                  rows={3}
                  disabled={saving}
                  className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-800 resize-none focus:outline-none focus:ring-2 focus:ring-amber-400/50"
                />
              ) : (
                <input
                  key={asset?.value}
                  type="text"
                  defaultValue={asset?.value || ""}
                  onBlur={e => handleBlur(f.type, f.label, e.target.value)}
                  placeholder={f.placeholder}
                  disabled={saving}
                  className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-amber-400/50"
                />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ColorSection({ colors, copiedId, onCopy, onSave, onDelete, saving }: {
  colors: BrandAsset[];
  copiedId: string | null;
  onCopy: (v: string, id: string) => void;
  onSave: (a: Partial<BrandAsset> & { asset_type: string; name: string }, id?: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  saving: boolean;
}) {
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [newHex, setNewHex] = useState("#000000");

  return (
    <section className="bg-white dark:bg-neutral-900 rounded-2xl border border-[var(--border-default)] p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-bold uppercase tracking-wider text-neutral-700 dark:text-neutral-300">Color Palette</h2>
        <button onClick={() => setAdding(!adding)} className="text-xs font-bold px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white">
          <Plus size={12} className="inline mr-1" /> Add Color
        </button>
      </div>

      {adding && (
        <div className="flex gap-2 mb-4 p-3 bg-gray-50 dark:bg-neutral-800 rounded-lg">
          <input type="text" placeholder="Nama warna" value={newName} onChange={e => setNewName(e.target.value)}
            className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900" />
          <input type="text" placeholder="#hex" value={newHex} onChange={e => setNewHex(e.target.value)}
            className="w-28 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 font-mono" />
          <input type="color" value={newHex} onChange={e => setNewHex(e.target.value)} className="w-10 h-10 rounded-lg cursor-pointer" />
          <button
            disabled={saving || !newName.trim() || !/^#[0-9a-f]{6}$/i.test(newHex)}
            onClick={async () => {
              await onSave({ asset_type: "color", name: newName, value: newHex, position: colors.length });
              setNewName(""); setNewHex("#000000"); setAdding(false);
            }}
            className="text-xs font-bold px-4 py-2 rounded-lg bg-green-500 hover:bg-green-600 text-white disabled:opacity-50"
          >
            Simpan
          </button>
        </div>
      )}

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {colors.map(c => (
          <div key={c.id} className="border border-[var(--border-default)] rounded-xl p-3 flex items-center gap-3">
            <div className="w-14 h-14 rounded-lg border border-gray-200 dark:border-neutral-700 shrink-0" style={{ backgroundColor: c.value || "#000" }} />
            <div className="flex-1 min-w-0">
              <input
                defaultValue={c.name}
                onBlur={e => e.target.value !== c.name && onSave({ asset_type: "color", name: e.target.value, value: c.value, position: c.position }, c.id)}
                className="w-full text-sm font-semibold bg-transparent border-none outline-none text-neutral-800 dark:text-neutral-100"
              />
              <input
                defaultValue={c.value || ""}
                onBlur={e => e.target.value !== c.value && /^#[0-9a-f]{6}$/i.test(e.target.value) && onSave({ asset_type: "color", name: c.name, value: e.target.value, position: c.position }, c.id)}
                className="w-full text-xs font-mono text-gray-500 bg-transparent border-none outline-none"
              />
            </div>
            <button onClick={() => c.value && onCopy(c.value, c.id)} className="p-2 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-lg" title="Copy hex">
              {copiedId === c.id ? <Check size={14} className="text-green-500" /> : <Copy size={14} className="text-gray-400" />}
            </button>
            <button onClick={() => onDelete(c.id)} className="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg" title="Hapus">
              <Trash2 size={14} className="text-red-400" />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

function FontSection({ fonts, onSave, saving }: {
  fonts: BrandAsset[];
  onSave: (a: Partial<BrandAsset> & { asset_type: string; name: string }, id?: string) => Promise<void>;
  saving: boolean;
}) {
  return (
    <section className="bg-white dark:bg-neutral-900 rounded-2xl border border-[var(--border-default)] p-6">
      <h2 className="text-sm font-bold uppercase tracking-wider text-neutral-700 dark:text-neutral-300 mb-4">Typography</h2>
      <div className="grid md:grid-cols-2 gap-4">
        {fonts.map(f => {
          const meta = (() => { try { return JSON.parse(f.asset_metadata || "{}"); } catch { return {}; } })();
          return (
            <div key={f.id} className="border border-[var(--border-default)] rounded-xl p-4">
              <div className="text-xs text-gray-500 uppercase tracking-wide font-bold mb-2">{f.name}</div>
              <input
                defaultValue={f.value || ""}
                onBlur={e => e.target.value !== f.value && onSave({ asset_type: "font", name: f.name, value: e.target.value, position: f.position, asset_metadata: f.asset_metadata }, f.id)}
                placeholder="Nama font (mis. Fredoka)"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 mb-2"
              />
              <input
                defaultValue={meta.weight || ""}
                onBlur={e => {
                  const newMeta = { ...meta, weight: e.target.value };
                  onSave({ asset_type: "font", name: f.name, value: f.value, position: f.position, asset_metadata: JSON.stringify(newMeta) }, f.id);
                }}
                placeholder="Weight (400/700)"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 mb-3"
              />
              <div
                className="px-4 py-3 bg-[var(--bg-canvas)] dark:bg-neutral-800 rounded-lg text-neutral-800 dark:text-neutral-100"
                style={{ fontFamily: `"${f.value}", ${meta.fallback || "sans-serif"}`, fontWeight: meta.weight || 400 }}
              >
                The quick brown fox jumps over the lazy dog
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function TemplateSection({ templates, copiedId, onCopy, onSave, onDelete, saving }: {
  templates: BrandAsset[];
  copiedId: string | null;
  onCopy: (v: string, id: string) => void;
  onSave: (a: Partial<BrandAsset> & { asset_type: string; name: string }, id?: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  saving: boolean;
}) {
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [newValue, setNewValue] = useState("");
  const [newType, setNewType] = useState("custom");

  return (
    <section className="bg-white dark:bg-neutral-900 rounded-2xl border border-[var(--border-default)] p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-bold uppercase tracking-wider text-neutral-700 dark:text-neutral-300">Templates & Boilerplate</h2>
        <button onClick={() => setAdding(!adding)} className="text-xs font-bold px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white">
          <Plus size={12} className="inline mr-1" /> Add Template
        </button>
      </div>

      {adding && (
        <div className="space-y-2 mb-4 p-3 bg-gray-50 dark:bg-neutral-800 rounded-lg">
          <div className="flex gap-2">
            <input type="text" placeholder="Nama template" value={newName} onChange={e => setNewName(e.target.value)}
              className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900" />
            <select value={newType} onChange={e => setNewType(e.target.value)}
              className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900">
              <option value="custom">Custom</option>
              <option value="tagline">Tagline</option>
              <option value="template_sosmed">Sosmed</option>
              <option value="template_proposal">Proposal</option>
            </select>
          </div>
          <textarea placeholder="Isi template..." value={newValue} onChange={e => setNewValue(e.target.value)} rows={3}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 resize-none" />
          <button
            disabled={saving || !newName.trim() || !newValue.trim()}
            onClick={async () => {
              await onSave({ asset_type: newType, name: newName, value: newValue, position: templates.length });
              setNewName(""); setNewValue(""); setNewType("custom"); setAdding(false);
            }}
            className="text-xs font-bold px-4 py-2 rounded-lg bg-green-500 hover:bg-green-600 text-white disabled:opacity-50"
          >
            Simpan
          </button>
        </div>
      )}

      <div className="space-y-3">
        {templates.length === 0 && (
          <div className="text-sm text-gray-400 text-center py-8">Belum ada template. Klik "Add Template" di atas.</div>
        )}
        {templates.map(t => (
          <div key={t.id} className="border border-[var(--border-default)] rounded-xl p-4">
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="flex-1 min-w-0">
                <input
                  defaultValue={t.name}
                  onBlur={e => e.target.value !== t.name && onSave({ asset_type: t.asset_type, name: e.target.value, value: t.value, position: t.position }, t.id)}
                  className="w-full text-sm font-semibold bg-transparent border-none outline-none text-neutral-800 dark:text-neutral-100"
                />
                <span className="text-[10px] uppercase tracking-wide font-bold text-amber-600">{t.asset_type.replace("template_", "")}</span>
              </div>
              <div className="flex gap-1">
                <button onClick={() => t.value && onCopy(t.value, t.id)} className="p-2 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-lg">
                  {copiedId === t.id ? <Check size={14} className="text-green-500" /> : <Copy size={14} className="text-gray-400" />}
                </button>
                <button onClick={() => onDelete(t.id)} className="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg">
                  <Trash2 size={14} className="text-red-400" />
                </button>
              </div>
            </div>
            <textarea
              defaultValue={t.value || ""}
              onBlur={e => e.target.value !== t.value && onSave({ asset_type: t.asset_type, name: t.name, value: e.target.value, position: t.position }, t.id)}
              rows={2}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 resize-none"
            />
          </div>
        ))}
      </div>
    </section>
  );
}
