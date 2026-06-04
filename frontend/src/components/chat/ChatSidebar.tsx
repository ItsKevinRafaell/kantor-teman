"use client";

import { Pencil } from "lucide-react";
import type { ChatProject, ChatConversation } from "./types";

interface Props {
  projects: ChatProject[];
  selectedProject: ChatProject | null;
  conversations: ChatConversation[];
  selectedConversation: ChatConversation | null;
  sidebarOpen: boolean;
  onSelectProject: (p: ChatProject) => void;
  onCreateConversation: () => void;
  onSelectConversation: (c: ChatConversation) => void;
  onToggleSidebar: () => void;
  onShowNewProjectModal: () => void;
  onShowMobilePicker: () => void;
  onRenameConversation: (c: ChatConversation) => void;
  onDeleteConversation: (c: ChatConversation) => void;
}

export default function ChatSidebar({
  projects, selectedProject, conversations, selectedConversation,
  sidebarOpen, onSelectProject, onCreateConversation,
  onSelectConversation, onToggleSidebar, onShowNewProjectModal,
  onShowMobilePicker, onRenameConversation, onDeleteConversation,
}: Props) {
  return (
    <>
      {/* Desktop Sidebar */}
      <aside className={`hidden lg:flex flex-col shrink-0 ${sidebarOpen ? "lg:w-64" : "lg:w-0"} bg-[var(--bg-surface)] border-r border-[var(--border-subtle)] transition-all duration-200 overflow-hidden`}>
        <div className="p-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <h2 className="font-semibold text-sm text-neutral-700 dark:text-neutral-200">Projects</h2>
          <button onClick={onShowNewProjectModal} className="text-xs text-brand-yellow hover:underline">+ New</button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {projects.length === 0 && (
            <div className="p-4 text-xs text-neutral-400 text-center">
              Belum ada project.
            </div>
          )}
          {projects.map(p => (
            <div key={p.id}>
              <button
                onClick={() => onSelectProject(p)}
                className={`w-full text-left px-4 py-2 text-sm ${selectedProject?.id === p.id ? "bg-brand-yellow/10 text-brand-yellow" : "text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"}`}
              >
                {p.name}
              </button>
              {selectedProject?.id === p.id && (
                <div className="ml-4 border-l border-[var(--border-subtle)]">
                  <div className="p-2 flex items-center justify-between">
                    <span className="text-xs text-neutral-400">Chats ({conversations.length})</span>
                    <button onClick={onCreateConversation} className="text-xs text-brand-yellow hover:underline">+</button>
                  </div>
                  {conversations.map(c => (
                    <div key={c.id} className="group flex items-center">
                      <button
                        onClick={() => onSelectConversation(c)}
                        className={`flex-1 text-left px-3 py-1.5 text-xs truncate ${selectedConversation?.id === c.id ? "bg-brand-yellow/5 text-brand-yellow" : "text-neutral-500 hover:bg-neutral-50 dark:hover:bg-neutral-900"}`}
                      >
                        {c.title}
                      </button>
                      <button
                        onClick={() => onRenameConversation(c)}
                        className="opacity-0 group-hover:opacity-100 px-1 text-neutral-400 hover:text-neutral-600"
                        title="Rename"
                      >
                        <Pencil size={12} />
                      </button>
                      <button
                        onClick={() => onDeleteConversation(c)}
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

      {/* Desktop sidebar toggle */}
      <button onClick={onToggleSidebar} className="hidden lg:block fixed left-0 top-1/2 -translate-y-1/2 z-40 p-2 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-r-lg text-neutral-400 hover:text-neutral-600">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
      </button>

      {/* Mobile toggle */}
      <button onClick={onShowMobilePicker} className="lg:hidden fixed bottom-20 right-4 z-40 p-3 bg-brand-yellow text-neutral-900 rounded-full shadow-lg">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
      </button>
    </>
  );
}
