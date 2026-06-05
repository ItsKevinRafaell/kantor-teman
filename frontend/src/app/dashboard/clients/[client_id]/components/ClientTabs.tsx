"use client";
import { useState } from "react";
import { FileText, Key, ExternalLink } from "lucide-react";
import NotesTimelineTab from "./NotesTimelineTab";
import CredentialsTab from "./CredentialsTab";
import DocumentsTab from "./DocumentsTab";

interface NoteData {
  id: string;
  category: string;
  content: string;
  actor: string;
  timestamp: string;
}

interface ClientTabsProps {
  clientId: number;
  initialNotes: NoteData[];
}

export default function ClientTabs({ clientId, initialNotes }: ClientTabsProps) {
  const [activeTab, setActiveTab] = useState<"notes" | "credentials" | "documents">("notes");

  const tabs = [
    { key: "notes" as const, label: "Timeline Notes", icon: <FileText size={14} /> },
    { key: "credentials" as const, label: "Kredensial & Akses", icon: <Key size={14} /> },
    { key: "documents" as const, label: "Dokumen & Media", icon: <ExternalLink size={14} /> },
  ];

  return (
    <div className="card overflow-hidden">
      <div className="px-5 py-3 border-b border-[var(--border-default)] flex items-center gap-1 bg-neutral-50/50 dark:bg-neutral-800/30">
        {tabs.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 ${activeTab === tab.key ? "bg-brand-yellow/10 text-brand-yellow shadow-sm" : "text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-700 dark:hover:text-neutral-200"}`}>
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>
      {activeTab === "notes" && <NotesTimelineTab clientId={clientId} initialNotes={initialNotes} />}
      {activeTab === "credentials" && <CredentialsTab clientId={clientId} />}
      {activeTab === "documents" && <DocumentsTab clientId={clientId} />}
    </div>
  );
}
