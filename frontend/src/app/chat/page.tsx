"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

interface ChatProject {
  id: string;
  name: string;
  description?: string;
  system_prompt?: string;
  default_model: string;
  context_window_size: number;
  created_at: string;
}

interface ChatConversation {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
}

interface ChatMessage {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  tokens_used: number;
  model_used?: string;
  created_at: string;
}

interface ChatMemory {
  id: string;
  project_id: string;
  content: string;
  created_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://api.kantorteman.my.id";

// Hardcoded models sebagai fallback
const DEFAULT_MODELS = [
  { id: "glm-5", name: "GLM-5", description: "Model cepat dan efisien" },
  { id: "gpt-4o-mini", name: "GPT-4o Mini", description: "Model ringan OpenAI" },
  { id: "claude-haiku-4-5-20251001", name: "Claude Haiku", description: "Model cepat Anthropic" },
];

function getToken(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)kt_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  if (!token) throw new Error("No token");

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    // Check for authentication errors
    if (res.status === 401 || err.detail?.includes("Token") || err.detail?.includes("token")) {
      // Clear invalid cookie and redirect to login
      document.cookie = "kt_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
      window.location.href = "/login";
      throw new Error("Session expired");
    }
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// Modal Component
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

// Simple markdown renderer
function renderMarkdown(text: string): React.ReactNode {
  const parts = text.split(/(```[\s\S]*?```|`[^`]+`|\*\*[^*]+\*\*|\n)/g);
  return parts.map((part, i) => {
    if (part.startsWith("```")) {
      const code = part.replace(/```(\w*)\n?/g, "").replace(/```$/g, "");
      return (
        <pre key={i} className="bg-neutral-900 text-neutral-100 rounded-lg p-3 my-2 overflow-x-auto text-xs">
          <code>{code}</code>
        </pre>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i} className="bg-neutral-200 dark:bg-neutral-700 px-1 rounded text-xs">{part.slice(1, -1)}</code>;
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part === "\n") {
      return <br key={i} />;
    }
    return part;
  });
}

