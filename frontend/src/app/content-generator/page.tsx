"use client";

import { useState, useCallback, useEffect } from "react";
import { useApi } from "../../lib/swr";
import { apiFetch } from "../../lib/api";
import Breadcrumb from "../../components/Breadcrumb";
import Toast from "../../components/Toast";

import ContentSidebar from "../../components/content-generator/ContentSidebar";
import SeoArticlePanel from "../../components/content-generator/SeoArticlePanel";
import ImagePanel from "../../components/content-generator/ImagePanel";
import CaptionPanel from "../../components/content-generator/CaptionPanel";
import ContentHistory from "../../components/content-generator/ContentHistory";
import ContentPreview from "../../components/content-generator/ContentPreview";

import type { Tool, ContentSession, ContentGeneration, ContentProvider } from "../../components/content-generator/types";

export default function ContentGeneratorPage() {
  const [activeTool, setActiveTool] = useState<Tool>("seo_article");
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" | "info" } | null>(null);
  const [viewResult, setViewResult] = useState<{
    title: string; meta_description: string; body: string;
    focus_keyword: string; secondary_keywords: string[]; id?: string;
  } | null>(null);
  const [showProviderModal, setShowProviderModal] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ContentProvider | null>(null);
  const [providerForm, setProviderForm] = useState({
    name: "", base_url: "", api_key: "", model: "", is_active: true,
  });

  // SWR data
  const { data: sessionsData = [] } = useApi<ContentSession[]>("/api/content/sessions");
  const { data: providersData = [] } = useApi<ContentProvider[]>("/api/content/providers?tool_type=image");
  const { data: generationsData = [] } = useApi<ContentGeneration[]>("/api/content/generations?limit=50");
  const { data: settingsData } = useApi<Record<string, string>>("/api/settings", { revalidateOnFocus: false });

  // Local state synced from SWR
  const [sessions, setSessions] = useState<ContentSession[]>([]);
  const [generations, setGenerations] = useState<ContentGeneration[]>([]);
  const [selectedSession, setSelectedSession] = useState<ContentSession | null>(null);
  const [sharedContext, setSharedContext] = useState<string[]>([]);
  const [cmsConfigOpen, setCmsConfigOpen] = useState(false);
  const [cmsUrl, setCmsUrl] = useState("");
  const [cmsApiToken, setCmsApiToken] = useState("");
  const [savingCms, setSavingCms] = useState(false);

  // Sync SWR → local state
  useEffect(() => { setSessions(sessionsData); }, [sessionsData]);
  useEffect(() => { setGenerations(generationsData); }, [generationsData]);
  useEffect(() => {
    if (settingsData) {
      setCmsUrl(settingsData.cms_url ?? "");
      setCmsApiToken(settingsData.cms_api_token ?? "");
    }
  }, [settingsData]);

  const showToast = useCallback((msg: string, type: "success" | "error" | "info" = "success") => {
    setToast({ msg, type });
  }, []);

  function toggleContext(id: string) {
    setSharedContext(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  }

  function clearAllContext() {
    setSharedContext([]);
  }

  function onResult(gen: ContentGeneration) {
    setGenerations(prev => prev.some(g => g.id === gen.id) ? prev : [gen, ...prev]);
  }

  // ─── Session CRUD ───────────────────────────────────────────────────────────

  async function createSession(data: { name: string; description?: string }) {
    const res = await apiFetch("/api/content/sessions", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (res.ok) {
      const s = await res.json();
      setSessions(prev => [s, ...prev]);
      setSelectedSession(s);
      showToast("Session dibuat");
    }
  }

  async function deleteSession(id: string) {
    const res = await apiFetch(`/api/content/sessions/${id}`, { method: "DELETE" });
    if (res.ok) {
      setSessions(prev => prev.filter(s => s.id !== id));
      if (selectedSession?.id === id) setSelectedSession(null);
      showToast("Session dihapus");
    }
  }

  async function renameSession(id: string, name: string) {
    const res = await apiFetch(`/api/content/sessions/${id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (res.ok) {
      setSessions(prev => prev.map(s => s.id === id ? { ...s, name } : s));
      if (selectedSession?.id === id) setSelectedSession(prev => prev ? { ...prev, name } : null);
      showToast("Session diupdate");
    }
  }

  async function deleteGeneration(id: string) {
    const res = await apiFetch(`/api/content/generations/${id}`, { method: "DELETE" });
    if (res.ok) {
      setGenerations(prev => prev.filter(g => g.id !== id));
      showToast("Artikel dihapus");
    }
  }

  async function saveCmsConfig() {
    setSavingCms(true);
    try {
      const res = await apiFetch("/api/settings", {
        method: "PUT",
        body: JSON.stringify({ cms_url: cmsUrl, cms_api_token: cmsApiToken }),
      });
      if (res.ok) showToast("Konfigurasi CMS disimpan");
      else showToast("Gagal menyimpan", "error");
    } catch { showToast("Gagal menyimpan", "error"); }
    finally { setSavingCms(false); }
  }

  // ─── Provider CRUD ─────────────────────────────────────────────────────────

  async function saveProvider() {
    if (!providerForm.name || !providerForm.base_url || !providerForm.model) return;
    const method = editingProvider ? "PUT" : "POST";
    const url = editingProvider ? `/api/content/providers/${editingProvider.id}` : "/api/content/providers";
    const res = await apiFetch(url, {
      method, headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...providerForm, tool_type: "image" }),
    });
    if (res.ok) {
      setShowProviderModal(false);
      setEditingProvider(null);
      setProviderForm({ name: "", base_url: "", api_key: "", model: "", is_active: true });
      showToast(editingProvider ? "Provider diupdate" : "Provider ditambahkan");
    }
  }

  async function deleteProvider(id: string) {
    const res = await apiFetch(`/api/content/providers/${id}`, { method: "DELETE" });
    if (res.ok) showToast("Provider dihapus");
  }

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col md:flex-row h-full gap-3 p-3 md:p-6 overflow-hidden">

      <ContentSidebar
        sessions={sessions}
        sessionsLoading={sessionsData === undefined}
        selectedSession={selectedSession}
        setSelectedSession={setSelectedSession}
        generations={generations}
        generationsLoading={generationsData === undefined}
        sharedContext={sharedContext}
        toggleContext={toggleContext}
        onClearContext={clearAllContext}
        onDeleteGeneration={deleteGeneration}
        onCreateSession={createSession}
        onDeleteSession={deleteSession}
        onRenameSession={renameSession}
        onManageProviders={() => {
          setEditingProvider(null);
          setProviderForm({ name: "", base_url: "", api_key: "", model: "", is_active: true });
          setShowProviderModal(true);
        }}
        activeTool={activeTool}
        onToolChange={setActiveTool}
      />

      <div className="flex-1 flex flex-col gap-4 min-w-0 overflow-y-auto">

        {/* Active tool indicator + session badge */}
        <Breadcrumb items={[{ label: "Generator Konten" }, { label: activeTool === "seo_article" ? "Buat Artikel SEO" : activeTool === "image" ? "Buat Gambar" : "Caption Sosmed" }]} showBack backHref="/" />
        <div className="flex items-center gap-3">
          <h2 className="text-base font-bold text-neutral-800 dark:text-neutral-100">
            {activeTool === "seo_article" ? "Buat Artikel SEO" : activeTool === "image" ? "Buat Gambar" : "Caption Sosmed"}
          </h2>
          {selectedSession && (
            <span className="px-2.5 py-1 bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 text-xs font-semibold rounded-full">
              {selectedSession.name}
            </span>
          )}
        </div>

        {/* CMS Config */}
        <div className="bg-white dark:bg-[var(--bg-canvas)] rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <button onClick={() => setCmsConfigOpen(o => !o)}
            className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
            <span className="text-xs font-bold text-neutral-600 dark:text-neutral-300 uppercase tracking-wide">Pengaturan Penerbit</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
              className={`text-neutral-400 transition-transform ${cmsConfigOpen ? "rotate-180" : ""}`}>
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          {cmsConfigOpen && (
            <div className="px-4 pb-4 space-y-3 border-t border-gray-100 dark:border-gray-700 pt-3">
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">CMS URL</label>
                <input type="text" value={cmsUrl} onChange={e => setCmsUrl(e.target.value)}
                  placeholder="https://temanumkmkita.com"
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-sm bg-gray-50 dark:bg-neutral-800 dark:text-gray-200 focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none transition" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">CMS API Token</label>
                <input type="password" value={cmsApiToken} onChange={e => setCmsApiToken(e.target.value)}
                  placeholder="Bearer token untuk CMS API"
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-sm bg-gray-50 dark:bg-neutral-800 dark:text-gray-200 focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none transition" />
              </div>
              <button onClick={saveCmsConfig} disabled={savingCms}
                className="px-4 py-2 text-xs font-semibold bg-neutral-500 hover:bg-neutral-600 text-white rounded-lg disabled:opacity-50 transition-colors">
                {savingCms ? "Menyimpan..." : "Simpan CMS Config"}
              </button>
            </div>
          )}
        </div>

        {/* Tool Panels */}
        {activeTool === "seo_article" && (
          <SeoArticlePanel sessionId={selectedSession?.id || null} sharedContext={sharedContext}
            showToast={showToast} onResult={onResult} />
        )}
        {activeTool === "image" && (
          <ImagePanel sessionId={selectedSession?.id || null} sharedContext={sharedContext}
            providers={providersData} showToast={showToast} onResult={onResult} />
        )}
        {activeTool === "caption" && (
          <CaptionPanel sessionId={selectedSession?.id || null} sharedContext={sharedContext}
            showToast={showToast} onResult={onResult} />
        )}

        {/* Viewed result */}
        {viewResult && (
          <ContentPreview result={viewResult} showToast={showToast} onClose={() => setViewResult(null)} />
        )}

        {/* History */}
        <ContentHistory
          generations={generations}
          generationsLoading={generationsData === undefined}
          sharedContext={sharedContext}
          toggleContext={toggleContext}
          onDeleteGeneration={deleteGeneration}
          onSetViewResult={setViewResult}
        />
      </div>

      {/* Provider Modal */}
      {showProviderModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setShowProviderModal(false)}>
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
          <div className="relative bg-white dark:bg-[var(--bg-canvas)] rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="sticky top-0 bg-white dark:bg-[var(--bg-canvas)] px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between rounded-t-2xl">
              <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-50">Image Provider</h2>
              <button onClick={() => setShowProviderModal(false)} className="p-1 text-neutral-400 hover:text-neutral-600 rounded-lg">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              {providersData.length > 0 && (
                <div className="space-y-2 mb-4">
                  {providersData.map(p => (
                    <div key={p.id} className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-xl">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 truncate">{p.name}</p>
                        <p className="text-xs text-neutral-400 truncate">{p.model} · {p.base_url}</p>
                      </div>
                      <button onClick={() => {
                        setEditingProvider(p);
                        setProviderForm({ name: p.name, base_url: p.base_url, api_key: p.api_key || "", model: p.model, is_active: p.is_active });
                      }}
                        className="text-xs text-neutral-500 hover:text-neutral-700 px-2 py-1 rounded hover:bg-neutral-100">Edit</button>
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
                    className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600 outline-none" />
                </div>
              ))}
              <div className="flex gap-2">
                <button onClick={saveProvider} disabled={!providerForm.name || !providerForm.base_url || !providerForm.model}
                  className="flex-1 px-4 py-2 text-sm rounded-lg font-medium bg-neutral-500 hover:bg-neutral-600 text-white disabled:opacity-50">
                  {editingProvider ? "Simpan Perubahan" : "Tambah Provider"}
                </button>
                {editingProvider && (
                  <button onClick={() => {
                    setEditingProvider(null);
                    setProviderForm({ name: "", base_url: "", api_key: "", model: "", is_active: true });
                  }}
                    className="px-4 py-2 text-sm rounded-lg bg-gray-100 dark:bg-gray-800 text-neutral-600">Batal</button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {toast && <Toast message={toast.msg} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
