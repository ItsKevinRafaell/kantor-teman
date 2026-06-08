import { Suspense } from "react";
import DocumentsContent from "./page.content";

export default function DocumentsPage() {
  return (
    <Suspense fallback={
      <div className="flex flex-col md:flex-row gap-4 md:gap-6 h-full animate-pulse">
        <div className="w-full md:w-48 shrink-0 space-y-2">
          {[1, 2, 3].map(i => <div key={i} className="h-9 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />)}
        </div>
        <div className="flex-1 space-y-4">
          <div className="h-10 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-36 bg-neutral-100 dark:bg-neutral-800 rounded-2xl" />)}
          </div>
        </div>
      </div>
    }>
      <DocumentsContent />
    </Suspense>
  );
}
