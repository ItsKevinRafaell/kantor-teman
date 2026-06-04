"use client";

import { useEffect, useRef } from "react";
import { apiFetch } from "../../lib/api";
import type { ChatMessage } from "./types";
import ChatMessageBubble from "./ChatMessageBubble";

interface Props {
  messages: ChatMessage[];
  loading: boolean;
  agentMode: boolean;
  lastToolCalls: any[] | null;
  savingMemory: boolean;
  editingMessageId: string | null;
  editText: string;
  onEditTextChange: (t: string) => void;
  onCancelEdit: () => void;
  onSubmitEdit: () => void;
  onStartEdit: (msg: ChatMessage) => void;
}

export default function ChatMessageList({
  messages, loading, agentMode, lastToolCalls, savingMemory,
  editingMessageId, editText, onEditTextChange, onCancelEdit, onSubmitEdit, onStartEdit,
}: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0 && !loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="text-center text-neutral-400 text-sm">
          <div className="text-4xl mb-4 text-neutral-300">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="mx-auto"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          </div>
          <p>Mulai percakapan dengan AI</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((msg, idx) => (
        <ChatMessageBubble
          key={msg.id}
          message={msg}
          isEditing={editingMessageId === msg.id}
          editText={editText}
          onEditTextChange={onEditTextChange}
          onCancelEdit={onCancelEdit}
          onSubmitEdit={onSubmitEdit}
          onStartEdit={onStartEdit}
          isLastUser={msg.role === "user" && idx === messages.length - 1}
          isLoading={loading}
        />
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
              {lastToolCalls.filter((t: any) => t.result?.success).length}/{lastToolCalls.length} tools: {lastToolCalls.map((t: any) => t.name).join(", ")}
            </div>
          </div>
        </div>
      )}
      {savingMemory && (
        <div className="flex justify-center">
          <div className="bg-brand-yellow/10 text-brand-yellow rounded-full px-4 py-1.5 text-xs flex items-center gap-2">
            <span className="animate-spin inline-block w-4 h-4 border-2 border-neutral-400 border-t-transparent rounded-full"></span>
            <span>Menyimpan memory...</span>
          </div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
