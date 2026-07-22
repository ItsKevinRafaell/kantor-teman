"use client";
import NativeSelect from "../ui/NativeSelect";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface ArchiveFolder {
  id: string;
  name: string;
  parent_id: string | null;
  lead_id?: number | null;
}

interface GeneratorPreviewProps {
  selectedTemplate: any;
  selectedProject: any;
  selectedLead: any;
  selectedContact: any;
  previewUrl: string | null;
  previewing: boolean;
  handlePreview: () => Promise<void>;
  generating: boolean;
  handleGenerate: () => Promise<void>;
  setStep: (s: number) => void;
  archiveFolders?: ArchiveFolder[];
  archiveFolderId?: string;
  setArchiveFolderId?: (id: string) => void;
}

function folderLabel(folders: ArchiveFolder[], folder: ArchiveFolder): string {
  const parts: string[] = [folder.name];
  let current = folder.parent_id ? folders.find(f => f.id === folder.parent_id) : null;
  const seen = new Set<string>([folder.id]);
  while (current && !seen.has(current.id)) {
    parts.unshift(current.name);
    seen.add(current.id);
    current = current.parent_id ? folders.find(f => f.id === current!.parent_id) : null;
  }
  return parts.join(" / ");
}

export default function GeneratorPreview({
  selectedTemplate, selectedProject, selectedLead, selectedContact,
  previewUrl, previewing, handlePreview, generating, handleGenerate, setStep,
  archiveFolders = [], archiveFolderId = "", setArchiveFolderId,
}: GeneratorPreviewProps) {
  const targetLabel = selectedProject
    ? selectedProject.name
    : selectedLead
      ? selectedLead.business_name
      : selectedContact
        ? selectedContact.business_name
        : "";

  const sortedFolders = [...archiveFolders].sort((a, b) =>
    folderLabel(archiveFolders, a).localeCompare(folderLabel(archiveFolders, b), "id"),
  );

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-bold text-neutral-700 dark:text-neutral-300">Preview &amp; Generate</h2>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{selectedTemplate?.name}{targetLabel ? ` · ${targetLabel}` : ""}</span>
        <button onClick={handlePreview} disabled={previewing}
          className="px-3 py-1.5 border border-gray-200 dark:border-neutral-700 rounded-lg font-semibold hover:bg-gray-50 dark:hover:bg-neutral-800 disabled:opacity-50">
          {previewing ? "Memuat..." : "Refresh Preview"}
        </button>
      </div>
      <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-neutral-700 bg-gray-100 dark:bg-neutral-800">
        {previewUrl ? (
          <iframe src={previewUrl} title="Preview PDF" className="w-full h-[72vh] bg-white" />
        ) : (
          <div className="flex h-80 items-center justify-center text-sm text-gray-400">Preview PDF belum tersedia.</div>
        )}
      </div>

      {setArchiveFolderId && (
        <div className="rounded-xl border border-amber-100 bg-amber-50/40 p-3 dark:border-amber-900/40 dark:bg-amber-950/10">
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Simpan salinan ke folder arsip
          </label>
          <NativeSelect
            value={archiveFolderId}
            onChange={setArchiveFolderId}
            placeholder="— Otomatis (folder klien/proyek) —"
            searchPlaceholder="Cari folder arsip…"
            options={sortedFolders.map(f => ({ value: f.id, label: folderLabel(archiveFolders, f) }))}
          />
          <p className="mt-1 text-[11px] text-neutral-500">
            PDF resmi tetap di Dokumen Resmi. Opsi ini memilih folder di Arsip Tim untuk salinan/link-nya.
          </p>
        </div>
      )}

      <div className="flex justify-between pt-2">
        <button onClick={() => setStep(2)} className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-gray-600 border border-gray-200 rounded-xl">
          <ChevronLeft size={16} /> Kembali
        </button>
        <button onClick={handleGenerate} disabled={generating}
          className="flex items-center gap-1.5 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl disabled:opacity-50">
          {generating ? "Generating..." : "Generate PDF"}
        </button>
      </div>
    </div>
  );
}
