"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../../../lib/api";
import { Plus, Pencil, Trash2 } from "lucide-react";
import Toast from "../../../../components/Toast";
import ConfirmModal from "../../../../components/ConfirmModal";
import Breadcrumb from "../../../../components/Breadcrumb";
import { TemplateModal } from "../../../../components/documents/TemplateModal";
import { STARTER_TEMPLATES, STARTER_VARIABLES } from "../../../../components/documents/templateData";

interface DocTemplate {
  id: string;
  name: string;
  type: string;
  html_template: string;
  variables: string[];
  is_active: boolean;
  created_at: string;
}

export default function DocumentTemplatesPage() {
  const [templates, setTemplates] = useState<DocTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<DocTemplate | null>(null);
  const [form, setForm] = useState({ name: "", type: "invoice", html_template: "", variables: "" });
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [confirmState, setConfirmState] = useState<{ open: boolean; title: string; message: string; onConfirm: () => void }>({ open: false, title: "", message: "", onConfirm: () => {} });
  const [starterTemplates, setStarterTemplates] = useState<Record<string, string>>(STARTER_TEMPLATES);
  const [starterVariables, setStarterVariables] = useState<Record<string, string>>(STARTER_VARIABLES);

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await apiFetch("/api/document-templates");
      if (res.ok) setTemplates(await res.json());
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchTemplates();
    apiFetch("/api/document-template-starters")
      .then(res => res.ok ? res.json() : {})
      .then((starters: Record<string, { html_template: string; variables: string[] }>) => {
        const html: Record<string, string> = { ...STARTER_TEMPLATES };
        const variables: Record<string, string> = { ...STARTER_VARIABLES };
        for (const [type, starter] of Object.entries(starters)) {
          html[type] = starter.html_template;
          variables[type] = starter.variables.join(", ");
        }
        setStarterTemplates(html);
        setStarterVariables(variables);
      })
      .catch(() => {});
  }, [fetchTemplates]);

  function openNew() {
    setEditing(null);
    setForm({ name: "", type: "invoice", html_template: starterTemplates["invoice"], variables: starterVariables["invoice"] });
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
      html_template: (!prev.html_template.trim() || Object.values(starterTemplates).includes(prev.html_template))
        ? (starterTemplates[newType] || "")
        : prev.html_template,
      variables: (!prev.variables.trim() || Object.values(starterVariables).includes(prev.variables))
        ? (starterVariables[newType] || "")
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
      open: true, title: "Hapus Template", message: "Yakin mau hapus template ini?",
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
      <Breadcrumb items={[
        { label: "Document Generator", href: "/documents/generator" },
        { label: "Templates" },
      ]} showBack backHref="/documents/generator" />
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

      {loading ? (
        <p className="text-sm text-gray-400">Memuat...</p>
      ) : (
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

      <TemplateModal
        open={modal} editing={editing} form={form} onChange={setForm}
        onTypeChange={handleTypeChange} onSave={handleSave} onClose={() => setModal(false)}
        onResetToStarter={() => setForm(prev => ({ ...prev, html_template: starterTemplates[prev.type], variables: starterVariables[prev.type] || prev.variables }))}
        starterTemplates={starterTemplates} saving={saving}
      />

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      <ConfirmModal open={confirmState.open} onClose={() => setConfirmState(s => ({ ...s, open: false }))}
        onConfirm={confirmState.onConfirm} title={confirmState.title} message={confirmState.message} />
    </div>
  );
}