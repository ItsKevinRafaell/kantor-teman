"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useApi } from "../../lib/swr";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://api.kantorteman.my.id";
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    if (res.status === 401) { window.location.href = "/login"; throw new Error("Session expired"); }
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

import ChatSidebar from "../../components/chat/ChatSidebar";
import ChatMessageList from "../../components/chat/ChatMessageList";
import ChatInput from "../../components/chat/ChatInput";
import ChatSettings from "../../components/chat/ChatSettings";

import type { ChatProject, ChatConversation, ChatMessage, ChatMemory, ChatModel } from "../../components/chat/types";
import { DEFAULT_MODELS } from "../../components/chat/types";

function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-neutral-900 rounded-xl shadow-xl max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-4 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
          <h3 className="font-semibold">{title}</h3>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600 text-xl leading-none">&times;</button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const router = useRouter();
  const abortRef = useRef<AbortController | null>(null);

  // ─── SWR data ───────────────────────────────────────────────────────────────
  const { data: projectsData = [] } = useApi<ChatProject[]>("/api/chat/projects");
  const { data: modelsData } = useApi<{ models: ChatModel[] }>("/api/chat/models");
  const { data: settingsData } = useApi<{ ai_api_key: string; ai_base_url: string }>("/api/settings");

  // ─── Local state ──────────────────────────────────────────────────────────
  const [projects, setProjects] = useState<ChatProject[]>(projectsData);
  const [selectedProject, setSelectedProject] = useState<ChatProject | null>(null);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<ChatConversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [memories, setMemories] = useState<ChatMemory[]>([]);
  const [models, setModels] = useState<ChatModel[]>(DEFAULT_MODELS);
  const [selectedModel, setSelectedModel] = useState("combo-genflow");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [agentMode, setAgentMode] = useState(false);
  const [lastToolCalls, setLastToolCalls] = useState<any[] | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [savingMemory, setSavingMemory] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [fullscreen, setFullscreen] = useState(false);
  const [showMobilePicker, setShowMobilePicker] = useState(false);
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [showProjectSettings, setShowProjectSettings] = useState(false);
  const [showMemoryPanel, setShowMemoryPanel] = useState(false);
  const [showApiSettings, setShowApiSettings] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [savingApiSettings, setSavingApiSettings] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  // Modals
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showDeleteProjectModal, setShowDeleteProjectModal] = useState(false);
  const [showRenameConvModal, setShowRenameConvModal] = useState<ChatConversation | null>(null);
  const [showDeleteConvModal, setShowDeleteConvModal] = useState<ChatConversation | null>(null);
  const [renameConvTitle, setRenameConvTitle] = useState("");
  const [newProjectName, setNewProjectName] = useState("");
  const [newMemory, setNewMemory] = useState("");

  // ─── Sync SWR → local ────────────────────────────────────────────────────
  useEffect(() => { setProjects(projectsData); }, [projectsData]);
  useEffect(() => { if (modelsData?.models?.length) setModels(modelsData.models); }, [modelsData]);
  useEffect(() => { if (settingsData) { setApiKey(settingsData.ai_api_key || ""); setApiBaseUrl(settingsData.ai_base_url || ""); } }, [settingsData]);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }, []);

  // ─── Auth guard ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!localStorage.getItem("kt_email")) router.push("/login");
  }, [router]);

  // ─── Project / conversation loaders ────────────────────────────────────────
  const loadMemories = async (projectId: string) => {
    try { setMemories(await apiFetch<ChatMemory[]>(`/api/chat/projects/${projectId}/memories`)); } catch { /* ok */ }
  };

  const selectProject = async (p: ChatProject) => {
    setSelectedProject(p);
    setSelectedConversation(null);
    setMessages([]);
    setSelectedModel(p.default_model || "combo-genflow");
    loadMemories(p.id);
    try {
      const data = await apiFetch<ChatConversation[]>(`/api/chat/projects/${p.id}/conversations`);
      setConversations(data);
      if (data.length > 0) selectConversation(data[0]);
    } catch { /* ok */ }
  };

  const selectConversation = async (c: ChatConversation) => {
    setSelectedConversation(c);
    try { setMessages(await apiFetch<ChatMessage[]>(`/api/chat/conversations/${c.id}/messages`)); } catch { /* ok */ }
  };

  // ─── CRUD actions ─────────────────────────────────────────────────────────
  async function createProject() {
    if (!newProjectName.trim()) return;
    try {
      const p = await apiFetch<ChatProject>("/api/chat/projects", {
        method: "POST", body: JSON.stringify({ name: newProjectName.trim(), default_model: selectedModel }),
      });
      setProjects(prev => [p, ...prev]);
      selectProject(p);
      setShowNewProjectModal(false);
      setNewProjectName("");
      showToast("Project berhasil dibuat");
    } catch (e: any) { showToast("Gagal: " + e.message); }
  }

  async function createConversation() {
    if (!selectedProject) return;
    try {
      const c = await apiFetch<ChatConversation>(`/api/chat/projects/${selectedProject.id}/conversations`, {
        method: "POST", body: JSON.stringify({ project_id: selectedProject.id, title: "New Chat" }),
      });
      setConversations(prev => [c, ...prev]);
      selectConversation(c);
      showToast("Conversation dibuat");
    } catch (e: any) { showToast("Gagal: " + e.message); }
  }

  async function deleteConversation(c: ChatConversation) {
    try {
      await apiFetch(`/api/chat/conversations/${c.id}`, { method: "DELETE" });
      const remaining = conversations.filter(x => x.id !== c.id);
      setConversations(remaining);
      if (selectedConversation?.id === c.id) {
        setSelectedConversation(null);
        setMessages([]);
        if (remaining.length > 0) selectConversation(remaining[0]);
      }
      showToast("Conversation dihapus");
    } catch (e: any) { showToast("Gagal: " + e.message); }
  }

  async function renameConversation(c: ChatConversation, newTitle: string) {
    if (!newTitle.trim()) return;
    try {
      const updated = await apiFetch<ChatConversation>(`/api/chat/conversations/${c.id}`, {
        method: "PATCH", body: JSON.stringify({ title: newTitle.trim() }),
      });
      setConversations(prev => prev.map(x => x.id === updated.id ? updated : x));
      if (selectedConversation?.id === c.id) setSelectedConversation(updated);
      showToast("Nama diubah");
    } catch (e: any) { showToast("Gagal: " + e.message); }
  }

  async function sendMessage() {
    if (!input.trim() || !selectedConversation || loading) return;
    const userMsg = input.trim();
    setInput("");
    const temp: ChatMessage = { id: "temp-user", conversation_id: selectedConversation.id, role: "user", content: userMsg, tokens_used: 0, created_at: new Date().toISOString() };
    setMessages(prev => [...prev, temp]);
    setLoading(true);
    setLastToolCalls(null);
    abortRef.current = new AbortController();

    try {
      const res = await apiFetch<{
        user_message: ChatMessage; message: ChatMessage; tool_calls?: any[];
        memory_saved?: boolean; memory_content?: string;
      }>(`/api/chat/conversations/${selectedConversation.id}/chat`, {
        method: "POST",
        body: JSON.stringify({ message: userMsg, model: selectedModel, agent_mode: agentMode }),
        signal: abortRef.current.signal,
      });
      setMessages(prev => [...prev.filter(m => m.id !== "temp-user"), res.user_message, res.message]);
      if (res.tool_calls?.length) { setLastToolCalls(res.tool_calls); showToast(`Tool: ${res.tool_calls.map((t: any) => t.name).join(", ")}`); }
      if (res.memory_saved) {
        setSavingMemory(true);
        setTimeout(() => { setSavingMemory(false); showToast("Memory disimpan"); if (selectedProject) loadMemories(selectedProject.id); }, 1000);
      }
    } catch (e: any) {
      setMessages(prev => prev.filter(m => m.id !== "temp-user"));
      if (e.name !== "AbortError") showToast("Gagal: " + e.message);
    } finally { setLoading(false); abortRef.current = null; }
  }

  function cancelSend() {
    abortRef.current?.abort();
    setLoading(false);
    setMessages(prev => prev.filter(m => m.id !== "temp-user"));
    showToast("Pesan dibatalkan");
  }

  async function submitEdit() {
    if (!editText.trim() || !editingMessageId || !selectedConversation) return;
    const idx = messages.findIndex(m => m.id === editingMessageId);
    if (idx === -1) return;
    try {
      const res = await apiFetch<{ user_message: ChatMessage; message: ChatMessage; tool_calls?: any[] }>(
        `/api/chat/conversations/${selectedConversation.id}/chat`, {
        method: "POST", body: JSON.stringify({ message: editText.trim(), model: selectedModel, agent_mode: agentMode }),
      });
      setMessages([...messages.slice(0, idx), res.user_message, res.message]);
      setEditingMessageId(null); setEditText("");
      showToast("Pesan direvisi");
    } catch (e: any) { showToast("Gagal: " + e.message); }
  }

  async function addMemory() {
    if (!newMemory.trim() || !selectedProject) return;
    try {
      const m = await apiFetch<ChatMemory>(`/api/chat/projects/${selectedProject.id}/memories`, {
        method: "POST", body: JSON.stringify({ content: newMemory.trim() }),
      });
      setMemories(prev => [m, ...prev]);
      setNewMemory("");
      showToast("Memory ditambahkan");
    } catch (e: any) { showToast("Gagal: " + e.message); }
  }

  async function deleteMemory(id: string) {
    try { await apiFetch(`/api/chat/memories/${id}`, { method: "DELETE" }); setMemories(prev => prev.filter(m => m.id !== id)); showToast("Memory dihapus"); }
    catch (e: any) { showToast("Gagal: " + e.message); }
  }

  async function updateProject(updates: Partial<ChatProject>) {
    if (!selectedProject) return;
    try {
      const updated = await apiFetch<ChatProject>(`/api/chat/projects/${selectedProject.id}`, { method: "PUT", body: JSON.stringify(updates) });
      setProjects(prev => prev.map(p => p.id === updated.id ? updated : p));
      setSelectedProject(updated);
      showToast("Project diupdate");
    } catch (e: any) { showToast("Gagal: " + e.message); }
  }

  async function deleteProject() {
    if (!selectedProject) return;
    try {
      await apiFetch(`/api/chat/projects/${selectedProject.id}`, { method: "DELETE" });
      const remaining = projects.filter(p => p.id !== selectedProject.id);
      setProjects(remaining);
      if (remaining.length > 0) selectProject(remaining[0]);
      else { setSelectedProject(null); setConversations([]); setSelectedConversation(null); setMessages([]); }
      setShowDeleteProjectModal(false);
      showToast("Project dihapus");
    } catch (e: any) { showToast("Gagal: " + e.message); }
  }

  async function saveApiSettings() {
    setSavingApiSettings(true);
    try { await apiFetch("/api/settings", { method: "PUT", body: JSON.stringify({ ai_api_key: apiKey, ai_base_url: apiBaseUrl, ai_provider: "9router" }) }); showToast("Settings 9router disimpan"); setShowApiSettings(false); }
    catch (e: any) { showToast("Gagal: " + e.message); }
    finally { setSavingApiSettings(false); }
  }

  function exportChat() {
    if (!selectedConversation || messages.length === 0) return;
    const content = messages.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join("\n\n---\n\n");
    const blob = new Blob([content], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${selectedConversation.title.replace(/[^a-z0-9]/gi, "_")}_${new Date().toISOString().split("T")[0]}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
    showToast("Chat diexport");
  }

  const totalTokens = messages.reduce((sum, m) => sum + (m.tokens_used || 0), 0);

  // ─── Render ───────────────────────────────────────────────────────────────
  return (
    <div className={fullscreen ? "fixed inset-0 z-50 flex bg-[var(--bg-main)]" : "flex h-full bg-[var(--bg-main)]"}>

      {/* Toast */}
      {toast && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[100] bg-neutral-900 text-white px-4 py-2 rounded-lg text-sm shadow-lg animate-fade-in">
          {toast}
        </div>
      )}

      <ChatSidebar
        projects={projects} selectedProject={selectedProject}
        conversations={conversations} selectedConversation={selectedConversation}
        sidebarOpen={sidebarOpen}
        onSelectProject={selectProject} onCreateConversation={createConversation}
        onSelectConversation={selectConversation}
        onToggleSidebar={() => setSidebarOpen(o => !o)}
        onShowNewProjectModal={() => setShowNewProjectModal(true)}
        onShowMobilePicker={() => setShowMobilePicker(true)}
        onRenameConversation={c => { setRenameConvTitle(c.title); setShowRenameConvModal(c); }}
        onDeleteConversation={c => setShowDeleteConvModal(c)}
      />

      {/* Main Area */}
      <div className="flex-1 flex flex-col relative">
        {/* Header */}
        <div className="p-4 border-b border-[var(--border-subtle)] flex items-center gap-3 bg-[var(--bg-surface)]">
          <a href="/dashboard" className="text-neutral-400 hover:text-neutral-600" title="Kembali">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>
          </a>
          <button onClick={() => setFullscreen(o => !o)} className="text-neutral-400 hover:text-neutral-600">
            {fullscreen ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 3v3a2 2 0 0 1-2 2H3"/><path d="M21 8h-3a2 2 0 0 1-2-2V3"/><path d="M3 16h3a2 2 0 0 1 2 2v3"/><path d="M16 21v-3a2 2 0 0 1 2-2h3"/></svg> : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/></svg>}
          </button>
          <h1 className="font-semibold text-neutral-800 dark:text-neutral-100 flex-1 truncate">
            {selectedConversation?.title || "AI Chat"}
          </h1>

          {/* Model Selector */}
          <div className="relative">
            <button onClick={() => setShowModelSelector(o => !o)}
              className="flex items-center gap-2 text-xs bg-neutral-100 dark:bg-neutral-800 px-3 py-1.5 rounded-lg hover:bg-neutral-200 dark:hover:bg-neutral-700">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 6v10M4.22 4.22l4.24 4.24m7.07 7.07l4.24 4.24M1 12h6m6 0h10M4.22 19.78l4.24-4.24m7.07-7.07l4.24-4.24"/></svg>
              {models.find(m => m.id === selectedModel)?.name || selectedModel}
            </button>
            {showModelSelector && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowModelSelector(false)} />
                <div className="absolute right-0 top-full mt-1 bg-white dark:bg-neutral-900 border border-[var(--border-subtle)] rounded-lg shadow-lg z-50 min-w-[200px]">
                  {models.map(m => (
                    <button key={m.id} onClick={() => { setSelectedModel(m.id); setShowModelSelector(false); }}
                      className={`w-full text-left px-3 py-2 text-xs ${selectedModel === m.id ? "bg-brand-yellow/10 text-brand-yellow" : "hover:bg-neutral-50 dark:hover:bg-neutral-800"}`}>
                      <div className="font-medium">{m.name}</div>
                      <div className="text-neutral-400 text-[10px]">{m.description}</div>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          <button onClick={() => setShowMemoryPanel(o => !o)} className={`p-2 rounded-lg ${showMemoryPanel ? "bg-brand-yellow/10 text-brand-yellow" : "text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`} title="Memory">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"/><path d="M12 6v6l4 2"/></svg>
          </button>
          <button onClick={() => setShowProjectSettings(o => !o)} className={`p-2 rounded-lg ${showProjectSettings ? "bg-brand-yellow/10 text-brand-yellow" : "text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`} title="Project Settings">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          </button>
          <button onClick={() => setShowApiSettings(o => !o)} className={`p-2 rounded-lg ${showApiSettings ? "bg-brand-yellow/10 text-brand-yellow" : "text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`} title="API Settings">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
          </button>
          <button onClick={exportChat} disabled={messages.length === 0}
            className="p-2 rounded-lg text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 disabled:opacity-50" title="Export">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          </button>
        </div>

        {/* Context Indicator */}
        {selectedProject && messages.length > 0 && (
          <div className="px-4 py-2 bg-neutral-50 dark:bg-neutral-900 border-b border-[var(--border-subtle)] flex items-center gap-4 text-xs text-neutral-500">
            <span>Context: {Math.min(messages.length, selectedProject.context_window_size)} messages</span>
            {memories.length > 0 && <span>Memories: {memories.length}</span>}
            {selectedProject.system_prompt && <span className="text-brand-yellow">System prompt aktif</span>}
            {totalTokens > 0 && <span className="ml-auto">Tokens: {totalTokens.toLocaleString()}</span>}
          </div>
        )}

        {/* Settings Panels */}
        <ChatSettings
          showProjectSettings={showProjectSettings} showMemoryPanel={showMemoryPanel} showApiSettings={showApiSettings}
          selectedProject={selectedProject} memories={memories}
          apiKey={apiKey} apiBaseUrl={apiBaseUrl} savingApiSettings={savingApiSettings}
          onCloseAll={() => { setShowProjectSettings(false); setShowMemoryPanel(false); setShowApiSettings(false); }}
          onCloseProjectSettings={() => setShowProjectSettings(false)} onCloseMemoryPanel={() => setShowMemoryPanel(false)} onCloseApiSettings={() => setShowApiSettings(false)}
          onUpdateProject={updateProject} onDeleteProject={deleteProject}
          onAddMemory={addMemory} onDeleteMemory={deleteMemory}
          onApiKeyChange={setApiKey} onApiBaseUrlChange={setApiBaseUrl} onSaveApiSettings={saveApiSettings}
          newMemory={newMemory} onNewMemoryChange={setNewMemory}
          onShowDeleteProjectModal={() => setShowDeleteProjectModal(true)}
        />

        {/* Empty states */}
        {!selectedProject && (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-neutral-400 text-sm">Buat project baru untuk mulai chat</p>
          </div>
        )}
        {selectedProject && !selectedConversation && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-neutral-300"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            <p className="text-neutral-400 text-sm">Buat conversation baru</p>
            <button onClick={createConversation} className="text-brand-yellow hover:underline text-sm">+ Buat Conversation</button>
          </div>
        )}

        {/* Messages */}
        {selectedConversation && (
          <ChatMessageList
            messages={messages} loading={loading} agentMode={agentMode}
            lastToolCalls={lastToolCalls} savingMemory={savingMemory}
            editingMessageId={editingMessageId} editText={editText}
            onEditTextChange={setEditText} onCancelEdit={() => { setEditingMessageId(null); setEditText(""); }}
            onSubmitEdit={submitEdit} onStartEdit={m => { setEditingMessageId(m.id); setEditText(m.content); }}
          />
        )}

        {/* Input */}
        <ChatInput
          input={input} onInputChange={setInput}
          onSend={sendMessage} onCancel={cancelSend}
          loading={loading} agentMode={agentMode} onAgentModeToggle={() => setAgentMode(o => !o)}
          disabled={!selectedConversation}
        />
      </div>

      {/* New Project Modal */}
      <Modal open={showNewProjectModal} onClose={() => setShowNewProjectModal(false)} title="Buat Project Baru">
        <div className="space-y-4">
          <input type="text" value={newProjectName} onChange={e => setNewProjectName(e.target.value)}
            placeholder="Contoh: Customer Support Bot" className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2"
            autoFocus onKeyDown={e => e.key === "Enter" && createProject()} />
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowNewProjectModal(false)} className="text-sm text-neutral-500 hover:text-neutral-700 px-3 py-1.5">Batal</button>
            <button onClick={createProject} className="text-sm bg-brand-yellow text-neutral-900 px-4 py-1.5 rounded font-medium">Buat</button>
          </div>
        </div>
      </Modal>

      {/* Delete Project Modal */}
      <Modal open={showDeleteProjectModal} onClose={() => setShowDeleteProjectModal(false)} title="Hapus Project">
        <p className="text-sm text-neutral-600 dark:text-neutral-300 mb-4">Yakin hapus project "{selectedProject?.name}"?</p>
        <div className="flex justify-end gap-2">
          <button onClick={() => setShowDeleteProjectModal(false)} className="text-sm text-neutral-500 px-3 py-1.5">Batal</button>
          <button onClick={deleteProject} className="text-sm bg-red-500 text-white px-4 py-1.5 rounded font-medium">Hapus</button>
        </div>
      </Modal>

      {/* Rename Conversation Modal */}
      <Modal open={!!showRenameConvModal} onClose={() => setShowRenameConvModal(null)} title="Ubah Nama Chat">
        <input type="text" value={renameConvTitle} onChange={e => setRenameConvTitle(e.target.value)}
          className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2 mb-4" autoFocus
          onKeyDown={e => e.key === "Enter" && showRenameConvModal && renameConversation(showRenameConvModal, renameConvTitle)} />
        <div className="flex justify-end gap-2">
          <button onClick={() => setShowRenameConvModal(null)} className="text-sm text-neutral-500 px-3 py-1.5">Batal</button>
          <button onClick={() => showRenameConvModal && renameConversation(showRenameConvModal, renameConvTitle)} className="text-sm bg-brand-yellow text-neutral-900 px-4 py-1.5 rounded font-medium">Simpan</button>
        </div>
      </Modal>

      {/* Delete Conversation Modal */}
      <Modal open={!!showDeleteConvModal} onClose={() => setShowDeleteConvModal(null)} title="Hapus Conversation">
        <p className="text-sm text-neutral-600 dark:text-neutral-300 mb-4">Yakin hapus conversation ini?</p>
        <div className="flex justify-end gap-2">
          <button onClick={() => setShowDeleteConvModal(null)} className="text-sm text-neutral-500 px-3 py-1.5">Batal</button>
          <button onClick={() => showDeleteConvModal && deleteConversation(showDeleteConvModal)} className="text-sm bg-red-500 text-white px-4 py-1.5 rounded font-medium">Hapus</button>
        </div>
      </Modal>
    </div>
  );
}
