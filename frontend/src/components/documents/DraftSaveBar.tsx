import { CheckCircle, Save, Clock } from "lucide-react";

interface DraftSaveBarProps {
  saving: boolean;
  lastSaved: Date | null;
  hasDraft: boolean;
}

export default function DraftSaveBar({ saving, lastSaved, hasDraft }: DraftSaveBarProps) {
  if (!hasDraft) return null;

  return (
    <div className="flex items-center gap-2 text-xs">
      {saving ? (
        <span className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
          <Clock size={12} className="animate-spin" />
          Menyimpan draft...
        </span>
      ) : lastSaved ? (
        <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
          <CheckCircle size={12} />
          Draft tersimpan {lastSaved.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}
        </span>
      ) : (
        <span className="flex items-center gap-1.5 text-gray-400">
          <Save size={12} />
          Belum tersimpan
        </span>
      )}
    </div>
  );
}
