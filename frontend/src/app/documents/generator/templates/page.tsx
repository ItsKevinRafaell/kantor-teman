"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../../lib/api";
import { Plus, Pencil, Trash2, X } from "lucide-react";
import Toast from "../../../../components/Toast";
import ConfirmModal from "../../../../components/ConfirmModal";

interface DocTemplate {
  id: string;
  name: string;
  type: string;
  html_template: string;
  variables: string[];
  is_active: boolean;
  created_at: string;
}

const TYPES = [
  { value: "invoice", label: "Invoice" },
  { value: "proposal_pdf", label: "Proposal PDF" },
  { value: "surat_penawaran", label: "Surat Penawaran" },
  { value: "kontrak", label: "Kontrak / MoU" },
  { value: "custom", label: "Custom" },
];

const STARTER_VARIABLES: Record<string, string> = {
  invoice: "logo, nomor_invoice, tanggal, due_date, klien, alamat, phone, items_rows, total, terms, nama_perusahaan, alamat_perusahaan, phone_perusahaan, email_perusahaan, tagline",
  proposal_pdf: "logo, tanggal, valid_until, klien, alamat, phone, layanan, items_rows, total, scope, nama_perusahaan, alamat_perusahaan, phone_perusahaan, email_perusahaan, tagline",
  surat_penawaran: "logo, nomor, tanggal, klien, alamat, phone, perihal, items_rows, total, terms, nama_perusahaan, alamat_perusahaan, phone_perusahaan, email_perusahaan",
  kontrak: "logo, tanggal_mulai, tanggal_akhir, klien, alamat, phone, layanan, durasi, nilai_kontrak, scope, terms, nama_perusahaan, alamat_perusahaan, phone_perusahaan, email_perusahaan, tagline",
  custom: "",
};

