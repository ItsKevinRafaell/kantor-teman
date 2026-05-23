"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../../lib/api";
import Toast from "../../components/Toast";

// ─── Interfaces ──────────────────────────────────────────────────────────────

interface ContentProvider {
  id: string; name: string; tool_type: string; base_url: string;
  api_key?: string; model: string; is_active: boolean; created_at: string;
}

interface ContentSession {
  id: string; name: string; description?: string; created_at: string;
}

interface ContentGeneration {
  id: string; session_id?: string; tool_type: string;
  input_data: Record<string, unknown>; output_data: unknown;
  model_used?: string; provider_name?: string; status: string;
  error_msg?: string; created_at: string;
}

type Tool = "caption" | "seo_article" | "image";
type ToastState = { msg: string; type: "success" | "error" | "info" } | null;

// ─── Helpers ──────────────────────────────────────────────────────────────────

const TOOL_LABELS: Record<Tool, string> = {
  caption: "Caption Generator",
  seo_article: "SEO Article",
  image: "Image Generator",
};

const TOOL_COLORS: Record<Tool, string> = {
  caption: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300",
  seo_article: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300",
  image: "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300",
};

function formatDate(d: string) {
  return new Date(d).toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

function applyInlineMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");
}

function markdownToHtml(md: string): string {
  const lines = md.split("\n");
  const parts: string[] = [];
  let inList = false;

  const endList = () => { if (inList) { parts.push("</ul>"); inList = false; } };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.startsWith("## ")) {
      endList();
      parts.push(`<h2 class="text-lg font-bold mt-5 mb-2 text-neutral-800 dark:text-neutral-200">${applyInlineMarkdown(line.slice(3))}</h2>`);
    } else if (line.startsWith("### ")) {
      endList();
      parts.push(`<h3 class="text-base font-semibold mt-4 mb-1 text-neutral-700 dark:text-neutral-300">${applyInlineMarkdown(line.slice(4))}</h3>`);
    } else if (line.startsWith("#### ")) {
      endList();
      parts.push(`<h4 class="text-sm font-semibold mt-3 mb-1 text-neutral-600 dark:text-neutral-400">${applyInlineMarkdown(line.slice(5))}</h4>`);
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      if (!inList) { parts.push(`<ul class="list-disc ml-5 my-2 space-y-0.5">`); inList = true; }
      parts.push(`<li class="text-sm text-neutral-700 dark:text-neutral-300">${applyInlineMarkdown(line.slice(2))}</li>`);
    } else if (line.trim() === "") {
      endList();
    } else {
      endList();
      parts.push(`<p class="text-sm text-neutral-700 dark:text-neutral-300 mb-2 leading-relaxed">${applyInlineMarkdown(line)}</p>`);
    }
  }
  endList();
  return parts.join("\n");
}

