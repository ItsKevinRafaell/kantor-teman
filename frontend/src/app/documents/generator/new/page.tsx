"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../../lib/api";
import { ChevronRight, ChevronLeft, Download, Mail, Check } from "lucide-react";
import Toast from "../../../../components/Toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DocTemplate { id: string; name: string; type: string; variables: string[]; }
interface Lead { id: number; business_name: string; phone_number: string; address: string | null; product_interest: string | null; }
interface GeneratedDoc { id: string; file_url: string; template_name: string; }

const STEPS = ["Pilih Template", "Pilih Target", "Isi Variabel", "Preview", "Selesai"];

export default function DocumentNewPage() {
  const [step, setStep] = useState(0);
  const [templates, setTemplates] = useState<DocTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<DocTemplate | null>(null);
  const [targetType, setTargetType] = useState<"lead" | "empty">("empty");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [generating, setGenerating] = useState(false);
  const [generatedDoc, setGeneratedDoc] = useState<GeneratedDoc | null>(null);
  const [emailModal, setEmailModal] = useState(false);
  const [emailTo, setEmailTo] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  useEffect(() => {
    apiFetch("/api/document-templates").then(r => r.ok ? r.json() : []).then(setTemplates).catch(() => {});
    apiFetch("/api/leads?limit=200").then(r => r.ok ? r.json() : []).then(setLeads).catch(() => {});
  }, []);

  function selectTemplate(t: DocTemplate) {
    setSelectedTemplate(t);
    const vars: Record<string, string> = {};
    t.variables.forEach(v => { vars[v] = ""; });
    setVariables(vars);
  }

  function autoFillFromLead(lead: Lead) {
    setSelectedLead(lead);
    setVariables(prev => ({
      ...prev,
      klien: lead.business_name,
      nama: lead.business_name,
      alamat: lead.address || "",
      layanan: lead.product_interest || "",
      phone: lead.phone_number,
    }));
  }

  async function handleGenerate() {
    if (!selectedTemplate) return;
    setGenerating(true);
    try {
      const res = await apiFetch("/api/documents/generate", {
        method: "POST",
        body: JSON.stringify({
          template_id: selectedTemplate.id,
          target_type: targetType === "lead" && selectedLead ? "lead" : null,
          target_id: selectedLead ? String(selectedLead.id) : null,
          variables,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Generate gagal");
      }
      const data = await res.json();
      setGeneratedDoc({ id: data.document_id, file_url: data.file_url, template_name: data.template_name });
      setStep(4);
    } catch (e: unknown) {
      setToast({ message: e instanceof Error ? e.message : "Generate gagal", type: "error" });
    } finally { setGenerating(false); }
  }

  async function handleSendEmail() {
    if (!generatedDoc || !emailTo) return;
    setSendingEmail(true);
    try {
      const res = await apiFetch(`/api/documents/${generatedDoc.id}/email`, {
        method: "POST",
        body: JSON.stringify({ to_email: emailTo, subject: emailSubject || undefined }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Gagal kirim email");
      }
      setToast({ message: `Email terkirim ke ${emailTo}`, type: "success" });
      setEmailModal(false);
    } catch (e: unknown) {
      setToast({ message: e instanceof Error ? e.message : "Gagal kirim email", type: "error" });
    } finally { setSendingEmail(false); }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Generate Dokumen</h1>
        <p className="text-sm text-gray-500 mt-1">Buat PDF dari template dalam beberapa langkah.</p>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-1">
        {STEPS.map((s, i) => (
          <div key={i} className="flex items-center gap-1">
            <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold transition-colors ${i < step ? "bg-green-500 text-white" : i === step ? "bg-amber-500 text-white" : "bg-gray-200 dark:bg-neutral-700 text-gray-500"}`}>
              {i < step ? <Check size={12} /> : i + 1}
            </div>
            <span className={`text-xs font-medium hidden sm:block ${i === step ? "text-amber-600" : "text-gray-400"}`}>{s}</span>
            {i < STEPS.length - 1 && <div className="w-4 h-px bg-gray-200 dark:bg-neutral-700 mx-1" />}
          </div>
        ))}
      </div>

      {/* Step 0: Pick Template */}
      {step === 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Pilih Template</h2>
          {templates.length === 0 && <p className="text-sm text-gray-400">Belum ada template. Buat di halaman Templates dulu.</p>}
          {templates.map(t => (
            <button key={t.id} onClick={() => selectTemplate(t)}
              className={`w-full text-left p-4 rounded-xl border-2 transition-colors ${selectedTemplate?.id === t.id ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20" : "border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300"}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{t.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Variabel: {t.variables.join(", ") || "—"}</p>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 font-bold uppercase">{t.type}</span>
              </div>
            </button>
          ))}
          <div className="flex justify-end pt-2">
            <button onClick={() => setStep(1)} disabled={!selectedTemplate}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl disabled:opacity-50">
              Lanjut <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Step 1: Pick Target */}
      {step === 1 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Pilih Target (opsional)</h2>
          <div className="flex gap-3">
            <button onClick={() => setTargetType("empty")}
              className={`flex-1 p-3 rounded-xl border-2 text-sm font-semibold transition-colors ${targetType === "empty" ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20 text-amber-700" : "border-[var(--border-default)] text-gray-600 hover:border-amber-300"}`}>
              Tanpa Target
            </button>
            <button onClick={() => setTargetType("lead")}
              className={`flex-1 p-3 rounded-xl border-2 text-sm font-semibold transition-colors ${targetType === "lead" ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20 text-amber-700" : "border-[var(--border-default)] text-gray-600 hover:border-amber-300"}`}>
              Dari Lead
            </button>
          </div>
          {targetType === "lead" && (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {leads.slice(0, 50).map(l => (
                <button key={l.id} onClick={() => autoFillFromLead(l)}
                  className={`w-full text-left p-3 rounded-xl border transition-colors ${selectedLead?.id === l.id ? "border-amber-500 bg-amber-50 dark:bg-amber-950/20" : "border-[var(--border-default)] bg-white dark:bg-neutral-900 hover:border-amber-300"}`}>
                  <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">{l.business_name}</p>
                  <p className="text-xs text-gray-500">{l.product_interest || "—"} · {l.phone_number}</p>
                </button>
              ))}
            </div>
          )}
          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(0)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-xl">
              <ChevronLeft size={16} /> Kembali
            </button>
            <button onClick={() => setStep(2)}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl">
              Lanjut <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Fill Variables */}
      {step === 2 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Isi Variabel</h2>
          {Object.keys(variables).length === 0 && <p className="text-sm text-gray-400">Template ini tidak punya variabel.</p>}
          <div className="space-y-3">
            {Object.entries(variables).map(([key, val]) => (
              <div key={key}>
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">{key.replace(/_/g, " ")}</label>
                {key.includes("html") || key.includes("body") || key.includes("rows") || key.includes("scope") || key.includes("terms") ? (
                  <textarea value={val} onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                    rows={4} placeholder={`{{${key}}}`}
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 resize-y" />
                ) : (
                  <input type="text" value={val} onChange={e => setVariables(prev => ({ ...prev, [key]: e.target.value }))}
                    placeholder={`{{${key}}}`}
                    className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(1)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-xl">
              <ChevronLeft size={16} /> Kembali
            </button>
            <button onClick={() => setStep(3)}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl">
              Preview <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Preview + Generate */}
      {step === 3 && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Preview & Generate</h2>
          <div className="bg-gray-50 dark:bg-neutral-800 rounded-xl p-4 text-sm space-y-1">
            <p><span className="font-semibold">Template:</span> {selectedTemplate?.name}</p>
            {selectedLead && <p><span className="font-semibold">Target:</span> {selectedLead.business_name}</p>}
            <p><span className="font-semibold">Variabel diisi:</span> {Object.values(variables).filter(Boolean).length}/{Object.keys(variables).length}</p>
          </div>
          <div className="flex justify-between pt-2">
            <button onClick={() => setStep(2)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-xl">
              <ChevronLeft size={16} /> Kembali
            </button>
            <button onClick={handleGenerate} disabled={generating}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl disabled:opacity-50">
              {generating ? "Generating..." : "Generate PDF"}
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Done */}
      {step === 4 && generatedDoc && (
        <div className="space-y-4 text-center">
          <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto">
            <Check size={28} className="text-green-600" />
          </div>
          <h2 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">PDF Berhasil Dibuat!</h2>
          <p className="text-sm text-gray-500">{generatedDoc.template_name}</p>
          <div className="flex gap-3 justify-center pt-2">
            <a href={`${API_BASE}${generatedDoc.file_url}`} download
              className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl">
              <Download size={16} /> Download PDF
            </a>
            <button onClick={() => setEmailModal(true)}
              className="flex items-center gap-2 px-5 py-2.5 border-2 border-gray-200 hover:border-gray-400 text-gray-700 dark:text-neutral-200 text-sm font-semibold rounded-xl">
              <Mail size={16} /> Kirim Email
            </button>
          </div>
          <button onClick={() => { setStep(0); setSelectedTemplate(null); setSelectedLead(null); setVariables({}); setGeneratedDoc(null); }}
            className="text-xs text-gray-400 hover:text-gray-600 underline mt-2">
            Generate dokumen lain
          </button>
        </div>
      )}

      {/* Email Modal */}
      {emailModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-neutral-900 rounded-2xl p-6 w-full max-w-md shadow-xl">
            <h3 className="text-lg font-bold text-neutral-800 dark:text-neutral-100 mb-4">Kirim via Email</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Alamat Email</label>
                <input type="email" value={emailTo} onChange={e => setEmailTo(e.target.value)}
                  placeholder="klien@email.com"
                  className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" />
              </div>
              <div>
                <label className="text-xs font-bold text-gray-600 uppercase tracking-wide">Subject (opsional)</label>
                <input type="text" value={emailSubject} onChange={e => setEmailSubject(e.target.value)}
                  placeholder={`${generatedDoc?.template_name} dari Teman UMKM Kita`}
                  className="mt-1 w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800" />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setEmailModal(false)} className="flex-1 py-2.5 rounded-xl border border-gray-200 text-sm font-semibold text-gray-600">Batal</button>
              <button onClick={handleSendEmail} disabled={sendingEmail || !emailTo}
                className="flex-1 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold disabled:opacity-50">
                {sendingEmail ? "Mengirim..." : "Kirim"}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
