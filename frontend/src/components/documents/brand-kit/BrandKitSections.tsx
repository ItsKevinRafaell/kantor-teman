"use client";
import NativeSelect from "../../ui/NativeSelect";

import { useState } from "react";
import { Plus, Trash2, Copy, Check } from "lucide-react";

interface BrandAsset {
  id: string;
  asset_type: string;
  name: string;
  value: string | null;
  file_url: string | null;
  position: number;
  asset_metadata: string | null;
}

// ─── Company Info ─────────────────────────────────────────────────────────

interface CompanyInfoSectionProps {
  assets: BrandAsset[];
  onSave: (a: Partial<BrandAsset> & { asset_type: string; name: string }, id?: string) => Promise<void>;
  saving: boolean;
}

export function CompanyInfoSection({ assets, onSave, saving }: CompanyInfoSectionProps) {
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
                <textarea key={asset?.value} defaultValue={asset?.value || ""} onBlur={e => handleBlur(f.type, f.label, e.target.value)}
                  placeholder={f.placeholder} rows={3} disabled={saving}
                  className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-800 resize-none focus:outline-none focus:ring-2 focus:ring-amber-400/50" />
              ) : (
                <input key={asset?.value} type="text" defaultValue={asset?.value || ""} onBlur={e => handleBlur(f.type, f.label, e.target.value)}
                  placeholder={f.placeholder} disabled={saving}
                  className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-amber-400/50" />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ─── Color Section ────────────────────────────────────────────────────────

interface ColorSectionProps {
  colors: BrandAsset[];
  copiedId: string | null;
  onCopy: (v: string, id: string) => void;
  onSave: (a: Partial<BrandAsset> & { asset_type: string; name: string }, id?: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  saving: boolean;
}

export function ColorSection({ colors, copiedId, onCopy, onSave, onDelete, saving }: ColorSectionProps) {
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
          <button disabled={saving || !newName.trim() || !/^#[0-9a-f]{6}$/i.test(newHex)}
            onClick={async () => { await onSave({ asset_type: "color", name: newName, value: newHex, position: colors.length }); setNewName(""); setNewHex("#000000"); setAdding(false); }}
            className="text-xs font-bold px-4 py-2 rounded-lg bg-green-500 hover:bg-green-600 text-white disabled:opacity-50">Simpan</button>
        </div>
      )}

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {colors.map(c => (
          <div key={c.id} className="border border-[var(--border-default)] rounded-xl p-3 flex items-center gap-3">
            <div className="w-14 h-14 rounded-lg border border-gray-200 dark:border-neutral-700 shrink-0" style={{ backgroundColor: c.value || "#000" }} />
            <div className="flex-1 min-w-0">
              <input defaultValue={c.name}
                onBlur={e => e.target.value !== c.name && onSave({ asset_type: "color", name: e.target.value, value: c.value, position: c.position }, c.id)}
                className="w-full text-sm font-semibold bg-transparent border-none outline-none text-neutral-800 dark:text-neutral-100" />
              <input defaultValue={c.value || ""}
                onBlur={e => e.target.value !== c.value && /^#[0-9a-f]{6}$/i.test(e.target.value) && onSave({ asset_type: "color", name: c.name, value: e.target.value, position: c.position }, c.id)}
                className="w-full text-xs font-mono text-gray-500 bg-transparent border-none outline-none" />
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

// ─── Font Section ──────────────────────────────────────────────────────────

interface FontSectionProps {
  fonts: BrandAsset[];
  onSave: (a: Partial<BrandAsset> & { asset_type: string; name: string }, id?: string) => Promise<void>;
  saving: boolean;
}

export function FontSection({ fonts, onSave, saving }: FontSectionProps) {
  return (
    <section className="bg-white dark:bg-neutral-900 rounded-2xl border border-[var(--border-default)] p-6">
      <h2 className="text-sm font-bold uppercase tracking-wider text-neutral-700 dark:text-neutral-300 mb-4">Typography</h2>
      <div className="grid md:grid-cols-2 gap-4">
        {fonts.map(f => {
          const meta = (() => { try { return JSON.parse(f.asset_metadata || "{}"); } catch { return {}; } })();
          return (
            <div key={f.id} className="border border-[var(--border-default)] rounded-xl p-4">
              <div className="text-xs text-gray-500 uppercase tracking-wide font-bold mb-2">{f.name}</div>
              <input defaultValue={f.value || ""}
                onBlur={e => e.target.value !== f.value && onSave({ asset_type: "font", name: f.name, value: e.target.value, position: f.position, asset_metadata: f.asset_metadata }, f.id)}
                placeholder="Nama font (mis. Fredoka)"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 mb-2" />
              <input defaultValue={meta.weight || ""}
                onBlur={e => { const newMeta = { ...meta, weight: e.target.value }; onSave({ asset_type: "font", name: f.name, value: f.value, position: f.position, asset_metadata: JSON.stringify(newMeta) }, f.id); }}
                placeholder="Weight (400/700)"
                className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 mb-3" />
              <div className="px-4 py-3 bg-[var(--bg-canvas)] dark:bg-neutral-800 rounded-lg text-neutral-800 dark:text-neutral-100"
                style={{ fontFamily: `"${f.value}", ${meta.fallback || "sans-serif"}`, fontWeight: meta.weight || 400 }}>
                The quick brown fox jumps over the lazy dog
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ─── Template Section ──────────────────────────────────────────────────────

interface TemplateSectionProps {
  templates: BrandAsset[];
  copiedId: string | null;
  onCopy: (v: string, id: string) => void;
  onSave: (a: Partial<BrandAsset> & { asset_type: string; name: string }, id?: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  saving: boolean;
}

export function TemplateSection({ templates, copiedId, onCopy, onSave, onDelete, saving }: TemplateSectionProps) {
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
            <NativeSelect value={newType} onChange={setNewType} clearable={false} options={["color","font","logo","other"].map(x=>({value:x,label:x}))} />
          </div>
          <textarea placeholder="Isi template..." value={newValue} onChange={e => setNewValue(e.target.value)} rows={3}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 resize-none" />
          <button disabled={saving || !newName.trim() || !newValue.trim()}
            onClick={async () => { await onSave({ asset_type: newType, name: newName, value: newValue, position: templates.length }); setNewName(""); setNewValue(""); setNewType("custom"); setAdding(false); }}
            className="text-xs font-bold px-4 py-2 rounded-lg bg-green-500 hover:bg-green-600 text-white disabled:opacity-50">Simpan</button>
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
                <input defaultValue={t.name}
                  onBlur={e => e.target.value !== t.name && onSave({ asset_type: t.asset_type, name: e.target.value, value: t.value, position: t.position }, t.id)}
                  className="w-full text-sm font-semibold bg-transparent border-none outline-none text-neutral-800 dark:text-neutral-100" />
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
            <textarea defaultValue={t.value || ""}
              onBlur={e => e.target.value !== t.value && onSave({ asset_type: t.asset_type, name: t.name, value: e.target.value, position: t.position }, t.id)}
              rows={2}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 resize-none" />
          </div>
        ))}
      </div>
    </section>
  );
}