export default function ChatPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ChatProject[]>([]);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [memories, setMemories] = useState<ChatMemory[]>([]);
  const [models, setModels] = useState(DEFAULT_MODELS);
  const [selectedProject, setSelectedProject] = useState<ChatProject | null>(null);
  const [selectedConversation, setSelectedConversation] = useState<ChatConversation | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("glm-5");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [savingMemory, setSavingMemory] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [showMemoryPanel, setShowMemoryPanel] = useState(false);
  const [showProjectSettings, setShowProjectSettings] = useState(false);
  const [showApiSettings, setShowApiSettings] = useState(false);
  const [newMemory, setNewMemory] = useState("");
  const [agentMode, setAgentMode] = useState(false);
  const [lastToolCalls, setLastToolCalls] = useState<any[] | null>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // API Settings states
  const [apiKey, setApiKey] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [savingApiSettings, setSavingApiSettings] = useState(false);

  // Modal states
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showDeleteProjectModal, setShowDeleteProjectModal] = useState(false);
  const [showDeleteConversationModal, setShowDeleteConversationModal] = useState<string | null>(null);
  const [showRenameConversationModal, setShowRenameConversationModal] = useState<string | null>(null);
  const [renameConversationTitle, setRenameConversationTitle] = useState("");
  const [newProjectName, setNewProjectName] = useState("");
  const [toast, setToast] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    loadProjects();
    loadModels();
    loadApiSettings();
  }, [router]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + "px";
    }
  }, [input]);

  const loadProjects = async () => {
    try {
      const data = await apiFetch<ChatProject[]>("/api/chat/projects");
      setProjects(data);
      if (data.length > 0 && !selectedProject) {
        selectProject(data[0]);
      }
    } catch (e: any) {
      console.error("Failed to load projects:", e);
      showToast("Gagal memuat projects: " + e.message);
    }
  };

  const loadModels = async () => {
    try {
      const data = await apiFetch<{ models: { id: string; name: string; description: string }[] }>("/api/chat/models");
      if (data.models && data.models.length > 0) {
        setModels(data.models);
      }
    } catch (e) {
      console.error("Failed to load models, using defaults");
    }
  };

  const loadApiSettings = async () => {
    try {
      const data = await apiFetch<{ openai_api_key: string; ai_base_url: string }>("/api/settings");
      setApiKey(data.openai_api_key || "");
      setApiBaseUrl(data.ai_base_url || "https://api.aimurah.com/v1");
    } catch (e) {
      console.error("Failed to load API settings:", e);
    }
  };

  const saveApiSettings = async () => {
    setSavingApiSettings(true);
    try {
      await apiFetch("/api/settings", {
        method: "PUT",
        body: JSON.stringify({ openai_api_key: apiKey, ai_base_url: apiBaseUrl }),
      });
      showToast("API settings berhasil disimpan");
      setShowApiSettings(false);
    } catch (e: any) {
      showToast("Gagal menyimpan API settings: " + e.message);
    } finally {
      setSavingApiSettings(false);
    }
  };

  const loadMemories = async (projectId: string) => {
    try {
      const data = await apiFetch<ChatMemory[]>(`/api/chat/projects/${projectId}/memories`);
      setMemories(data);
    } catch (e) {
      console.error("Failed to load memories:", e);
    }
  };

  const selectProject = async (project: ChatProject) => {
    setSelectedProject(project);
    setSelectedConversation(null);
    setMessages([]);
    setSelectedModel(project.default_model || "glm-5");
    loadMemories(project.id);
    try {
      const data = await apiFetch<ChatConversation[]>(`/api/chat/projects/${project.id}/conversations`);
      setConversations(data);
      if (data.length > 0) {
        selectConversation(data[0]);
      }
    } catch (e) {
      console.error("Failed to load conversations:", e);
    }
  };

  const selectConversation = async (conv: ChatConversation) => {
    setSelectedConversation(conv);
    try {
      const data = await apiFetch<ChatMessage[]>(`/api/chat/conversations/${conv.id}/messages`);
      setMessages(data);
    } catch (e) {
      console.error("Failed to load messages:", e);
    }
  };

  const createProject = async () => {
    if (!newProjectName.trim()) {
      showToast("Nama project tidak boleh kosong");
      return;
    }
    try {
      const project = await apiFetch<ChatProject>("/api/chat/projects", {
        method: "POST",
        body: JSON.stringify({ name: newProjectName.trim(), default_model: selectedModel }),
      });
      setProjects([project, ...projects]);
      selectProject(project);
      setNewProjectName("");
      setShowNewProjectModal(false);
      showToast("Project berhasil dibuat");
    } catch (e: any) {
      showToast("Gagal membuat project: " + e.message);
    }
  };

  const createConversation = async () => {
    if (!selectedProject) return;
    try {
      const conv = await apiFetch<ChatConversation>(`/api/chat/projects/${selectedProject.id}/conversations`, {
        method: "POST",
        body: JSON.stringify({ project_id: selectedProject.id, title: "New Chat" }),
      });
      setConversations([conv, ...conversations]);
      selectConversation(conv);
      showToast("Conversation berhasil dibuat");
    } catch (e: any) {
      showToast("Gagal membuat conversation: " + e.message);
    }
  };

  const deleteConversation = async (convId: string) => {
    try {
      await apiFetch(`/api/chat/conversations/${convId}`, { method: "DELETE" });
      const remaining = conversations.filter((c) => c.id !== convId);
      setConversations(remaining);
      if (selectedConversation?.id === convId) {
        setSelectedConversation(null);
        setMessages([]);
        if (remaining.length > 0) {
          selectConversation(remaining[0]);
        }
      }
      setShowDeleteConversationModal(null);
      showToast("Conversation dihapus");
    } catch (e: any) {
      showToast("Gagal menghapus: " + e.message);
    }
  };

  const renameConversation = async (convId: string, newTitle: string) => {
    if (!newTitle.trim()) {
      showToast("Nama tidak boleh kosong");
      return;
    }
    try {
      const updated = await apiFetch<ChatConversation>(`/api/chat/conversations/${convId}`, {
        method: "PATCH",
        body: JSON.stringify({ title: newTitle.trim() }),
      });
      setConversations(conversations.map((c) => (c.id === updated.id ? updated : c)));
      if (selectedConversation?.id === convId) {
        setSelectedConversation(updated);
      }
      setShowRenameConversationModal(null);
      showToast("Nama conversation diubah");
    } catch (e: any) {
      showToast("Gagal mengubah nama: " + e.message);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !selectedConversation || loading) return;
    const userMessage = input.trim();
    setInput("");

    // Show user message immediately
    const tempUserMsg: ChatMessage = {
      id: "temp-user",
      conversation_id: selectedConversation.id,
      role: "user",
      content: userMessage,
      tokens_used: 0,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setLoading(true);
    setLastToolCalls(null);

    // Create abort controller for cancel functionality
    abortControllerRef.current = new AbortController();

    try {
      const res = await apiFetch<{
        user_message: ChatMessage;
        message: ChatMessage;
        tool_calls?: any[];
        memory_saved?: boolean;
        memory_content?: string;
        summary_created?: boolean;
        context_info?: {
          total_messages: number;
          recent_messages: number;
          summaries: number;
          memories: number;
        };
      }>(`/api/chat/conversations/${selectedConversation.id}/chat`, {
        method: "POST",
        body: JSON.stringify({ message: userMessage, model: selectedModel, agent_mode: agentMode }),
        signal: abortControllerRef.current.signal,
      });
      // Replace temp message with actual messages from server
      setMessages((prev) => [...prev.filter((m) => m.id !== "temp-user"), res.user_message, res.message]);

      // Show tool calls if any
      if (res.tool_calls && res.tool_calls.length > 0) {
        setLastToolCalls(res.tool_calls);
        const toolNames = res.tool_calls.map((t: any) => t.name).join(", ");
        showToast(`🔧 Tool executed: ${toolNames}`);
      }

      // Show memory saved indicator
      if (res.memory_saved && res.memory_content) {
        setSavingMemory(true);
        setTimeout(() => {
          setSavingMemory(false);
          showToast("💾 Memory disimpan: " + res.memory_content?.substring(0, 50) + "...");
          // Reload memories
          if (selectedProject) {
            loadMemories(selectedProject.id);
          }
        }, 1000);
      }

      // Show summary created indicator
      if (res.summary_created) {
        showToast("📝 Ringkasan percakapan dibuat untuk konteks panjang");
      }
    } catch (e: any) {
      // Remove temp message on error
      setMessages((prev) => prev.filter((m) => m.id !== "temp-user"));
      if (e.name !== "AbortError") {
        showToast("Gagal mengirim: " + e.message);
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  const cancelSend = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setLoading(false);
      setMessages((prev) => prev.filter((m) => m.id !== "temp-user"));
      showToast("Pesan dibatalkan");
    }
  };

  const startEditMessage = (msg: ChatMessage) => {
    setEditingMessageId(msg.id);
    setEditText(msg.content);
  };

  const cancelEdit = () => {
    setEditingMessageId(null);
    setEditText("");
  };

  const submitEdit = async () => {
    if (!editText.trim() || !editingMessageId || !selectedConversation) return;
    try {
      // Find the message index to truncate from
      const msgIndex = messages.findIndex((m) => m.id === editingMessageId);
      if (msgIndex === -1) return;

      // Delete messages from this point onward (except temp messages)
      const messagesToKeep = messages.slice(0, msgIndex);

      // Send the edited message
      const res = await apiFetch<{
        user_message: ChatMessage;
        message: ChatMessage;
        tool_calls?: any[];
        memory_saved?: boolean;
        memory_content?: string;
      }>(`/api/chat/conversations/${selectedConversation.id}/chat`, {
        method: "POST",
        body: JSON.stringify({ message: editText.trim(), model: selectedModel, agent_mode: agentMode }),
      });

      // Update messages: keep previous + new response
      setMessages([...messagesToKeep, res.user_message, res.message]);

      if (res.tool_calls && res.tool_calls.length > 0) {
        setLastToolCalls(res.tool_calls);
      }

      setEditingMessageId(null);
      setEditText("");
      showToast("Pesan direvisi");
    } catch (e: any) {
      showToast("Gagal revisi: " + e.message);
    }
  };

  const addMemory = async () => {
    if (!newMemory.trim() || !selectedProject) return;
    try {
      const memory = await apiFetch<ChatMemory>(`/api/chat/projects/${selectedProject.id}/memories`, {
        method: "POST",
        body: JSON.stringify({ content: newMemory.trim() }),
      });
      setMemories([memory, ...memories]);
      setNewMemory("");
      showToast("Memory ditambahkan");
    } catch (e: any) {
      showToast("Gagal menambah memory: " + e.message);
    }
  };

  const deleteMemory = async (memoryId: string) => {
    try {
      await apiFetch(`/api/chat/memories/${memoryId}`, { method: "DELETE" });
      setMemories(memories.filter((m) => m.id !== memoryId));
      showToast("Memory dihapus");
    } catch (e: any) {
      showToast("Gagal menghapus memory: " + e.message);
    }
  };

  const updateProject = async (updates: Partial<ChatProject>) => {
    if (!selectedProject) return;
    try {
      const updated = await apiFetch<ChatProject>(`/api/chat/projects/${selectedProject.id}`, {
        method: "PUT",
        body: JSON.stringify(updates),
      });
      setProjects(projects.map((p) => (p.id === updated.id ? updated : p)));
      setSelectedProject(updated);
      showToast("Project diupdate");
    } catch (e: any) {
      showToast("Gagal update: " + e.message);
    }
  };

  const deleteProject = async () => {
    if (!selectedProject) return;
    try {
      await apiFetch(`/api/chat/projects/${selectedProject.id}`, { method: "DELETE" });
      const remaining = projects.filter((p) => p.id !== selectedProject.id);
      setProjects(remaining);
      if (remaining.length > 0) {
        selectProject(remaining[0]);
      } else {
        setSelectedProject(null);
        setConversations([]);
        setSelectedConversation(null);
        setMessages([]);
      }
      setShowDeleteProjectModal(false);
      showToast("Project dihapus");
    } catch (e: any) {
      showToast("Gagal menghapus project: " + e.message);
    }
  };

  const exportChat = () => {
    if (!selectedConversation || messages.length === 0) return;
    const content = messages.map((m) => `[${m.role.toUpperCase()}]\n${m.content}`).join("\n\n---\n\n");
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedConversation.title.replace(/[^a-z0-9]/gi, "_")}_${new Date().toISOString().split("T")[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Chat diexport");
  };

  const totalTokens = messages.reduce((sum, m) => sum + (m.tokens_used || 0), 0);

  return (
    <div className="flex h-[calc(100vh-64px)] bg-[var(--bg-main)]">
      {/* Toast */}
      {toast && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[100] bg-neutral-900 text-white px-4 py-2 rounded-lg text-sm shadow-lg animate-fade-in">
          {toast}
        </div>
      )}

      {/* Sidebar */}
      <aside className={`${sidebarOpen ? "w-64" : "w-0"} bg-[var(--bg-surface)] border-r border-[var(--border-subtle)] flex flex-col transition-all duration-200 overflow-hidden`}>
        <div className="p-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <h2 className="font-semibold text-sm text-neutral-700 dark:text-neutral-200">Projects</h2>
          <button onClick={() => setShowNewProjectModal(true)} className="text-xs text-brand-yellow hover:underline">+ New</button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {projects.length === 0 && (
            <div className="p-4 text-xs text-neutral-400 text-center">
              Belum ada project. Klik + New untuk membuat.
            </div>
          )}
          {projects.map((p) => (
            <div key={p.id}>
              <button
                onClick={() => selectProject(p)}
                className={`w-full text-left px-4 py-2 text-sm ${selectedProject?.id === p.id ? "bg-brand-yellow/10 text-brand-yellow" : "text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}
              >
                {p.name}
              </button>
              {selectedProject?.id === p.id && (
                <div className="ml-4 border-l border-[var(--border-subtle)]">
                  <div className="p-2 flex items-center justify-between">
                    <span className="text-xs text-neutral-400">Chats ({conversations.length})</span>
                    <button onClick={createConversation} className="text-xs text-brand-yellow hover:underline">+</button>
                  </div>
                  {conversations.map((c) => (
                    <div key={c.id} className="group flex items-center">
                      <button
                        onClick={() => selectConversation(c)}
                        className={`flex-1 text-left px-3 py-1.5 text-xs truncate ${selectedConversation?.id === c.id ? "bg-brand-yellow/5 text-brand-yellow" : "text-neutral-500 hover:bg-neutral-50 dark:hover:bg-neutral-900"}`}
                      >
                        {c.title}
                      </button>
                      <button
                        onClick={() => {
                          setRenameConversationTitle(c.title);
                          setShowRenameConversationModal(c.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 px-1 text-neutral-400 hover:text-neutral-600"
                        title="Rename"
                      >
                        ✎
                      </button>
                      <button
                        onClick={() => setShowDeleteConversationModal(c.id)}
                        className="opacity-0 group-hover:opacity-100 px-1 text-red-400 hover:text-red-600"
                        title="Delete"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative">
        {/* Header */}
        <div className="p-4 border-b border-[var(--border-subtle)] flex items-center gap-3 bg-[var(--bg-surface)]">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-neutral-400 hover:text-neutral-600">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
          </button>
          <h1 className="font-semibold text-neutral-800 dark:text-neutral-100 flex-1 truncate">
            {selectedConversation?.title || "AI Chat"}
          </h1>

          {/* Model Selector */}
          <div className="relative">
            <button
              onClick={() => setShowModelSelector(!showModelSelector)}
              className="flex items-center gap-2 text-xs bg-neutral-100 dark:bg-neutral-800 px-3 py-1.5 rounded-lg hover:bg-neutral-200 dark:hover:bg-neutral-700"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M12 1v6m0 6v10M4.22 4.22l4.24 4.24m7.07 7.07l4.24 4.24M1 12h6m6 0h10M4.22 19.78l4.24-4.24m7.07-7.07l4.24-4.24" /></svg>
              {models.find((m) => m.id === selectedModel)?.name || selectedModel}
            </button>
            {showModelSelector && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowModelSelector(false)} />
                <div className="absolute right-0 top-full mt-1 bg-white dark:bg-neutral-900 border border-[var(--border-subtle)] rounded-lg shadow-lg z-50 min-w-[200px]">
                  {models.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => {
                        setSelectedModel(m.id);
                        setShowModelSelector(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs ${selectedModel === m.id ? "bg-brand-yellow/10 text-brand-yellow" : "hover:bg-neutral-50 dark:hover:bg-neutral-800"}`}
                    >
                      <div className="font-medium">{m.name}</div>
                      <div className="text-neutral-400 text-[10px]">{m.description}</div>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Memory Button */}
          <button
            onClick={() => setShowMemoryPanel(!showMemoryPanel)}
            className={`p-2 rounded-lg ${showMemoryPanel ? "bg-brand-yellow/10 text-brand-yellow" : "text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}
            title="Memory Bank"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z" /><path d="M12 6v6l4 2" /></svg>
          </button>

          {/* Project Settings Button */}
          <button
            onClick={() => setShowProjectSettings(!showProjectSettings)}
            className={`p-2 rounded-lg ${showProjectSettings ? "bg-brand-yellow/10 text-brand-yellow" : "text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}
            title="Project Settings"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
          </button>

          {/* API Settings Button */}
          <button
            onClick={() => setShowApiSettings(!showApiSettings)}
            className={`p-2 rounded-lg ${showApiSettings ? "bg-brand-yellow/10 text-brand-yellow" : "text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}
            title="API Settings"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" /></svg>
          </button>

          {/* Export Button */}
          <button
            onClick={exportChat}
            disabled={messages.length === 0}
            className="p-2 rounded-lg text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 disabled:opacity-50"
            title="Export Chat"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
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

        {/* Project Settings Panel */}
        {showProjectSettings && selectedProject && (
          <>
            <div className="fixed inset-0 z-30" onClick={() => setShowProjectSettings(false)} />
            <div className="absolute right-4 top-[60px] w-80 bg-white dark:bg-neutral-900 border border-[var(--border-subtle)] rounded-lg shadow-lg z-40">
              <div className="p-3 border-b border-[var(--border-subtle)] flex items-center justify-between">
                <h3 className="font-medium text-sm">Project Settings</h3>
                <button onClick={() => setShowProjectSettings(false)} className="text-neutral-400 hover:text-neutral-600">×</button>
              </div>
              <div className="p-4 space-y-3">
                <div>
                  <label className="text-xs text-neutral-500 block mb-1">Nama Project</label>
                  <input
                    type="text"
                    defaultValue={selectedProject.name}
                    onBlur={(e) => updateProject({ name: e.target.value })}
                    className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="text-xs text-neutral-500 block mb-1">System Prompt</label>
                  <textarea
                    defaultValue={selectedProject.system_prompt || ""}
                    onBlur={(e) => updateProject({ system_prompt: e.target.value })}
                    placeholder="Instruksi khusus untuk AI"
                    rows={3}
                    className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2 resize-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-neutral-500 block mb-1">Context Window</label>
                  <input
                    type="number"
                    defaultValue={selectedProject.context_window_size}
                    onBlur={(e) => updateProject({ context_window_size: parseInt(e.target.value) || 20 })}
                    min={5}
                    max={100}
                    className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2"
                  />
                </div>
                <div className="pt-2 border-t border-[var(--border-subtle)]">
                  <button onClick={() => setShowDeleteProjectModal(true)} className="text-xs text-red-500 hover:text-red-700">
                    Hapus Project
                  </button>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Memory Panel */}
        {showMemoryPanel && selectedProject && (
          <>
            <div className="fixed inset-0 z-30" onClick={() => setShowMemoryPanel(false)} />
            <div className="absolute right-4 top-[60px] w-80 bg-white dark:bg-neutral-900 border border-[var(--border-subtle)] rounded-lg shadow-lg z-40">
              <div className="p-3 border-b border-[var(--border-subtle)]">
                <h3 className="font-medium text-sm">Memory Bank</h3>
                <p className="text-[10px] text-neutral-400">Info yang diingat AI dalam project ini</p>
              </div>
              <div className="max-h-48 overflow-y-auto p-2 space-y-2">
                {memories.length === 0 && (
                  <p className="text-xs text-neutral-400 text-center py-4">Belum ada memory</p>
                )}
                {memories.map((m) => (
                  <div key={m.id} className="group flex items-start gap-2 bg-neutral-50 dark:bg-neutral-800 p-2 rounded text-xs">
                    <span className="flex-1">{m.content}</span>
                    <button onClick={() => deleteMemory(m.id)} className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600">×</button>
                  </div>
                ))}
              </div>
              <div className="p-3 border-t border-[var(--border-subtle)] flex gap-2">
                <input
                  type="text"
                  value={newMemory}
                  onChange={(e) => setNewMemory(e.target.value)}
                  placeholder="Tambah memory..."
                  className="flex-1 text-xs border border-[var(--border-subtle)] rounded px-2 py-1"
                  onKeyDown={(e) => e.key === "Enter" && addMemory()}
                />
                <button onClick={addMemory} className="text-xs bg-brand-yellow text-neutral-900 px-2 py-1 rounded font-medium">Add</button>
              </div>
            </div>
          </>
        )}

        {/* API Settings Panel */}
        {showApiSettings && (
          <>
            <div className="fixed inset-0 z-30" onClick={() => setShowApiSettings(false)} />
            <div className="absolute right-4 top-[60px] w-80 bg-white dark:bg-neutral-900 border border-[var(--border-subtle)] rounded-lg shadow-lg z-40">
              <div className="p-3 border-b border-[var(--border-subtle)] flex items-center justify-between">
                <h3 className="font-medium text-sm">API Settings</h3>
                <button onClick={() => setShowApiSettings(false)} className="text-neutral-400 hover:text-neutral-600">×</button>
              </div>
              <div className="p-4 space-y-3">
                <div>
                  <label className="text-xs text-neutral-500 block mb-1">API Key</label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="sk-..."
                    className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2"
                  />
                </div>
                <div>
                  <label className="text-xs text-neutral-500 block mb-1">API Base URL</label>
                  <input
                    type="text"
                    value={apiBaseUrl}
                    onChange={(e) => setApiBaseUrl(e.target.value)}
                    placeholder="https://api.aimurah.com/v1"
                    className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2"
                  />
                </div>
                <div className="pt-2 flex justify-end gap-2">
                  <button onClick={() => setShowApiSettings(false)} className="text-sm text-neutral-500 hover:text-neutral-700 px-3 py-1.5">
                    Batal
                  </button>
                  <button
                    onClick={saveApiSettings}
                    disabled={savingApiSettings}
                    className="text-sm bg-brand-yellow text-neutral-900 px-4 py-1.5 rounded font-medium disabled:opacity-50"
                  >
                    {savingApiSettings ? "Menyimpan..." : "Simpan"}
                  </button>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!selectedProject && (
            <div className="text-center text-neutral-400 text-sm mt-20">
              <div className="text-4xl mb-4">💬</div>
              <p>Buat project baru untuk mulai chat</p>
            </div>
          )}
          {selectedProject && !selectedConversation && (
            <div className="text-center text-neutral-400 text-sm mt-20">
              <div className="text-4xl mb-4">💬</div>
              <p>Buat conversation baru untuk mulai chat</p>
              <button onClick={createConversation} className="mt-4 text-brand-yellow hover:underline text-sm">
                + Buat Conversation
              </button>
            </div>
          )}
          {selectedConversation && messages.length === 0 && !loading && (
            <div className="text-center text-neutral-400 text-sm mt-20">
              <div className="text-4xl mb-4">💬</div>
              <p>Mulai percakapan dengan AI</p>
              <p className="text-xs mt-2 text-neutral-500">Model: {models.find((m) => m.id === selectedModel)?.name}</p>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} gap-2`}>
              {editingMessageId === msg.id ? (
                <div className="max-w-[85%] flex flex-col gap-2">
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="rounded-xl border border-brand-yellow bg-white dark:bg-neutral-900 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-yellow/30 resize-none"
                    rows={3}
                    autoFocus
                  />
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={cancelEdit}
                      className="text-xs text-neutral-500 hover:text-neutral-700 px-3 py-1"
                    >
                      Batal
                    </button>
                    <button
                      onClick={submitEdit}
                      className="text-xs bg-brand-yellow text-neutral-900 px-3 py-1 rounded font-medium"
                    >
                      Revisi
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                    msg.role === "user"
                      ? "bg-brand-yellow text-neutral-900"
                      : "bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{msg.role === "assistant" ? renderMarkdown(msg.content) : msg.content}</div>
                  {msg.model_used && (
                    <div className="text-[10px] text-neutral-400 mt-1">{msg.model_used} • {msg.tokens_used} tokens</div>
                  )}
                </div>
              )}
              {msg.role === "user" && editingMessageId !== msg.id && idx === messages.length - 1 && !loading && (
                <button
                  onClick={() => startEditMessage(msg)}
                  className="text-neutral-400 hover:text-neutral-600 self-end mb-1"
                  title="Revisi pesan"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                </button>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-neutral-100 dark:bg-neutral-800 rounded-2xl px-4 py-2.5 text-sm">
                <span className="animate-pulse">{agentMode ? "Executing..." : "Thinking..."}</span>
              </div>
            </div>
          )}
          {lastToolCalls && lastToolCalls.length > 0 && (
            <div className="flex justify-start opacity-60 hover:opacity-100 transition-opacity">
              <div className="bg-neutral-100 dark:bg-neutral-800 rounded-xl px-3 py-2 text-[10px] max-w-[85%]">
                <div className="text-neutral-400 mb-1">
                  {lastToolCalls.filter(t => t.result?.success).length}/{lastToolCalls.length} tools: {lastToolCalls.map(t => t.name).join(", ")}
                </div>
              </div>
            </div>
          )}
          {savingMemory && (
            <div className="flex justify-center">
              <div className="bg-brand-yellow/10 text-brand-yellow rounded-full px-4 py-1.5 text-xs flex items-center gap-2">
                <span className="animate-spin">💾</span>
                <span>Menyimpan memory...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)]">
          <div className="flex gap-3 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder={selectedConversation ? "Ketik pesan... (Shift+Enter untuk newline)" : "Pilih conversation dulu"}
              disabled={!selectedConversation || loading}
              rows={1}
              className="flex-1 rounded-xl border border-[var(--border-subtle)] bg-white dark:bg-neutral-900 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-yellow/30 disabled:opacity-50 resize-none max-h-[150px]"
            />
            <button
              onClick={() => setAgentMode(!agentMode)}
              className={`flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-medium transition-colors shrink-0 ${agentMode ? "bg-green-500 text-white" : "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700"}`}
              title={agentMode ? "Agent Mode ON - AI dapat mengeksekusi aksi" : "Agent Mode OFF - AI hanya chat biasa"}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" /></svg>
              Agent
            </button>
            {loading ? (
              <button
                onClick={cancelSend}
                className="bg-red-500 hover:bg-red-600 text-white font-medium px-5 py-2.5 rounded-xl text-sm transition-colors shrink-0"
              >
                Batal
              </button>
            ) : (
              <button
                onClick={sendMessage}
                disabled={!input.trim() || !selectedConversation}
                className="bg-brand-yellow hover:bg-brand-yellow/90 disabled:opacity-50 disabled:cursor-not-allowed text-neutral-900 font-medium px-5 py-2.5 rounded-xl text-sm transition-colors shrink-0"
              >
                Kirim
              </button>
            )}
          </div>
        </div>
      </div>

      {/* New Project Modal */}
      <Modal open={showNewProjectModal} onClose={() => setShowNewProjectModal(false)} title="Buat Project Baru">
        <div className="space-y-4">
          <div>
            <label className="text-xs text-neutral-500 block mb-1">Nama Project</label>
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="Contoh: Customer Support Bot"
              className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2"
              autoFocus
              onKeyDown={(e) => e.key === "Enter" && createProject()}
            />
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowNewProjectModal(false)} className="text-sm text-neutral-500 hover:text-neutral-700 px-3 py-1.5">
              Batal
            </button>
            <button onClick={createProject} className="text-sm bg-brand-yellow text-neutral-900 px-4 py-1.5 rounded font-medium">
              Buat
            </button>
          </div>
        </div>
      </Modal>

      {/* Delete Project Modal */}
      <Modal open={showDeleteProjectModal} onClose={() => setShowDeleteProjectModal(false)} title="Hapus Project">
        <div className="space-y-4">
          <p className="text-sm text-neutral-600 dark:text-neutral-300">
            Yakin hapus project "{selectedProject?.name}" dan semua conversation di dalamnya?
          </p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowDeleteProjectModal(false)} className="text-sm text-neutral-500 hover:text-neutral-700 px-3 py-1.5">
              Batal
            </button>
            <button onClick={deleteProject} className="text-sm bg-red-500 text-white px-4 py-1.5 rounded font-medium">
              Hapus
            </button>
          </div>
        </div>
      </Modal>

      {/* Delete Conversation Modal */}
      <Modal open={!!showDeleteConversationModal} onClose={() => setShowDeleteConversationModal(null)} title="Hapus Conversation">
        <div className="space-y-4">
          <p className="text-sm text-neutral-600 dark:text-neutral-300">
            Yakin hapus conversation ini?
          </p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowDeleteConversationModal(null)} className="text-sm text-neutral-500 hover:text-neutral-700 px-3 py-1.5">
              Batal
            </button>
            <button onClick={() => showDeleteConversationModal && deleteConversation(showDeleteConversationModal)} className="text-sm bg-red-500 text-white px-4 py-1.5 rounded font-medium">
              Hapus
            </button>
          </div>
        </div>
      </Modal>

      {/* Rename Conversation Modal */}
      <Modal open={!!showRenameConversationModal} onClose={() => setShowRenameConversationModal(null)} title="Ubah Nama Chat">
        <div className="space-y-4">
          <div>
            <label className="text-xs text-neutral-500 block mb-1">Nama Chat</label>
            <input
              type="text"
              value={renameConversationTitle}
              onChange={(e) => setRenameConversationTitle(e.target.value)}
              placeholder="Nama chat"
              className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2"
              autoFocus
              onKeyDown={(e) => e.key === "Enter" && showRenameConversationModal && renameConversation(showRenameConversationModal, renameConversationTitle)}
            />
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowRenameConversationModal(null)} className="text-sm text-neutral-500 hover:text-neutral-700 px-3 py-1.5">
              Batal
            </button>
            <button
              onClick={() => showRenameConversationModal && renameConversation(showRenameConversationModal, renameConversationTitle)}
              className="text-sm bg-brand-yellow text-neutral-900 px-4 py-1.5 rounded font-medium"
            >
              Simpan
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
