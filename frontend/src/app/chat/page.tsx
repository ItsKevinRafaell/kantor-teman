"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

interface ChatProject {
  id: string;
  name: string;
  description?: string;
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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://api.kantorteman.my.id";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem("token");
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
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export default function ChatPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ChatProject[]>([]);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedProject, setSelectedProject] = useState<ChatProject | null>(null);
  const [selectedConversation, setSelectedConversation] = useState<ChatConversation | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    loadProjects();
  }, [router]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const loadProjects = async () => {
    try {
      const data = await apiFetch<ChatProject[]>("/api/chat/projects");
      setProjects(data);
      if (data.length > 0 && !selectedProject) {
        selectProject(data[0]);
      }
    } catch (e) {
      console.error("Failed to load projects:", e);
    }
  };

  const selectProject = async (project: ChatProject) => {
    setSelectedProject(project);
    setSelectedConversation(null);
    setMessages([]);
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
    const name = prompt("Nama project baru:");
    if (!name) return;
    try {
      const project = await apiFetch<ChatProject>("/api/chat/projects", {
        method: "POST",
        body: JSON.stringify({ name, default_model: "glm-5" }),
      });
      setProjects([project, ...projects]);
      selectProject(project);
    } catch (e) {
      alert("Gagal membuat project");
    }
  };

  const createConversation = async () => {
    if (!selectedProject) return;
    try {
      const conv = await apiFetch<ChatConversation>(`/api/chat/projects/${selectedProject.id}/conversations`, {
        method: "POST",
        body: JSON.stringify({ title: "New Chat" }),
      });
      setConversations([conv, ...conversations]);
      selectConversation(conv);
    } catch (e) {
      alert("Gagal membuat conversation");
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !selectedConversation || loading) return;
    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [
      ...prev,
      { id: "temp", conversation_id: selectedConversation.id, role: "user", content: userMessage, tokens_used: 0, created_at: new Date().toISOString() },
    ]);
    setLoading(true);
    try {
      const res = await apiFetch<{ message: ChatMessage }>(`/api/chat/conversations/${selectedConversation.id}/chat`, {
        method: "POST",
        body: JSON.stringify({ message: userMessage }),
      });
      setMessages((prev) => [...prev.filter((m) => m.id !== "temp"), res.message]);
    } catch (e: any) {
      alert(e.message || "Gagal mengirim pesan");
      setMessages((prev) => prev.filter((m) => m.id !== "temp"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-64px)] bg-[var(--bg-main)]">
      {/* Sidebar - Projects & Conversations */}
      <aside className={`${sidebarOpen ? "w-64" : "w-0"} bg-[var(--bg-surface)] border-r border-[var(--border-subtle)] flex flex-col transition-all duration-200 overflow-hidden`}>
        <div className="p-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <h2 className="font-semibold text-sm text-neutral-700 dark:text-neutral-200">Projects</h2>
          <button onClick={createProject} className="text-xs text-brand-yellow hover:underline">+ New</button>
        </div>
        <div className="flex-1 overflow-y-auto">
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
                    <span className="text-xs text-neutral-400">Chats</span>
                    <button onClick={createConversation} className="text-xs text-brand-yellow hover:underline">+</button>
                  </div>
                  {conversations.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => selectConversation(c)}
                      className={`w-full text-left px-3 py-1.5 text-xs truncate ${selectedConversation?.id === c.id ? "bg-brand-yellow/5 text-brand-yellow" : "text-neutral-500 hover:bg-neutral-50 dark:hover:bg-neutral-900"}`}
                    >
                      {c.title}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <div className="p-4 border-b border-[var(--border-subtle)] flex items-center gap-3 bg-[var(--bg-surface)]">
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-neutral-400 hover:text-neutral-600">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
          </button>
          <h1 className="font-semibold text-neutral-800 dark:text-neutral-100">
            {selectedConversation?.title || "AI Chat"}
          </h1>
          {selectedProject && (
            <span className="text-xs text-neutral-400 bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 rounded">
              {selectedProject.default_model}
            </span>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !loading && (
            <div className="text-center text-neutral-400 text-sm mt-20">
              Mulai percakapan baru dengan AI Assistant
            </div>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-brand-yellow text-neutral-900"
                    : "bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-neutral-100 dark:bg-neutral-800 rounded-2xl px-4 py-2.5 text-sm">
                <span className="animate-pulse">Thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)]">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
              placeholder="Ketik pesan..."
              disabled={!selectedConversation || loading}
              className="flex-1 rounded-xl border border-[var(--border-subtle)] bg-white dark:bg-neutral-900 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-yellow/30 disabled:opacity-50"
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || !selectedConversation || loading}
              className="bg-brand-yellow hover:bg-brand-yellow/90 disabled:opacity-50 disabled:cursor-not-allowed text-neutral-900 font-medium px-5 py-2.5 rounded-xl text-sm transition-colors"
            >
              Kirim
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