async function exportToDocx(result: {
  title: string; meta_description: string; body: string;
  focus_keyword: string; secondary_keywords: string[];
}) {
  const { Document, Paragraph, TextRun, HeadingLevel, Packer } = await import("docx");

  const children: InstanceType<typeof Paragraph>[] = [];

  children.push(new Paragraph({ text: result.title, heading: HeadingLevel.HEADING_1 }));
  children.push(new Paragraph({ text: "" }));
  children.push(new Paragraph({
    children: [
      new TextRun({ text: "Meta Description: ", bold: true }),
      new TextRun({ text: result.meta_description }),
    ],
  }));
  if (result.secondary_keywords?.length) {
    children.push(new Paragraph({
      children: [
        new TextRun({ text: "Secondary Keywords: ", bold: true }),
        new TextRun({ text: result.secondary_keywords.join(", ") }),
      ],
    }));
  }
  children.push(new Paragraph({ text: "" }));

  for (const raw of result.body.split("\n")) {
    const line = raw.trimEnd();
    const strip = (s: string) => s.replace(/\*\*(.+?)\*\*/g, "$1").replace(/\*(.+?)\*/g, "$1");
    if (line.startsWith("## ")) {
      children.push(new Paragraph({ text: strip(line.slice(3)), heading: HeadingLevel.HEADING_2 }));
    } else if (line.startsWith("### ")) {
      children.push(new Paragraph({ text: strip(line.slice(4)), heading: HeadingLevel.HEADING_3 }));
    } else if (line.startsWith("#### ")) {
      children.push(new Paragraph({ text: strip(line.slice(5)), heading: HeadingLevel.HEADING_4 }));
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      children.push(new Paragraph({ text: strip(line.slice(2)), bullet: { level: 0 } }));
    } else if (line.trim() === "") {
      children.push(new Paragraph({ text: "" }));
    } else {
      children.push(new Paragraph({ text: strip(line) }));
    }
  }

  const doc = new Document({ sections: [{ children }] });
  const blob = await Packer.toBlob(doc);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${result.title.replace(/[^a-z0-9\s]/gi, "").trim().replace(/\s+/g, "_") || "seo_article"}.docx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
      <div className="relative bg-white dark:bg-[#242423] rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 bg-white dark:bg-[#242423] px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between rounded-t-2xl">
          <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-50">{title}</h2>
          <button onClick={onClose} className="p-1 text-neutral-400 hover:text-neutral-600 rounded-lg">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ContentGeneratorPage() {
  const [activeTool, setActiveTool] = useState<Tool>("caption");
  const [sessions, setSessions] = useState<ContentSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<ContentSession | null>(null);
  const [imageProviders, setImageProviders] = useState<ContentProvider[]>([]);
  const [generations, setGenerations] = useState<ContentGeneration[]>([]);
  const [sharedContext, setSharedContext] = useState<string[]>([]);
  const [toast, setToast] = useState<ToastState>(null);

  // Modals
  const [showProviderModal, setShowProviderModal] = useState(false);
  const [showNewSessionModal, setShowNewSessionModal] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ContentProvider | null>(null);

  // Provider form
  const [providerForm, setProviderForm] = useState({ name: "", base_url: "", api_key: "", model: "", is_active: true });

  // Session form
  const [sessionForm, setSessionForm] = useState({ name: "", description: "" });

  // Session rename
  const [renamingSession, setRenamingSession] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const showToast = (msg: string, type: "success" | "error" | "info" = "success") => setToast({ msg, type });

  const loadSessions = useCallback(async () => {
    try { const res = await apiFetch("/api/content/sessions"); if (res.ok) setSessions(await res.json()); } catch {}
  }, []);

  const loadProviders = useCallback(async () => {
    try { const res = await apiFetch("/api/content/providers?tool_type=image"); if (res.ok) setImageProviders(await res.json()); } catch {}
  }, []);

  const loadGenerations = useCallback(async (sessionId?: string) => {
    try {
      const url = sessionId ? `/api/content/generations?session_id=${sessionId}&limit=30` : "/api/content/generations?limit=20";
      const res = await apiFetch(url);
      if (res.ok) setGenerations(await res.json());
    } catch {}
  }, []);

  useEffect(() => { loadSessions(); loadProviders(); loadGenerations(); }, [loadSessions, loadProviders, loadGenerations]);

  useEffect(() => { loadGenerations(selectedSession?.id); }, [selectedSession, loadGenerations]);

  // ── Provider CRUD ──────────────────────────────────────────────────────────

  async function saveProvider() {
    if (!providerForm.name || !providerForm.base_url || !providerForm.model) return;
    try {
      const method = editingProvider ? "PUT" : "POST";
      const url = editingProvider ? `/api/content/providers/${editingProvider.id}` : "/api/content/providers";
      const res = await apiFetch(url, {
        method, headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...providerForm, tool_type: "image" }),
      });
      if (res.ok) {
        await loadProviders();
        setShowProviderModal(false);
        setEditingProvider(null);
        setProviderForm({ name: "", base_url: "", api_key: "", model: "", is_active: true });
        showToast(editingProvider ? "Provider diupdate" : "Provider ditambahkan");
      }
    } catch { showToast("Gagal simpan provider", "error"); }
  }

  async function deleteProvider(id: string) {
    try {
      const res = await apiFetch(`/api/content/providers/${id}`, { method: "DELETE" });
      if (res.ok) { await loadProviders(); showToast("Provider dihapus"); }
    } catch { showToast("Gagal hapus provider", "error"); }
  }

  // ── Session CRUD ───────────────────────────────────────────────────────────

  async function createSession() {
    if (!sessionForm.name.trim()) return;
    try {
      const res = await apiFetch("/api/content/sessions", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(sessionForm),
      });
      if (res.ok) {
        const s = await res.json();
        setSessions(prev => [s, ...prev]);
        setSelectedSession(s);
        setShowNewSessionModal(false);
        setSessionForm({ name: "", description: "" });
        showToast("Session dibuat");
      }
    } catch { showToast("Gagal buat session", "error"); }
  }

  async function deleteSession(id: string) {
    try {
      const res = await apiFetch(`/api/content/sessions/${id}`, { method: "DELETE" });
      if (res.ok) {
        setSessions(prev => prev.filter(s => s.id !== id));
        if (selectedSession?.id === id) setSelectedSession(null);
        showToast("Session dihapus");
      }
    } catch { showToast("Gagal hapus session", "error"); }
  }

  async function commitRename(id: string) {
    if (!renameValue.trim()) { setRenamingSession(null); return; }
    try {
      const res = await apiFetch(`/api/content/sessions/${id}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: renameValue.trim() }),
      });
      if (res.ok) {
        setSessions(prev => prev.map(s => s.id === id ? { ...s, name: renameValue.trim() } : s));
        if (selectedSession?.id === id) setSelectedSession(prev => prev ? { ...prev, name: renameValue.trim() } : null);
        showToast("Session diupdate");
      }
    } catch { showToast("Gagal update session", "error"); }
    setRenamingSession(null);
  }

  // ── Context toggle ─────────────────────────────────────────────────────────

  function toggleContext(id: string) {
    setSharedContext(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  }

  // ── Generation callback ────────────────────────────────────────────────────

  function onResult(gen: ContentGeneration) {
    setGenerations(prev => prev.some(g => g.id === gen.id) ? prev : [gen, ...prev]);
  }

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col md:flex-row h-full gap-3 p-3 md:p-6 overflow-hidden">

      {/* ── Left Sidebar ── */}
      <aside className="w-full md:w-52 shrink-0 flex flex-col gap-3 overflow-x-auto md:overflow-y-auto">
        <div>
          <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-2">Tools</p>
          {(["caption", "seo_article", "image"] as Tool[]).map(t => (
            <button key={t} onClick={() => setActiveTool(t)}
              className={`w-full text-left px-3 py-2 rounded-xl text-sm font-medium mb-1 transition-all
                ${activeTool === t ? "bg-yellow-500 text-white shadow-sm" : "text-neutral-500 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-neutral-800 dark:hover:text-neutral-200"}`}>
              {t === "caption" && "💬 "}{t === "seo_article" && "📝 "}{t === "image" && "🎨 "}
              {TOOL_LABELS[t]}
            </button>
          ))}
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest">Sesi</p>
            <button onClick={() => setShowNewSessionModal(true)} className="text-xs text-yellow-600 hover:text-yellow-700 font-medium">+ Baru</button>
          </div>
          <button onClick={() => setSelectedSession(null)}
            className={`w-full text-left px-3 py-2 rounded-xl text-sm mb-1 transition-all
              ${!selectedSession ? "bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300 font-medium" : "text-neutral-500 hover:bg-gray-100 dark:hover:bg-gray-800"}`}>
            Tanpa sesi
          </button>
          {sessions.map(s => (
            <div key={s.id} className={`group flex items-center gap-1 px-3 py-2 rounded-xl text-sm mb-1 transition-all
              ${selectedSession?.id === s.id ? "bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-300 font-medium" : "text-neutral-500 hover:bg-gray-100 dark:hover:bg-gray-800"}`}>
              {renamingSession === s.id ? (
                <input
                  value={renameValue}
                  onChange={e => setRenameValue(e.target.value)}
                  onBlur={() => commitRename(s.id)}
                  onKeyDown={e => { if (e.key === "Enter") commitRename(s.id); if (e.key === "Escape") setRenamingSession(null); }}
                  autoFocus
                  className="flex-1 bg-transparent outline-none border-b border-yellow-400 text-sm min-w-0"
                  onClick={e => e.stopPropagation()}
                />
              ) : (
                <span className="flex-1 truncate cursor-pointer" onClick={() => setSelectedSession(s)}>{s.name}</span>
              )}
              {renamingSession !== s.id && (
                <>
                  <button onClick={e => { e.stopPropagation(); setRenameValue(s.name); setRenamingSession(s.id); }}
                    className="opacity-0 group-hover:opacity-100 text-neutral-400 hover:text-yellow-600 text-xs shrink-0" title="Rename">✎</button>
                  <button onClick={e => { e.stopPropagation(); deleteSession(s.id); }}
                    className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 text-xs shrink-0" title="Hapus">✕</button>
                </>
              )}
            </div>
          ))}
        </div>

        {sharedContext.length > 0 && (
          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-3">
            <p className="text-xs font-semibold text-amber-700 dark:text-amber-400 mb-1">{sharedContext.length} konteks aktif</p>
            <button onClick={() => setSharedContext([])} className="text-xs text-amber-500 hover:text-amber-700">Hapus semua</button>
          </div>
        )}

        {activeTool === "image" && (
          <button onClick={() => { setEditingProvider(null); setProviderForm({ name: "", base_url: "", api_key: "", model: "", is_active: true }); setShowProviderModal(true); }}
            className="text-xs text-neutral-500 hover:text-yellow-600 px-3 py-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-left">
            ⚙️ Kelola Image Provider
          </button>
        )}
      </aside>

      {/* ── Main Area ── */}
      <div className="flex-1 flex flex-col gap-4 min-w-0 overflow-y-auto">

        {/* Session badge */}
        {selectedSession && (
          <div className="flex items-center gap-2 px-3 py-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl w-fit">
            <span className="text-xs font-semibold text-yellow-700 dark:text-yellow-300">📁 {selectedSession.name}</span>
            {selectedSession.description && <span className="text-xs text-neutral-400">{selectedSession.description}</span>}
          </div>
        )}

        {/* Tool Panels */}
        {activeTool === "caption" && (
          <CaptionPanel sessionId={selectedSession?.id || null} sharedContext={sharedContext}
            showToast={showToast} onResult={onResult} />
        )}
        {activeTool === "seo_article" && (
          <SeoArticlePanel sessionId={selectedSession?.id || null} sharedContext={sharedContext}
            showToast={showToast} onResult={onResult} />
        )}
        {activeTool === "image" && (
          <ImagePanel sessionId={selectedSession?.id || null} sharedContext={sharedContext}
            providers={imageProviders} showToast={showToast} onResult={onResult} />
        )}

        {/* History */}
        <HistoryPanel generations={generations} sharedContext={sharedContext} onToggleContext={toggleContext} />
      </div>

      {/* ── Modals ── */}
      <Modal open={showProviderModal} onClose={() => setShowProviderModal(false)} title="Image Provider">
        <div className="space-y-4">
          {imageProviders.length > 0 && (
            <div className="space-y-2 mb-4">
              {imageProviders.map(p => (
                <div key={p.id} className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 truncate">{p.name}</p>
                    <p className="text-xs text-neutral-400 truncate">{p.model} · {p.base_url}</p>
                  </div>
                  <button onClick={() => { setEditingProvider(p); setProviderForm({ name: p.name, base_url: p.base_url, api_key: p.api_key || "", model: p.model, is_active: p.is_active }); }}
                    className="text-xs text-yellow-600 hover:text-yellow-700 px-2 py-1 rounded hover:bg-yellow-50">Edit</button>
                  <button onClick={() => deleteProvider(p.id)} className="text-xs text-red-500 hover:text-red-600 px-2 py-1 rounded hover:bg-red-50">Hapus</button>
                </div>
              ))}
              <hr className="border-gray-200 dark:border-gray-700" />
            </div>
          )}
          <p className="text-sm font-semibold text-neutral-700 dark:text-neutral-300">{editingProvider ? "Edit Provider" : "Tambah Provider Baru"}</p>
          {([
            { label: "Nama", key: "name" as const, placeholder: "DALL-E 3", type: "text" },
            { label: "Base URL", key: "base_url" as const, placeholder: "https://api.openai.com/v1", type: "text" },
            { label: "API Key", key: "api_key" as const, placeholder: "sk-...", type: "password" },
            { label: "Model", key: "model" as const, placeholder: "dall-e-3", type: "text" },
          ] as { label: string; key: "name"|"base_url"|"api_key"|"model"; placeholder: string; type: string }[]).map(({ label, key, placeholder, type }) => (
            <div key={key}>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">{label}</label>
              <input type={type} value={providerForm[key]}
                onChange={e => setProviderForm(prev => ({ ...prev, [key]: e.target.value }))}
                placeholder={placeholder}
                className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
            </div>
          ))}
          <div className="flex gap-2">
            <button onClick={saveProvider} disabled={!providerForm.name || !providerForm.base_url || !providerForm.model}
              className="flex-1 px-4 py-2 text-sm rounded-lg font-medium bg-yellow-500 hover:bg-yellow-600 text-white disabled:opacity-50">
              {editingProvider ? "Simpan Perubahan" : "Tambah Provider"}
            </button>
            {editingProvider && (
              <button onClick={() => { setEditingProvider(null); setProviderForm({ name: "", base_url: "", api_key: "", model: "", is_active: true }); }}
                className="px-4 py-2 text-sm rounded-lg bg-gray-100 dark:bg-gray-800 text-neutral-600">Batal</button>
            )}
          </div>
        </div>
      </Modal>

      <Modal open={showNewSessionModal} onClose={() => setShowNewSessionModal(false)} title="Sesi Baru">
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Nama Sesi</label>
            <input type="text" value={sessionForm.name} onChange={e => setSessionForm(p => ({ ...p, name: e.target.value }))}
              placeholder="Kampanye Lebaran 2025"
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Deskripsi (opsional)</label>
            <input type="text" value={sessionForm.description} onChange={e => setSessionForm(p => ({ ...p, description: e.target.value }))}
              placeholder="Konten untuk campaign Ramadan..."
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
          </div>
          <button onClick={createSession} disabled={!sessionForm.name.trim()}
            className="w-full px-4 py-2 text-sm rounded-lg font-medium bg-yellow-500 hover:bg-yellow-600 text-white disabled:opacity-50">
            Buat Sesi
          </button>
        </div>
      </Modal>

      {toast && <Toast message={toast.msg} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Caption Panel
// ═══════════════════════════════════════════════════════════════════════════════

function CaptionPanel({ sessionId, sharedContext, showToast, onResult }: {
  sessionId: string | null; sharedContext: string[];
  showToast: (m: string, t?: "success"|"error"|"info") => void;
  onResult: (g: ContentGeneration) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [topic, setTopic] = useState("");
  const [platform, setPlatform] = useState<"instagram"|"tiktok">("instagram");
  const [tone, setTone] = useState("casual");
  const [keywords, setKeywords] = useState("");
  const [result, setResult] = useState<{ caption: string; hashtags: string[]; notes: string; id?: string } | null>(null);

  async function generate() {
    if (!topic.trim()) return;
    setLoading(true); setResult(null);
    try {
      const res = await apiFetch("/api/content/generate/caption", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic, platform, tone,
          keywords: keywords.split(",").map(k => k.trim()).filter(Boolean),
          session_id: sessionId,
          context_from: sharedContext,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setResult(data);
        onResult({ id: data.id, session_id: sessionId || undefined, tool_type: "caption",
          input_data: { topic, platform }, output_data: data, status: "done", created_at: data.created_at });
        showToast("Caption berhasil dibuat!");
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Gagal generate caption", "error");
      }
    } catch { showToast("Gagal generate caption", "error"); }
    finally { setLoading(false); }
  }

  return (
    <div className="bg-white dark:bg-[#242423] rounded-2xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
      <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-200">💬 Caption Generator</h2>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Topik / Produk</label>
        <textarea value={topic} onChange={e => setTopic(e.target.value)} rows={3}
          placeholder="Deskripsikan topik, produk, atau pesan yang ingin disampaikan..."
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm resize-none focus:ring-2 focus:ring-yellow-400 outline-none" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Platform</label>
          <div className="flex gap-2">
            {(["instagram", "tiktok"] as const).map(p => (
              <button key={p} onClick={() => setPlatform(p)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all capitalize
                  ${platform === p ? "bg-yellow-500 text-white" : "bg-gray-100 dark:bg-gray-800 text-neutral-500 hover:bg-gray-200 dark:hover:bg-gray-700"}`}>
                {p === "instagram" ? "📸 IG" : "🎵 TikTok"}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Tone</label>
          <select value={tone} onChange={e => setTone(e.target.value)}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none">
            {["casual", "profesional", "fun", "inspiratif", "edukatif"].map(t => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Keyword (pisah koma, opsional)</label>
        <input type="text" value={keywords} onChange={e => setKeywords(e.target.value)}
          placeholder="promo, diskon, gratis ongkir"
          className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
      </div>
      {sharedContext.length > 0 && (
        <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 rounded-lg">
          ✓ {sharedContext.length} konteks dari history akan digunakan
        </p>
      )}
      <button onClick={generate} disabled={loading || !topic.trim()}
        className="w-full py-2.5 bg-yellow-500 hover:bg-yellow-600 text-white text-sm font-semibold rounded-xl disabled:opacity-50 transition-all flex items-center justify-center gap-2">
        {loading ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Membuat...</> : "✨ Generate Caption"}
      </button>

      {result && (
        <div className="space-y-3 pt-2 border-t border-gray-100 dark:border-gray-700">
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
            <p className="text-sm text-neutral-800 dark:text-neutral-200 whitespace-pre-wrap leading-relaxed">{result.caption}</p>
          </div>
          {result.hashtags?.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.hashtags.map((h, i) => (
                <span key={i} className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs rounded-full font-medium">{h}</span>
              ))}
            </div>
          )}
          {result.notes && <p className="text-xs text-neutral-400 italic">💡 {result.notes}</p>}
          <div className="flex gap-2">
            <button onClick={() => copyToClipboard(`${result.caption}\n\n${result.hashtags?.join(" ")}`)}
              className="flex-1 py-2 text-xs rounded-lg bg-gray-100 dark:bg-gray-800 text-neutral-600 hover:bg-gray-200 dark:hover:bg-gray-700">📋 Copy</button>
            <button onClick={() => showToast("Sudah otomatis masuk history")}
              className="flex-1 py-2 text-xs rounded-lg bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 hover:bg-amber-100">🔗 Ada di History</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SEO Article Panel
// ═══════════════════════════════════════════════════════════════════════════════

function SeoArticlePanel({ sessionId, sharedContext, showToast, onResult }: {
  sessionId: string | null; sharedContext: string[];
  showToast: (m: string, t?: "success"|"error"|"info") => void;
  onResult: (g: ContentGeneration) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [title, setTitle] = useState("");
  const [wordCount, setWordCount] = useState(800);
  const [tone, setTone] = useState("informatif");
  const [searchIntent, setSearchIntent] = useState("informational");
  const [showAdvanced, setShowAdvanced] = useState(false);
  // Semrush data
  const [keywordDifficulty, setKeywordDifficulty] = useState("");
  const [searchVolume, setSearchVolume] = useState("");
  const [lsiKeywords, setLsiKeywords] = useState("");
  // Content structure
  const [faqTopics, setFaqTopics] = useState("");
  const [serpFeatures, setSerpFeatures] = useState<string[]>([]);
  // Context
  const [targetAudience, setTargetAudience] = useState("");
  const [targetLocation, setTargetLocation] = useState("");
  const [brandName, setBrandName] = useState("");
  const [uniqueAngle, setUniqueAngle] = useState("");
  const [internalLinkTargets, setInternalLinkTargets] = useState("");

  const [result, setResult] = useState<{
    title: string; meta_description: string; body: string;
    focus_keyword: string; secondary_keywords: string[]; id?: string;
  } | null>(null);

  function toggleSerp(val: string) {
    setSerpFeatures(prev => prev.includes(val) ? prev.filter(v => v !== val) : [...prev, val]);
  }

  async function generate() {
    if (!keyword.trim()) return;
    setLoading(true); setResult(null);
    try {
      const res = await apiFetch("/api/content/generate/seo-article", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          keyword, title: title || undefined, word_count: wordCount, tone,
          search_intent: searchIntent,
          keyword_difficulty: keywordDifficulty ? parseInt(keywordDifficulty) : undefined,
          search_volume: searchVolume ? parseInt(searchVolume) : undefined,
          lsi_keywords: lsiKeywords ? lsiKeywords.split(",").map(k => k.trim()).filter(Boolean) : [],
          faq_topics: faqTopics ? faqTopics.split("\n").map(q => q.trim()).filter(Boolean) : [],
          serp_features: serpFeatures,
          target_audience: targetAudience || undefined,
          target_location: targetLocation || undefined,
          brand_name: brandName || undefined,
          unique_angle: uniqueAngle || undefined,
          internal_link_targets: internalLinkTargets || undefined,
          session_id: sessionId, context_from: sharedContext,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setResult(data);
        onResult({ id: data.id, session_id: sessionId || undefined, tool_type: "seo_article",
          input_data: { keyword, word_count: wordCount }, output_data: data, status: "done", created_at: data.created_at });
        showToast("Artikel berhasil dibuat!");
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Gagal generate artikel", "error");
      }
    } catch { showToast("Gagal generate artikel", "error"); }
    finally { setLoading(false); }
  }

  async function handleExportDocx() {
    if (!result) return;
    setExporting(true);
    try {
      await exportToDocx(result);
      showToast("DOCX berhasil diexport!");
    } catch { showToast("Gagal export DOCX", "error"); }
    finally { setExporting(false); }
  }

  const SERP_OPTIONS = [
    { value: "featured_snippet", label: "Featured Snippet" },
    { value: "paa", label: "People Also Ask" },
    { value: "local_pack", label: "Local Pack" },
    { value: "image_pack", label: "Image Pack" },
  ];

  return (
    <div className="bg-white dark:bg-[#242423] rounded-2xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
      <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-200">📝 SEO Article Writer</h2>

      {/* Core fields */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Keyword Utama *</label>
          <input type="text" value={keyword} onChange={e => setKeyword(e.target.value)}
            placeholder="jasa pembuatan website murah"
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Judul (opsional)</label>
          <input type="text" value={title} onChange={e => setTitle(e.target.value)}
            placeholder="Otomatis dari keyword"
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Search Intent</label>
          <select value={searchIntent} onChange={e => setSearchIntent(e.target.value)}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none">
            <option value="informational">Informational — edukasi</option>
            <option value="commercial">Commercial — pertimbangan</option>
            <option value="transactional">Transactional — konversi</option>
            <option value="navigational">Navigational — brand</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Tone</label>
          <select value={tone} onChange={e => setTone(e.target.value)}
            className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none">
            {["informatif", "persuasif", "edukatif", "casual"].map(t => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Jumlah Kata: {wordCount}</label>
        <input type="range" min={400} max={2000} step={200} value={wordCount} onChange={e => setWordCount(Number(e.target.value))}
          className="w-full accent-yellow-500" />
        <div className="flex justify-between text-xs text-neutral-400 mt-1"><span>400</span><span>2000</span></div>
      </div>

      {/* Advanced toggle */}
      <button onClick={() => setShowAdvanced(p => !p)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-neutral-600 dark:text-neutral-300 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 hover:text-yellow-700 dark:hover:text-yellow-400 transition-colors border border-gray-200 dark:border-gray-700 w-full">
        <span className="text-xs">{showAdvanced ? "▾" : "▸"}</span>
        <span>{showAdvanced ? "Sembunyikan data lanjutan" : "Data Semrush & konteks lanjutan (opsional)"}</span>
        {!showAdvanced && <span className="ml-auto text-xs text-neutral-400">KD · Volume · LSI · FAQ · dll</span>}
      </button>

      {showAdvanced && (
        <div className="space-y-4 border border-gray-100 dark:border-gray-700 rounded-xl p-4 bg-gray-50/50 dark:bg-gray-800/30">
          <p className="text-xs font-semibold text-neutral-400 uppercase tracking-widest">Data Semrush</p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Search Volume <span className="font-normal normal-case text-neutral-300">/bulan</span></label>
              <input type="number" value={searchVolume} onChange={e => setSearchVolume(e.target.value)}
                placeholder="1200"
                className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Keyword Difficulty <span className="font-normal normal-case text-neutral-300">0-100</span></label>
              <input type="number" min={0} max={100} value={keywordDifficulty} onChange={e => setKeywordDifficulty(e.target.value)}
                placeholder="45"
                className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">LSI / Related Keywords <span className="font-normal normal-case text-neutral-300">pisah koma</span></label>
            <input type="text" value={lsiKeywords} onChange={e => setLsiKeywords(e.target.value)}
              placeholder="jasa web murah, buat website toko online, harga website profesional"
              className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Target SERP Features</label>
            <div className="flex flex-wrap gap-2">
              {SERP_OPTIONS.map(opt => (
                <button key={opt.value} onClick={() => toggleSerp(opt.value)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-all border
                    ${serpFeatures.includes(opt.value)
                      ? "bg-yellow-500 text-white border-yellow-500"
                      : "bg-white dark:bg-gray-800 text-neutral-500 border-gray-200 dark:border-gray-700 hover:border-yellow-300"}`}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">FAQ Topics <span className="font-normal normal-case text-neutral-300">1 pertanyaan per baris</span></label>
            <textarea value={faqTopics} onChange={e => setFaqTopics(e.target.value)} rows={3}
              placeholder={"Berapa biaya membuat website?\nBerapa lama proses pembuatan?\nApakah bisa request desain custom?"}
              className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm resize-none focus:ring-2 focus:ring-yellow-400 outline-none" />
          </div>

          <hr className="border-gray-200 dark:border-gray-700" />
          <p className="text-xs font-semibold text-neutral-400 uppercase tracking-widest">Konteks Bisnis</p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Target Pembaca</label>
              <input type="text" value={targetAudience} onChange={e => setTargetAudience(e.target.value)}
                placeholder="UMKM, pemilik toko online"
                className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Target Lokasi</label>
              <input type="text" value={targetLocation} onChange={e => setTargetLocation(e.target.value)}
                placeholder="Jakarta, Indonesia"
                className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Nama Brand</label>
              <input type="text" value={brandName} onChange={e => setBrandName(e.target.value)}
                placeholder="Teman UMKM Kita"
                className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Internal Link Targets</label>
              <input type="text" value={internalLinkTargets} onChange={e => setInternalLinkTargets(e.target.value)}
                placeholder="/blog/tips-umkm, /layanan/website"
                className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Angle Unik Artikel</label>
            <input type="text" value={uniqueAngle} onChange={e => setUniqueAngle(e.target.value)}
              placeholder="Fokus pada UMKM kuliner, dengan contoh nyata, bukan teori"
              className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
          </div>
        </div>
      )}

      {sharedContext.length > 0 && (
        <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 rounded-lg">
          ✓ {sharedContext.length} konteks dari history akan digunakan
        </p>
      )}

      <button onClick={generate} disabled={loading || !keyword.trim()}
        className="w-full py-2.5 bg-yellow-500 hover:bg-yellow-600 text-white text-sm font-semibold rounded-xl disabled:opacity-50 transition-all flex items-center justify-center gap-2">
        {loading ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Sedang menulis artikel...</> : "✨ Generate Artikel"}
      </button>

      {result && (
        <div className="space-y-3 pt-2 border-t border-gray-100 dark:border-gray-700">
          <div className="bg-green-50 dark:bg-green-900/20 rounded-xl p-3">
            <p className="text-xs font-semibold text-green-700 dark:text-green-400 mb-1">Meta Description</p>
            <p className="text-sm text-neutral-700 dark:text-neutral-300">{result.meta_description}</p>
          </div>
          {result.secondary_keywords?.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              <span className="text-xs text-neutral-400 self-center">Secondary keywords:</span>
              {result.secondary_keywords.map((k, i) => (
                <span key={i} className="px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs rounded-full">{k}</span>
              ))}
            </div>
          )}
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4 max-h-96 overflow-y-auto">
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 mb-3 text-base">{result.title}</h3>
            <div className="prose-content" dangerouslySetInnerHTML={{ __html: markdownToHtml(result.body) }} />
          </div>
          <div className="flex gap-2 flex-wrap">
            <button onClick={() => copyToClipboard(`# ${result.title}\n\n${result.body}`)}
              className="flex-1 py-2 text-xs rounded-lg bg-gray-100 dark:bg-gray-800 text-neutral-600 hover:bg-gray-200 dark:hover:bg-gray-700">📋 Copy Markdown</button>
            <button onClick={() => copyToClipboard(result.meta_description)}
              className="flex-1 py-2 text-xs rounded-lg bg-green-50 dark:bg-green-900/20 text-green-700 hover:bg-green-100">📋 Copy Meta</button>
            <button onClick={handleExportDocx} disabled={exporting}
              className="flex-1 py-2 text-xs rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 hover:bg-blue-100 disabled:opacity-50 flex items-center justify-center gap-1">
              {exporting ? <><div className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />Exporting...</> : "⬇ Export DOCX"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Image Panel
// ═══════════════════════════════════════════════════════════════════════════════

function ImagePanel({ sessionId, sharedContext, providers, showToast, onResult }: {
  sessionId: string | null; sharedContext: string[]; providers: ContentProvider[];
  showToast: (m: string, t?: "success"|"error"|"info") => void;
  onResult: (g: ContentGeneration) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [providerId, setProviderId] = useState("");
  const [size, setSize] = useState("512x512");
  const [images, setImages] = useState<{ type: string; value: string; id?: string }[]>([]);

  useEffect(() => { if (providers.length > 0 && !providerId) setProviderId(providers[0].id); }, [providers, providerId]);

  const [w, h] = size.split("x").map(Number);

  async function generate() {
    if (!prompt.trim() || !providerId) return;
    setLoading(true); setImages([]);
    try {
      const res = await apiFetch("/api/content/generate/image", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, provider_id: providerId, session_id: sessionId,
          negative_prompt: negativePrompt || undefined, width: w, height: h }),
      });
      if (res.ok) {
        const data = await res.json();
        setImages((data.images || []).map((img: { type: string; value: string }) => ({ ...img, id: data.id })));
        onResult({ id: data.id, session_id: sessionId || undefined, tool_type: "image",
          input_data: { prompt }, output_data: data, status: "done", created_at: data.created_at });
        showToast("Gambar berhasil dibuat!");
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Gagal generate image", "error");
      }
    } catch { showToast("Gagal generate image", "error"); }
    finally { setLoading(false); }
  }

  return (
    <div className="bg-white dark:bg-[#242423] rounded-2xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
      <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-200">🎨 Image Generator</h2>
      {providers.length === 0 ? (
        <div className="bg-amber-50 dark:bg-amber-900/20 rounded-xl p-4 text-center">
          <p className="text-sm text-amber-700 dark:text-amber-400">Belum ada image provider.</p>
          <p className="text-xs text-neutral-400 mt-1">Klik "Kelola Image Provider" di sidebar untuk menambahkan.</p>
        </div>
      ) : (
        <>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Provider</label>
            <select value={providerId} onChange={e => setProviderId(e.target.value)}
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none">
              {providers.map(p => <option key={p.id} value={p.id}>{p.name} ({p.model})</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Prompt *</label>
            <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={3}
              placeholder="Describe the image you want to generate..."
              className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm resize-none focus:ring-2 focus:ring-yellow-400 outline-none" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Negative Prompt</label>
              <input type="text" value={negativePrompt} onChange={e => setNegativePrompt(e.target.value)}
                placeholder="blurry, low quality..."
                className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">Ukuran</label>
              <select value={size} onChange={e => setSize(e.target.value)}
                className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-yellow-400 outline-none">
                {["512x512", "768x768", "1024x1024", "1024x576", "576x1024"].map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
          <button onClick={generate} disabled={loading || !prompt.trim() || !providerId}
            className="w-full py-2.5 bg-yellow-500 hover:bg-yellow-600 text-white text-sm font-semibold rounded-xl disabled:opacity-50 transition-all flex items-center justify-center gap-2">
            {loading ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Generating...</> : "✨ Generate Image"}
          </button>
          {images.length > 0 && (
            <div className="space-y-3 pt-2 border-t border-gray-100 dark:border-gray-700">
              <div className="grid grid-cols-2 gap-3">
                {images.map((img, i) => (
                  <div key={i} className="relative group rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700">
                    <img src={img.type === "b64" ? `data:image/png;base64,${img.value}` : img.value}
                      alt={`Generated ${i + 1}`} className="w-full h-48 object-cover" />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <a href={img.type === "b64" ? `data:image/png;base64,${img.value}` : img.value}
                        download={`generated-${i + 1}.png`}
                        className="px-3 py-1.5 bg-white text-neutral-800 text-xs rounded-lg font-medium">⬇ Download</a>
                      {img.type === "url" && (
                        <button onClick={() => copyToClipboard(img.value)}
                          className="px-3 py-1.5 bg-white text-neutral-800 text-xs rounded-lg font-medium">📋 URL</button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// History Panel
// ═══════════════════════════════════════════════════════════════════════════════

function HistoryPanel({ generations, sharedContext, onToggleContext }: {
  generations: ContentGeneration[];
  sharedContext: string[];
  onToggleContext: (id: string) => void;
}) {
  if (generations.length === 0) return null;

  function getPreview(g: ContentGeneration): string {
    const out = g.output_data as Record<string, unknown> | null;
    if (!out) return g.error_msg || "—";
    if (g.tool_type === "caption") return String(out.caption || "").slice(0, 100);
    if (g.tool_type === "seo_article") return `${out.title || ""} — ${String(out.meta_description || "").slice(0, 80)}`;
    if (g.tool_type === "image") {
      const imgs = (out.images as unknown[]) || [];
      return `${imgs.length} gambar`;
    }
    return "—";
  }

  return (
    <div className="bg-white dark:bg-[#242423] rounded-2xl border border-gray-200 dark:border-gray-700 p-5">
      <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-3">📂 History</h3>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {generations.map(g => {
          const isCtx = sharedContext.includes(g.id);
          return (
            <div key={g.id} className={`flex items-start gap-3 p-3 rounded-xl transition-colors
              ${isCtx ? "bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800" : "bg-gray-50 dark:bg-gray-800/50"}`}>
              <span className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full ${TOOL_COLORS[g.tool_type as Tool] || "bg-gray-100 text-gray-600"}`}>
                {g.tool_type === "caption" ? "💬" : g.tool_type === "seo_article" ? "📝" : "🎨"} {g.tool_type}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-neutral-600 dark:text-neutral-400 truncate">{getPreview(g)}</p>
                <p className="text-[10px] text-neutral-400 mt-0.5">{formatDate(g.created_at)}</p>
              </div>
              <button onClick={() => onToggleContext(g.id)}
                className={`shrink-0 text-xs px-2 py-1 rounded-lg font-medium transition-all
                  ${isCtx ? "bg-amber-200 dark:bg-amber-800 text-amber-800 dark:text-amber-200" : "bg-gray-200 dark:bg-gray-700 text-neutral-500 hover:bg-amber-100 hover:text-amber-700"}`}>
                {isCtx ? "✓ Konteks" : "+ Konteks"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