const STARTER_TEMPLATES: Record<string, string> = {
  invoice: `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700&display=swap');
@page { size: A4; margin: 2cm; }
* { font-family: 'Noto Sans', sans-serif; box-sizing: border-box; }
body { color: #1f2937; line-height: 1.6; font-size: 12px; }
.header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #f59e0b; padding-bottom: 16px; margin-bottom: 24px; }
.header .info { text-align: right; }
.header .info h1 { font-size: 24px; color: #f59e0b; margin: 0 0 4px; }
.header .info p { margin: 2px 0; font-size: 11px; color: #4b5563; }
.meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
.meta-box h3 { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #6b7280; margin: 0 0 6px; font-weight: 700; }
.meta-box p { margin: 2px 0; font-size: 12px; }
.items { margin: 20px 0; }
.terms { margin-top: 20px; padding: 12px 16px; background: #f9fafb; border-left: 3px solid #f59e0b; border-radius: 0 8px 8px 0; font-size: 11px; color: #4b5563; }
.footer { margin-top: 40px; text-align: center; font-size: 10px; color: #9ca3af; border-top: 1px solid #e5e7eb; padding-top: 12px; }
</style></head><body>
<div class="header">
  <div>{{logo}}</div>
  <div class="info">
    <h1>INVOICE</h1>
    <p><strong>{{nomor_invoice}}</strong></p>
    <p>Tanggal: {{tanggal}}</p>
    <p>Jatuh Tempo: {{due_date}}</p>
  </div>
</div>
<div class="meta-grid">
  <div class="meta-box">
    <h3>Dari</h3>
    <p><strong>{{nama_perusahaan}}</strong></p>
    <p>{{alamat_perusahaan}}</p>
    <p>{{phone_perusahaan}}</p>
    <p>{{email_perusahaan}}</p>
  </div>
  <div class="meta-box">
    <h3>Kepada</h3>
    <p><strong>{{klien}}</strong></p>
    <p>{{alamat}}</p>
    <p>{{phone}}</p>
  </div>
</div>
<div class="items">{{items_rows}}</div>
<div class="terms"><strong>Syarat &amp; Ketentuan:</strong><br/>{{terms}}</div>
<div class="footer">{{nama_perusahaan}} &mdash; {{tagline}}</div>
</body></html>`,

  proposal_pdf: `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700&display=swap');
@page { size: A4; margin: 2cm; }
* { font-family: 'Noto Sans', sans-serif; box-sizing: border-box; }
body { color: #1f2937; line-height: 1.6; font-size: 12px; }
.header { border-bottom: 3px solid #f59e0b; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-end; }
.header h1 { font-size: 22px; color: #111827; margin: 8px 0 2px; }
.header .subtitle { font-size: 11px; color: #6b7280; }
.section { margin: 20px 0; }
.section h2 { font-size: 12px; color: #f59e0b; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; margin-bottom: 10px; font-weight: 700; }
.meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
.meta-box { padding: 12px; background: #f9fafb; border-radius: 8px; }
.meta-box h3 { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #6b7280; margin: 0 0 6px; font-weight: 700; }
.meta-box p { margin: 2px 0; }
.validity { background: #fef3c7; padding: 10px 14px; border-radius: 8px; font-size: 11px; color: #92400e; margin-top: 20px; }
.scope { background: #f9fafb; padding: 12px 16px; border-radius: 8px; font-size: 12px; white-space: pre-line; }
.footer { margin-top: 40px; text-align: center; font-size: 10px; color: #9ca3af; border-top: 1px solid #e5e7eb; padding-top: 12px; }
</style></head><body>
<div class="header">
  <div>
    {{logo}}
    <h1>PROPOSAL PENAWARAN</h1>
    <div class="subtitle">{{tanggal}} &nbsp;&middot;&nbsp; Berlaku hingga {{valid_until}}</div>
  </div>
</div>
<div class="meta-grid">
  <div class="meta-box">
    <h3>Dari</h3>
    <p><strong>{{nama_perusahaan}}</strong></p>
    <p>{{alamat_perusahaan}}</p>
    <p>{{phone_perusahaan}}</p>
    <p>{{email_perusahaan}}</p>
  </div>
  <div class="meta-box">
    <h3>Kepada</h3>
    <p><strong>{{klien}}</strong></p>
    <p>{{alamat}}</p>
    <p>{{phone}}</p>
    <p>Layanan: {{layanan}}</p>
  </div>
</div>
<div class="section">
  <h2>Layanan yang Ditawarkan</h2>
  {{items_rows}}
</div>
<div class="section">
  <h2>Lingkup Pekerjaan</h2>
  <div class="scope">{{scope}}</div>
</div>
<div class="validity">Proposal ini berlaku hingga <strong>{{valid_until}}</strong>. Setelah tanggal tersebut, harga dan ketersediaan dapat berubah.</div>
<div class="footer">{{nama_perusahaan}} &mdash; {{tagline}}</div>
</body></html>`,

  surat_penawaran: `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700&display=swap');
@page { size: A4; margin: 2cm; }
* { font-family: 'Noto Sans', sans-serif; box-sizing: border-box; }
body { color: #1f2937; line-height: 1.8; font-size: 12px; }
.kop { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f59e0b; padding-bottom: 12px; margin-bottom: 20px; }
.kop .company { text-align: right; font-size: 11px; color: #4b5563; line-height: 1.6; }
.kop .company strong { font-size: 13px; color: #111827; }
.nomor-box { font-size: 11px; color: #6b7280; margin-bottom: 20px; }
.recipient { margin: 16px 0; padding: 12px 16px; background: #f9fafb; border-radius: 8px; }
.recipient p { margin: 2px 0; }
.perihal { font-size: 13px; font-weight: 700; margin: 16px 0 8px; }
.items { margin: 20px 0; }
.terms { margin-top: 20px; padding: 12px 16px; background: #f9fafb; border-left: 3px solid #f59e0b; border-radius: 0 8px 8px 0; font-size: 11px; color: #4b5563; }
.signature { margin-top: 50px; display: flex; justify-content: flex-end; }
.signature .sig-block { text-align: center; }
.signature .sig-line { margin-top: 60px; border-top: 1px solid #1f2937; padding-top: 4px; font-size: 11px; min-width: 180px; }
</style></head><body>
<div class="kop">
  <div>{{logo}}</div>
  <div class="company">
    <strong>{{nama_perusahaan}}</strong><br/>
    {{alamat_perusahaan}}<br/>
    {{phone_perusahaan}} &nbsp;&middot;&nbsp; {{email_perusahaan}}
  </div>
</div>
<div class="nomor-box">
  No: <strong>{{nomor}}</strong><br/>
  Tanggal: {{tanggal}}
</div>
<div class="recipient">
  <p>Kepada Yth,</p>
  <p><strong>{{klien}}</strong></p>
  <p>{{alamat}}</p>
  <p>{{phone}}</p>
</div>
<p class="perihal">Perihal: {{perihal}}</p>
<p>Dengan hormat, bersama surat ini kami mengajukan penawaran jasa sebagai berikut:</p>
<div class="items">{{items_rows}}</div>
<div class="terms"><strong>Syarat &amp; Ketentuan:</strong><br/>{{terms}}</div>
<div class="signature">
  <div class="sig-block">
    <p>Hormat kami,</p>
    <div class="sig-line">{{nama_perusahaan}}</div>
  </div>
</div>
</body></html>`,

  kontrak: `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700&display=swap');
@page { size: A4; margin: 2cm; }
* { font-family: 'Noto Sans', sans-serif; box-sizing: border-box; }
body { color: #1f2937; line-height: 1.8; font-size: 12px; }
.header { text-align: center; border-bottom: 3px solid #f59e0b; padding-bottom: 16px; margin-bottom: 24px; }
.header h1 { font-size: 18px; margin: 8px 0 4px; letter-spacing: 2px; }
.header .subtitle { font-size: 11px; color: #6b7280; }
.section { margin: 20px 0; }
.section h2 { font-size: 12px; color: #f59e0b; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; margin-bottom: 10px; font-weight: 700; }
.parties { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0; }
.party { padding: 12px 16px; background: #f9fafb; border-radius: 8px; }
.party h3 { font-size: 10px; text-transform: uppercase; color: #6b7280; margin: 0 0 6px; font-weight: 700; }
.party p { margin: 2px 0; }
.highlight { background: #fef3c7; padding: 12px 16px; border-radius: 8px; font-size: 12px; margin: 12px 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.highlight .item label { font-size: 10px; text-transform: uppercase; color: #92400e; font-weight: 700; display: block; margin-bottom: 2px; }
.highlight .item span { font-weight: 700; color: #78350f; }
.scope { background: #f9fafb; padding: 12px 16px; border-radius: 8px; white-space: pre-line; }
.terms { font-size: 11px; color: #374151; white-space: pre-line; }
.signatures { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 60px; }
.sig-box { text-align: center; }
.sig-box .line { margin-top: 70px; border-top: 1px solid #1f2937; padding-top: 6px; font-size: 11px; }
.sig-box .role { font-size: 10px; color: #6b7280; margin-top: 2px; }
</style></head><body>
<div class="header">
  {{logo}}
  <h1>PERJANJIAN KERJA SAMA</h1>
  <div class="subtitle">Tanggal: {{tanggal_mulai}}</div>
</div>
<p>Pada hari ini, <strong>{{tanggal_mulai}}</strong>, telah disepakati perjanjian kerja sama antara:</p>
<div class="parties">
  <div class="party">
    <h3>Pihak Pertama (Penyedia Jasa)</h3>
    <p><strong>{{nama_perusahaan}}</strong></p>
    <p>{{alamat_perusahaan}}</p>
    <p>{{phone_perusahaan}}</p>
    <p>{{email_perusahaan}}</p>
  </div>
  <div class="party">
    <h3>Pihak Kedua (Klien)</h3>
    <p><strong>{{klien}}</strong></p>
    <p>{{alamat}}</p>
    <p>{{phone}}</p>
  </div>
</div>
<div class="highlight">
  <div class="item"><label>Layanan</label><span>{{layanan}}</span></div>
  <div class="item"><label>Durasi</label><span>{{durasi}}</span></div>
  <div class="item"><label>Nilai Kontrak</label><span>{{nilai_kontrak}}</span></div>
</div>
<div class="highlight" style="grid-template-columns: 1fr 1fr; margin-top: 0;">
  <div class="item"><label>Tanggal Mulai</label><span>{{tanggal_mulai}}</span></div>
  <div class="item"><label>Tanggal Selesai</label><span>{{tanggal_akhir}}</span></div>
</div>
<div class="section">
  <h2>Lingkup Pekerjaan</h2>
  <div class="scope">{{scope}}</div>
</div>
<div class="section">
  <h2>Syarat &amp; Ketentuan</h2>
  <div class="terms">{{terms}}</div>
</div>
<div class="signatures">
  <div class="sig-box">
    <div class="line">{{nama_perusahaan}}</div>
    <div class="role">Pihak Pertama</div>
  </div>
  <div class="sig-box">
    <div class="line">{{klien}}</div>
    <div class="role">Pihak Kedua</div>
  </div>
</div>
<div style="margin-top:30px;text-align:center;font-size:10px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:12px;">{{nama_perusahaan}} &mdash; {{tagline}}</div>
</body></html>`,

  custom: `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700&display=swap');
@page { size: A4; margin: 2cm; }
* { font-family: 'Noto Sans', sans-serif; box-sizing: border-box; }
body { color: #1f2937; line-height: 1.6; font-size: 12px; }
</style></head><body>
<p>Tulis konten dokumen di sini...</p>
</body></html>`,
};

