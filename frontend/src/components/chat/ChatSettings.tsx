"use client";

import type { ChatProject, ChatMemory } from "./types";

interface Props {
  showProjectSettings: boolean;
  showMemoryPanel: boolean;
  showApiSettings: boolean;
  selectedProject: ChatProject | null;
  memories: ChatMemory[];
  apiKey: string;
  apiBaseUrl: string;
  savingApiSettings: boolean;
  onCloseAll: () => void;
  onCloseProjectSettings: () => void;
  onCloseMemoryPanel: () => void;
  onCloseApiSettings: () => void;
  onUpdateProject: (updates: Partial<ChatProject>) => void;
  onDeleteProject: () => void;
  onAddMemory: () => void;
  onDeleteMemory: (id: string) => void;
  onApiKeyChange: (v: string) => void;
  onApiBaseUrlChange: (v: string) => void;
  onSaveApiSettings: () => void;
  newMemory: string;
  onNewMemoryChange: (v: string) => void;
  onShowDeleteProjectModal: () => void;
}

export default function ChatSettings({
  showProjectSettings, showMemoryPanel, showApiSettings,
  selectedProject, memories, apiKey, apiBaseUrl, savingApiSettings,
  onCloseAll, onCloseProjectSettings, onCloseMemoryPanel, onCloseApiSettings,
  onUpdateProject, onDeleteProject, onAddMemory, onDeleteMemory,
  onApiKeyChange, onApiBaseUrlChange, onSaveApiSettings,
  newMemory, onNewMemoryChange, onShowDeleteProjectModal,
}: Props) {
  const anyPanel = showProjectSettings || showMemoryPanel || showApiSettings;

  if (!anyPanel) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-30" onClick={onCloseAll} />

      {/* Project Settings */}
      {showProjectSettings && selectedProject && (
        <div className="absolute right-4 top-[60px] w-80 bg-white dark:bg-neutral-900 border border-[var(--border-subtle)] rounded-lg shadow-lg z-40">
          <div className="p-3 border-b border-[var(--border-subtle)] flex items-center justify-between">
            <h3 className="font-medium text-sm">Project Settings</h3>
            <button onClick={onCloseProjectSettings} className="text-neutral-400 hover:text-neutral-600">×</button>
          </div>
          <div className="p-4 space-y-3">
            <div>
              <label className="text-xs text-neutral-500 block mb-1">Nama Project</label>
              <input type="text" defaultValue={selectedProject.name}
                onBlur={e => onUpdateProject({ name: e.target.value })}
                className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2" />
            </div>
            <div>
              <label className="text-xs text-neutral-500 block mb-1">System Prompt</label>
              <textarea defaultValue={selectedProject.system_prompt || ""}
                onBlur={e => onUpdateProject({ system_prompt: e.target.value })}
                placeholder="Instruksi khusus untuk AI" rows={3}
                className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2 resize-none" />
            </div>
            <div>
              <label className="text-xs text-neutral-500 block mb-1">Context Window</label>
              <input type="number" defaultValue={selectedProject.context_window_size}
                onBlur={e => onUpdateProject({ context_window_size: parseInt(e.target.value) || 20 })}
                min={5} max={100}
                className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2" />
            </div>
            <div className="pt-2 border-t border-[var(--border-subtle)]">
              <button onClick={onShowDeleteProjectModal} className="text-xs text-red-500 hover:text-red-700">Hapus Project</button>
            </div>
          </div>
        </div>
      )}

      {/* Memory Panel */}
      {showMemoryPanel && selectedProject && (
        <div className="absolute right-4 top-[60px] w-80 bg-white dark:bg-neutral-900 border border-[var(--border-subtle)] rounded-lg shadow-lg z-40">
          <div className="p-3 border-b border-[var(--border-subtle)]">
            <h3 className="font-medium text-sm">Memory Bank</h3>
            <p className="text-[10px] text-neutral-400">Info yang diingat AI dalam project ini</p>
          </div>
          <div className="max-h-48 overflow-y-auto p-2 space-y-2">
            {memories.length === 0 && (
              <p className="text-xs text-neutral-400 text-center py-4">Belum ada memory</p>
            )}
            {memories.map(m => (
              <div key={m.id} className="group flex items-start gap-2 bg-neutral-50 dark:bg-neutral-800 p-2 rounded text-xs">
                <span className="flex-1">{m.content}</span>
                <button onClick={() => onDeleteMemory(m.id)} className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600">×</button>
              </div>
            ))}
          </div>
          <div className="p-3 border-t border-[var(--border-subtle)] flex gap-2">
            <input type="text" value={newMemory} onChange={e => onNewMemoryChange(e.target.value)}
              placeholder="Tambah memory..." className="flex-1 text-xs border border-[var(--border-subtle)] rounded px-2 py-1"
              onKeyDown={e => e.key === "Enter" && onAddMemory()} />
            <button onClick={onAddMemory} className="text-xs bg-brand-yellow text-neutral-900 px-2 py-1 rounded font-medium">Add</button>
          </div>
        </div>
      )}

      {/* API Settings */}
      {showApiSettings && (
        <div className="absolute right-4 top-[60px] w-80 bg-white dark:bg-neutral-900 border border-[var(--border-subtle)] rounded-lg shadow-lg z-40">
          <div className="p-3 border-b border-[var(--border-subtle)] flex items-center justify-between">
            <h3 className="font-medium text-sm">API Settings</h3>
            <button onClick={onCloseApiSettings} className="text-neutral-400 hover:text-neutral-600">×</button>
          </div>
          <div className="p-4 space-y-3">
            <div>
              <label className="text-xs text-neutral-500 block mb-1">API Key</label>
              <input type="password" value={apiKey} onChange={e => onApiKeyChange(e.target.value)}
                placeholder="sk-..." className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2" />
            </div>
            <div>
              <label className="text-xs text-neutral-500 block mb-1">API Base URL</label>
              <input type="text" value={apiBaseUrl} onChange={e => onApiBaseUrlChange(e.target.value)}
                placeholder="http://localhost:20128/v1" className="w-full text-sm border border-[var(--border-subtle)] rounded px-3 py-2" />
            </div>
            <div className="pt-2 flex justify-end gap-2">
              <button onClick={onCloseApiSettings} className="text-sm text-neutral-500 hover:text-neutral-700 px-3 py-1.5">Batal</button>
              <button onClick={onSaveApiSettings} disabled={savingApiSettings}
                className="text-sm bg-brand-yellow text-neutral-900 px-4 py-1.5 rounded font-medium disabled:opacity-50">
                {savingApiSettings ? "Menyimpan..." : "Simpan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
