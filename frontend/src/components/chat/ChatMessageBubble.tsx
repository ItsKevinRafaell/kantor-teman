"use client";

import { useRef, useEffect } from "react";
import type { ChatMessage } from "./types";

interface Props {
  message: ChatMessage;
  isEditing: boolean;
  editText: string;
  onEditTextChange: (t: string) => void;
  onCancelEdit: () => void;
  onSubmitEdit: () => void;
  onStartEdit: (msg: ChatMessage) => void;
  isLastUser: boolean;
  isLoading: boolean;
}

function renderMarkdown(text: string): React.ReactNode {
  const parts = text.split(/(```[\s\S]*?```|`[^`]+`|\*\*[^*]+\*\*|\n)/g);
  return parts.map((part, i) => {
    if (part.startsWith("```")) {
      const code = part.replace(/```(\w*)\n?/g, "").replace(/```$/g, "");
      return <pre key={i} className="bg-neutral-900 text-neutral-100 rounded-lg p-3 my-2 overflow-x-auto text-xs"><code>{code}</code></pre>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i} className="bg-neutral-200 dark:bg-neutral-700 px-1 rounded text-xs">{part.slice(1, -1)}</code>;
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part === "\n") return <br key={i} />;
    return part;
  });
}

export default function ChatMessageBubble({
  message, isEditing, editText, onEditTextChange,
  onCancelEdit, onSubmitEdit, onStartEdit, isLastUser, isLoading,
}: Props) {
  return (
    <div className={`flex ${message.role === "user" ? "justify-end" : "justify-start"} gap-2`}>
      {isEditing ? (
        <div className="max-w-[85%] flex flex-col gap-2">
          <textarea
            value={editText}
            onChange={e => onEditTextChange(e.target.value)}
            className="rounded-xl border border-brand-yellow bg-white dark:bg-neutral-900 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-yellow/30 resize-none"
            rows={3}
            autoFocus
          />
          <div className="flex gap-2 justify-end">
            <button onClick={onCancelEdit} className="text-xs text-neutral-500 hover:text-neutral-700 px-3 py-1">Batal</button>
            <button onClick={onSubmitEdit} className="text-xs bg-brand-yellow text-neutral-900 px-3 py-1 rounded font-medium">Revisi</button>
          </div>
        </div>
      ) : (
        <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${message.role === "user" ? "bg-brand-yellow text-neutral-900" : "bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200"}`}>
          <div className="whitespace-pre-wrap">{message.role === "assistant" ? renderMarkdown(message.content) : message.content}</div>
          {message.model_used && (
            <div className="text-[10px] text-neutral-400 mt-1">{message.model_used} • {message.tokens_used} tokens</div>
          )}
        </div>
      )}
      {message.role === "user" && !isEditing && isLastUser && !isLoading && (
        <button onClick={() => onStartEdit(message)} className="text-neutral-400 hover:text-neutral-600 self-end mb-1" title="Revisi pesan">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
        </button>
      )}
    </div>
  );
}
