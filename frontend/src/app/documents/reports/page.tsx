import { Suspense } from "react";
import ReportsContent from "./page.content";

export default function ReportsPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-neutral-400">Memuat laporan...</div>}>
      <ReportsContent />
    </Suspense>
  );
}