export default function DocumentTemplatesPage() {
  const [templates, setTemplates] = useState<DocTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<DocTemplate | null>(null);
  const [form, setForm] = useState({ name: "", type: "invoice", html_template: "", variables: "" });
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [confirmState, setConfirmState] = useState<{ open: boolean; title: string; message: string; onConfirm: () => void }>({ open: false, title: "", message: "", onConfirm: () => {} });

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await apiFetch("/api/document-templates");
      if (res.ok) setTemplates(await res.json());
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchTemplates(); }, [fetchTemplates]);

  function openNew() {
    setEditing(null);
    setForm({ name: "", type: "invoice", html_template: STARTER_TEMPLATES["invoice"], variables: STARTER_VARIABLES["invoice"] });
    setModal(true);
  }

  function openEdit(t: DocTemplate) {
    setEditing(t);
    setForm({ name: t.name, type: t.type, html_template: t.html_template, variables: t.variables.join(", ") });
    setModal(true);
  }

  function handleTypeChange(newType: string) {
    setForm(prev => ({
      ...prev,
      type: newType,
      // Only auto-fill if HTML is still the starter or empty
      html_template: (!prev.html_template.trim() || Object.values(STARTER_TEMPLATES).includes(prev.html_template))
        ? (STARTER_TEMPLATES[newType] || "")
        : prev.html_template,
      variables: (!prev.variables.trim() || Object.values(STARTER_VARIABLES).includes(prev.variables))
        ? (STARTER_VARIABLES[newType] || "")
        : prev.variables,
    }));
  }

  async function handleSave() {
    if (!form.name.trim() || !form.html_template.trim()) return;
    setSaving(true);
    try {
      const vars = form.variables.split(",").map(v => v.trim()).filter(Boolean);
      const payload = { name: form.name, type: form.type, html_template: form.html_template, variables: vars };
      const url = editing ? `/api/document-templates/${editing.id}` : "/api/document-templates";
      const method = editing ? "PUT" : "POST";
      const res = await apiFetch(url, { method, body: JSON.stringify(payload) });
      if (!res.ok) throw new Error();
      await fetchTemplates();
      setModal(false);
      setToast({ message: editing ? "Template diupdate" : "Template dibuat", type: "success" });
    } catch { setToast({ message: "Gagal simpan", type: "error" }); }
    finally { setSaving(false); }
  }

  async function handleDelete(id: string) {
    setConfirmState({
      open: true,
      title: "Hapus Template",
      message: "Yakin mau hapus template ini?",
      onConfirm: async () => {
        const res = await apiFetch(`/api/document-templates/${id}`, { method: "DELETE" });
        if (res.ok || res.status === 204) {
          setTemplates(prev => prev.filter(t => t.id !== id));
          setToast({ message: "Template dihapus", type: "success" });
        }
      },
    });
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Document Templates</h1>
          <p className="text-sm text-gray-500 mt-1">Kelola template HTML untuk generate PDF.</p>
        </div>
        <button onClick={openNew}
          className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold rounded-lg transition-colors">
          <Plus size={14} /> Buat Template
        </button>
      </div>

      {loading ? <p className="text-sm text-gray-400">Memuat...</p> : (
        <div className="space-y-2">
          {templates.map(t => (
            <div key={t.id} className="flex items-center justify-between p-4 bg-white dark:bg-neutral-900 border border-[var(--border-default)] rounded-xl">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{t.name}</p>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 font-bold uppercase">{t.type}</span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">Variabel: {t.variables.length > 0 ? t.variables.join(", ") : "—"}</p>
              </div>
              <div className="flex gap-1 ml-3">
                <button onClick={() => openEdit(t)} className="p-2 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-lg"><Pencil size={14} className="text-gray-500" /></button>
                <button onClick={() => handleDelete(t.id)} className="p-2 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"><Trash2 size={14} className="text-red-400" /></button>
              </div>
            </div>
          ))}
          {templates.length === 0 && <p className="text-sm text-gray-400 text-center py-8">Belum ada template.</p>}
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-neutral-900 rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-xl">
            <div className="flex items-center justify-between p-5 border-b border-[var(--border-default)]">
              <h3 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">{editing ? "Edit Template" : "Buat Template"}</h3>
              <button onClick={() => setModal(false)} className="p-2 hover:bg-gray-100 dark:hover:bg-neutral-800 rounded-lg"><X size={18} /></button>
            </div>
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Nama Template</label>
                  <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Type</label>
                  <select value={form.type} onChange={e => handleTypeChange(e.target.value)}
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800">
                    {TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Variables (comma-separated)</label>
                <input type="text" value={form.variables} onChange={e => setForm({ ...form, variables: e.target.value })}
                  placeholder="klien, tanggal, total, items_rows"
                  className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 font-mono" />
              </div>
              <div>
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">HTML Template</label>
                  {STARTER_TEMPLATES[form.type] && (
                    <button type="button"
                      onClick={() => setForm(prev => ({ ...prev, html_template: STARTER_TEMPLATES[form.type], variables: STARTER_VARIABLES[form.type] || prev.variables }))}
                      className="text-[11px] text-amber-600 hover:text-amber-700 font-semibold">
                      Reset ke Starter Template
                    </button>
                  )}
                </div>
                <textarea value={form.html_template} onChange={e => setForm({ ...form, html_template: e.target.value })}
                  rows={16}
                  className="mt-1 w-full px-3 py-2 text-xs border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 font-mono resize-y" />
              </div>
            </div>
            <div className="flex justify-end gap-3 p-5 border-t border-[var(--border-default)]">
              <button onClick={() => setModal(false)} className="px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-lg">Batal</button>
              <button onClick={handleSave} disabled={saving || !form.name.trim() || !form.html_template.trim()}
                className="px-4 py-2 text-sm font-bold bg-amber-500 hover:bg-amber-600 text-white rounded-lg disabled:opacity-50">
                {saving ? "Menyimpan..." : "Simpan"}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
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
