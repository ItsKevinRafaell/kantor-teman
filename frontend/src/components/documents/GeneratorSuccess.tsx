"use client";
import { Download, Mail, Check } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface GeneratorSuccessProps {
  generatedDoc: any;
  previewUrl: string | null;
  setPreviewUrl: (url: string | null) => void;
  setStep: (s: number) => void;
  setSelectedTemplate: (t: any) => void;
  setSelectedLead: (l: any) => void;
  setSelectedContact: (c: any) => void;
  setSelectedProject: (p: any) => void;
  setVariables: (v: Record<string, string>) => void;
  setLineItems: (v: any) => void;
  setGeneratedDoc: (d: any) => void;
  setTargetType: (t: "empty" | "lead" | "contact" | "project") => void;
  setTargetSearch: (s: string) => void;
  onNewDocument: () => void;
}

export default function GeneratorSuccess({
  generatedDoc, previewUrl, setPreviewUrl, setStep, setSelectedTemplate,
  setSelectedLead, setSelectedContact, setSelectedProject, setVariables,
  setLineItems, setGeneratedDoc, setTargetType, setTargetSearch, onNewDocument,
}: GeneratorSuccessProps) {
  if (!generatedDoc) return null;

  const handleReset = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setStep(0);
    setSelectedTemplate(null);
    setSelectedLead(null);
    setSelectedContact(null);
    setSelectedProject(null);
    setVariables({});
    setLineItems({});
    setGeneratedDoc(null);
    setTargetType("empty");
    setTargetSearch("");
    onNewDocument?.();
  };

  return (
    <div className="space-y-4 text-center">
      <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto">
        <Check size={28} className="text-green-600" />
      </div>
      <h2 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">PDF Berhasil Dibuat!</h2>
      <p className="text-sm text-gray-500">{generatedDoc.template_name}</p>
      <div className="flex gap-3 justify-center pt-2">
        <a href={`${API_BASE}/api/documents/${generatedDoc.id}/download`} target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl">
          <Download size={16} /> Download PDF
        </a>
        <button onClick={() => onNewDocument && onNewDocument()}
          className="flex items-center gap-2 px-5 py-2.5 border-2 border-gray-200 hover:border-gray-400 text-gray-700 dark:text-neutral-200 text-sm font-semibold rounded-xl">
          <Mail size={16} /> Kirim Email
        </button>
      </div>
      <button onClick={handleReset} className="text-xs text-gray-400 hover:text-gray-600 underline mt-2">
        Generate dokumen lain
      </button>
    </div>
  );
}