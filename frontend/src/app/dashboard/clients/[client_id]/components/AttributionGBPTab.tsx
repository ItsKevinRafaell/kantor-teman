"use client";

import { useCallback, useEffect, useState } from "react";
import { Copy, Save } from "lucide-react";
import { apiFetch } from "../../../../../lib/api";

interface AttributionGBP {
  lead_id: number;
  canonical_landing_url: string | null;
  generated_url: string | null;
  ga4_measurement_id: string | null;
  conversion_event_name: string | null;
  conversion_event_verified: boolean;
  readiness_note: string | null;
}

const emptyForm = {
  canonical_landing_url: "",
  ga4_measurement_id: "",
  conversion_event_name: "",
  conversion_event_verified: false,
  readiness_note: "",
};

export default function AttributionGBPTab({ clientId, leadId }: { clientId: number; leadId: number | null }) {
  const [form, setForm] = useState(emptyForm);
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiFetch(`/api/clients/${clientId}/attribution-gbp`);
      if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.detail || "Gagal memuat Attribution GBP.");
      }
      const data: AttributionGBP = await response.json();
      setForm({
        canonical_landing_url: data.canonical_landing_url || "",
        ga4_measurement_id: data.ga4_measurement_id || "",
        conversion_event_name: data.conversion_event_name || "",
        conversion_event_verified: data.conversion_event_verified,
        readiness_note: data.readiness_note || "",
      });
      setGeneratedUrl(data.generated_url);
    } catch (error) {
      setFeedback({ type: "error", message: error instanceof Error ? error.message : "Gagal memuat data." });
    } finally {
      setLoading(false);
    }
  }, [clientId]);

  useEffect(() => { load(); }, [load]);

  async function save() {
    setSaving(true);
    setFeedback(null);
    try {
      const response = await apiFetch(`/api/clients/${clientId}/attribution-gbp`, {
        method: "PUT",
        body: JSON.stringify(form),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Gagal menyimpan Attribution GBP.");
      setGeneratedUrl(data.generated_url);
      setFeedback({ type: "success", message: "Bukti attribution dan URL tersimpan." });
    } catch (error) {
      setFeedback({ type: "error", message: error instanceof Error ? error.message : "Gagal menyimpan data." });
    } finally {
      setSaving(false);
    }
  }

  async function copyGeneratedUrl() {
    if (!generatedUrl) return;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard tidak tersedia di browser ini.");
      await navigator.clipboard.writeText(generatedUrl);
      setFeedback({ type: "success", message: "URL UTM berhasil disalin." });
    } catch (error) {
      setFeedback({ type: "error", message: error instanceof Error ? error.message : "URL gagal disalin." });
    }
  }

  if (loading) return <div className="p-6"><div className="h-44 bg-neutral-100 dark:bg-neutral-800 rounded-xl animate-pulse" /></div>;

  return (
    <div className="p-5 space-y-5">
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
        <p className="font-bold">Gerbang permanen: tidak mempublikasikan GBP</p>
        <p className="mt-1">Fitur ini tidak mengubah atau mempublikasikan link website GBP. Perubahan GBP terpisah; perlu akses manager terkonfirmasi dan URL kanonik disetujui Kevin.</p>
      </div>

      {!leadId ? (
        <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">Kontak ini belum memiliki relasi lead; attribution tidak dapat disimpan.</p>
      ) : (
        <>
          <div>
            <h2 className="text-base font-bold text-neutral-900 dark:text-neutral-50">Attribution GBP</h2>
            <p className="mt-0.5 text-xs text-neutral-500">Simpan hanya bukti yang sudah diverifikasi. Tidak ada data awal atau tebakan nama klien.</p>
          </div>
          {feedback && <p role="status" className={`rounded-lg px-3 py-2 text-sm ${feedback.type === "success" ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300" : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300"}`}>{feedback.message}</p>}
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block md:col-span-2"><span className="mb-1 block text-xs font-semibold text-neutral-600 dark:text-neutral-300">URL landing kanonik (HTTPS)</span><input className="input-field" value={form.canonical_landing_url} onChange={e => setForm({ ...form, canonical_landing_url: e.target.value })} placeholder="https://example.com/halaman" /></label>
            <label className="block"><span className="mb-1 block text-xs font-semibold text-neutral-600 dark:text-neutral-300">GA4 measurement ID terverifikasi</span><input className="input-field" value={form.ga4_measurement_id} onChange={e => setForm({ ...form, ga4_measurement_id: e.target.value })} placeholder="G-XXXXXXXX" /></label>
            <label className="block"><span className="mb-1 block text-xs font-semibold text-neutral-600 dark:text-neutral-300">Event konversi (opsional)</span><input className="input-field" value={form.conversion_event_name} onChange={e => setForm({ ...form, conversion_event_name: e.target.value })} placeholder="whatsapp_click" /></label>
            <label className="flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-200"><input type="checkbox" checked={form.conversion_event_verified} onChange={e => setForm({ ...form, conversion_event_verified: e.target.checked })} /> Event konversi sudah diverifikasi</label>
            <label className="block md:col-span-2"><span className="mb-1 block text-xs font-semibold text-neutral-600 dark:text-neutral-300">Catatan/evidence readiness</span><textarea className="input-field min-h-24" value={form.readiness_note} onChange={e => setForm({ ...form, readiness_note: e.target.value })} placeholder="Sumber dan tanggal verifikasi internal..." /></label>
          </div>
          <div className="rounded-xl border border-[var(--border-default)] bg-neutral-50 p-4 dark:bg-neutral-900/40">
            <p className="text-xs font-semibold text-neutral-600 dark:text-neutral-300">URL GBP UTM yang dihitung server</p>
            <p className="mt-2 break-all font-mono text-sm text-neutral-800 dark:text-neutral-100">{generatedUrl || "Simpan URL landing kanonik yang valid untuk menghasilkan URL."}</p>
            <button type="button" onClick={copyGeneratedUrl} disabled={!generatedUrl} className="btn-secondary mt-3 flex items-center gap-1.5 text-xs disabled:opacity-50"><Copy size={14} /> Salin URL</button>
          </div>
          <button type="button" onClick={save} disabled={saving || !form.canonical_landing_url.trim()} className="btn-primary flex items-center gap-1.5 text-xs disabled:opacity-50"><Save size={14} /> {saving ? "Menyimpan..." : "Simpan evidence"}</button>
        </>
      )}
    </div>
  );
}
