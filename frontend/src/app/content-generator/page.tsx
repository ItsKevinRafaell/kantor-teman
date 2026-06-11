"use client";

import { useState, useCallback, useEffect } from "react";
import { useApi } from "../../lib/swr";
import { apiFetch } from "../../lib/api";
import Breadcrumb from "../../components/Breadcrumb";
import Toast from "../../components/Toast";

import ContentSidebar from "../../components/content-generator/ContentSidebar";
import SeoArticlePanel from "../../components/content-generator/SeoArticlePanel";
import ContentHistory from "../../components/content-generator/ContentHistory";
import ContentPreview from "../../components/content-generator/ContentPreview";

import type { Tool, ContentSession, ContentGeneration } from "../../components/content-generator/types";

export default function ContentGeneratorPage() {
  const [activeTool, setActiveTool] = useState<Tool>("seo_article");
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" | "info" } | null>(null);
  const [viewResult, setViewResult] = useState<{
    title: string; meta_description: string; body: string;
    focus_keyword: string; secondary_keywords: string[]; id?: string;
  } | null>(null);

  // SWR data
  const { data: sessionsData = [] } = useApi<ContentSession[]>("/api/content/sessions");
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

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="relative z-0 flex min-h-full flex-col gap-4 rounded-2xl bg-amber-50/20 p-3 md:flex-row md:p-5 dark:bg-amber-950/5">

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
        activeTool={activeTool}
        onToolChange={setActiveTool}
      />

      <div className="flex min-w-0 flex-1 flex-col gap-4">

        {/* Active tool indicator + session badge */}
        <Breadcrumb items={[{ label: "Generator Konten" }, { label: "Buat Artikel SEO" }]} showBack backHref="/" />
        <div className="flex items-center gap-3">
          <h2 className="text-base font-bold text-neutral-800 dark:text-neutral-100">
            Buat Artikel SEO
          </h2>
          {selectedSession && (
            <span className="px-2.5 py-1 bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 text-xs font-semibold rounded-full">
              {selectedSession.name}
            </span>
          )}
        </div>

        {/* CMS Config */}
        <div className="overflow-hidden rounded-2xl border border-amber-100 bg-white shadow-sm dark:border-amber-900/40 dark:bg-[var(--bg-surface)]">
          <button onClick={() => setCmsConfigOpen(o => !o)}
            className="w-full flex items-center justify-between px-4 py-3 text-left transition-colors hover:bg-amber-50/70 dark:hover:bg-amber-950/20">
            <span className="text-xs font-bold text-amber-700 dark:text-amber-300 uppercase tracking-wide">Pengaturan Penerbit</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
              className={`text-neutral-400 transition-transform ${cmsConfigOpen ? "rotate-180" : ""}`}>
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          {cmsConfigOpen && (
            <div className="space-y-3 border-t border-amber-100 px-4 pb-4 pt-3 dark:border-amber-900/40">
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">CMS URL</label>
                <input type="text" value={cmsUrl} onChange={e => setCmsUrl(e.target.value)}
                  placeholder="https://temanumkmkita.com"
                  className="w-full rounded-lg border border-gray-200 bg-amber-50/40 px-3 py-2 text-sm outline-none transition focus:ring-2 focus:ring-amber-300 dark:border-gray-700 dark:bg-neutral-800/70 dark:text-gray-200" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 uppercase mb-1">CMS API Token</label>
                <input type="password" value={cmsApiToken} onChange={e => setCmsApiToken(e.target.value)}
                  placeholder="Bearer token untuk CMS API"
                  className="w-full rounded-lg border border-gray-200 bg-amber-50/40 px-3 py-2 text-sm outline-none transition focus:ring-2 focus:ring-amber-300 dark:border-gray-700 dark:bg-neutral-800/70 dark:text-gray-200" />
              </div>
              <button onClick={saveCmsConfig} disabled={savingCms}
                className="rounded-lg bg-amber-500 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-amber-600 disabled:opacity-50">
                {savingCms ? "Menyimpan..." : "Simpan Pengaturan CMS"}
              </button>
            </div>
          )}
        </div>

        {/* Tool Panels */}
        {activeTool === "seo_article" && (
          <SeoArticlePanel sessionId={selectedSession?.id || null} sharedContext={sharedContext}
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

      {toast && <Toast message={toast.msg} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
