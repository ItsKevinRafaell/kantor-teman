import { FileText, Trash2, RotateCcw } from "lucide-react";

interface Draft {
  id: string;
  template_id: string | null;
  template_name: string | null;
  target_type: string | null;
  target_id: string | null;
  variables_json: Record<string, string>;
  created_at: string;
  updated_at: string | null;
}

interface DraftLoaderProps {
  drafts: Draft[];
  loading: boolean;
  onResume: (draft: Draft) => void;
  onDelete: (draftId: string) => void;
  onDismiss: () => void;
}

// Replicate backend _build_pdf_display_name logic:
// TYPE_ClientSlug_InvoiceNo → e.g. INV_UMKM-Maju-Jaya_INV-202606-001
function buildDraftDisplayName(draft: Draft): string {
  const vars = draft.variables_json || {};
  const klien = vars.klien || vars.nama || "";
  const invoiceNo = vars.nomor_invoice || vars.no_invoice || "";
  const docNumber = vars.nomor || "";
  const numberRef = invoiceNo || docNumber;

  // Build type prefix (same as backend _DOC_TYPE_PREFIX)
  const templateType = draft.template_name?.toLowerCase() || "";
  let prefix = "DOC";
  if (templateType.includes("invoice")) prefix = "INV";
  else if (templateType.includes("receipt") || templateType.includes("kwitansi")) prefix = "RCPT";
  else if (templateType.includes("kontrak") && templateType.includes("web")) prefix = "KONTRAK-WD";
  else if (templateType.includes("kontrak") && templateType.includes("seo")) prefix = "KONTRAK-SEO";
  else if (templateType.includes("kontrak") && templateType.includes("sosmed")) prefix = "KONTRAK-SM";
  else if (templateType.includes("kontrak") && templateType.includes("maintenance")) prefix = "KONTRAK-MTN";
  else if (templateType.includes("kontrak") && templateType.includes("branding")) prefix = "KONTRAK-BRAND";
  else if (templateType.includes("kontrak") && templateType.includes("retainer")) prefix = "KONTRAK-RET";
  else if (templateType.includes("kontrak")) prefix = "KONTRAK";
  else if (templateType.includes("mou")) prefix = "MOU";
  else if (templateType.includes("penawaran")) prefix = "SP";
  else if (templateType.includes("proposal")) prefix = "PROPOSAL";

  // Client slug: strip special chars, replace spaces with dashes
  const clientSlug = klien.replace(/[^a-zA-Z0-9\s-]/g, "").trim().replace(/\s+/g, "-") || "Dokumen";

  if (invoiceNo) {
    const invSlug = invoiceNo.replace(/\//g, "-").replace(/\s+/g, "-");
    return `${prefix}_${clientSlug}_${invSlug}`;
  }

  return `${prefix}_${clientSlug}`;
}

export default function DraftLoader({ drafts, loading, onResume, onDelete, onDismiss }: DraftLoaderProps) {
  if (loading) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/20 p-4">
        <p className="text-sm text-amber-700 dark:text-amber-300">Memeriksa draft tersimpan...</p>
      </div>
    );
  }

  if (drafts.length === 0) return null;

  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/20 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-amber-600 dark:text-amber-400" />
          <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-200">
            Draft Tersimpan ({drafts.length})
          </h3>
        </div>
        <button onClick={onDismiss} className="text-xs text-amber-500 hover:text-amber-700 dark:hover:text-amber-300">
          Tutup
        </button>
      </div>

      <div className="space-y-2">
        {drafts.map(draft => {
          const displayName = buildDraftDisplayName(draft);
          const updatedOrCreated = draft.updated_at || draft.created_at;
          const timeStr = new Date(updatedOrCreated).toLocaleDateString("id-ID", {
            day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit"
          });

          return (
            <div key={draft.id} className="flex items-center justify-between rounded-xl border border-amber-200 dark:border-amber-800 bg-white dark:bg-neutral-900 p-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-neutral-800 dark:text-neutral-100 truncate font-mono">
                  {displayName}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {draft.template_name} — {timeStr}
                </p>
              </div>
              <div className="flex items-center gap-1 ml-3 shrink-0">
                <button onClick={() => onResume(draft)}
                  className="flex items-center gap-1 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold rounded-lg transition-colors">
                  <RotateCcw size={12} /> Lanjutkan
                </button>
                <button onClick={() => onDelete(draft.id)}
                  className="p-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors" title="Hapus draft">
                  <Trash2 size={12} className="text-red-400" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
