"use client";

import { useEffect, useRef } from "react";

interface Props {
  input: string;
  onInputChange: (v: string) => void;
  onSend: () => void;
  onCancel: () => void;
  loading: boolean;
  agentMode: boolean;
  onAgentModeToggle: () => void;
  disabled: boolean;
}

export default function ChatInput({ input, onInputChange, onSend, onCancel, loading, agentMode, onAgentModeToggle, disabled }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + "px";
    }
  }, [input]);

  return (
    <div className="p-4 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      <div className="flex gap-3 items-end">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => onInputChange(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          placeholder={disabled ? "Pilih conversation dulu" : "Ketik pesan... (Shift+Enter untuk newline)"}
          disabled={disabled}
          rows={1}
          className="flex-1 rounded-xl border border-[var(--border-subtle)] bg-white dark:bg-neutral-900 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-yellow/30 disabled:opacity-50 resize-none max-h-[150px]"
        />
        <button
          onClick={onAgentModeToggle}
          className={`flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-medium transition-colors shrink-0 ${agentMode ? "bg-green-500 text-white" : "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700"}`}
          title={agentMode ? "Agent Mode ON" : "Agent Mode OFF"}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" /></svg>
          Agent
        </button>
        {loading ? (
          <button onClick={onCancel} className="bg-red-500 hover:bg-red-600 text-white font-medium px-5 py-2.5 rounded-xl text-sm transition-colors shrink-0">
            Batal
          </button>
        ) : (
          <button
            onClick={onSend}
            disabled={!input.trim() || disabled}
            className="bg-brand-yellow hover:bg-brand-yellow/90 disabled:opacity-50 disabled:cursor-not-allowed text-neutral-900 font-medium px-5 py-2.5 rounded-xl text-sm transition-colors shrink-0"
          >
            Kirim
          </button>
        )}
      </div>
    </div>
  );
}
