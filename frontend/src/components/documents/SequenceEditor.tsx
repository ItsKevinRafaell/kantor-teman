"use client";

interface SequenceEditorProps {
  showSeqEditor: boolean;
  setShowSeqEditor: (b: boolean) => void;
  seqStartFrom: string;
  setSeqStartFrom: (s: string) => void;
  saveSequence: () => Promise<void>;
  templateType?: string;
}

export default function SequenceEditor({
  showSeqEditor, setShowSeqEditor, seqStartFrom, setSeqStartFrom, saveSequence, templateType,
}: SequenceEditorProps) {
  if (!showSeqEditor) return null;

  const typeLabel = (() => {
    switch (templateType) {
      case "invoice": return "Invoice";
      case "proposal_pdf": return "Proposal";
      case "receipt": return "Bukti Pembayaran";
      case "surat_penawaran": return "Surat Penawaran";
      case "mou": return "MOU";
      case "kontrak": return "Kontrak";
      default: return templateType ? templateType.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase()) : "Dokumen";
    }
  })();

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-neutral-900 rounded-2xl p-6 w-full max-w-sm shadow-xl">
        <h3 className="text-lg font-bold text-neutral-800 dark:text-neutral-100 mb-2">Atur Nomor {typeLabel} Awal</h3>
        <p className="text-xs text-gray-500 mb-4">Nomor {typeLabel.toLowerCase()} berikutnya akan dimulai dari angka ini. Format: PREFIX/BULANTAHUN/NOMOR.</p>
        <input
          type="number"
          min="1"
          value={seqStartFrom}
          onChange={e => setSeqStartFrom(e.target.value)}
          placeholder="1"
          className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 font-mono"
        />
        <div className="flex gap-3 mt-4">
          <button onClick={() => setShowSeqEditor(false)}
            className="flex-1 py-2.5 rounded-xl border border-gray-200 text-sm font-semibold text-gray-600">
            Batal
          </button>
          <button onClick={saveSequence}
            className="flex-1 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold">
            Simpan
          </button>
        </div>
      </div>
    </div>
  );
}