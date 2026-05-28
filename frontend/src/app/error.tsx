"use client";

import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Page error:", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center">
      <div className="w-16 h-16 mb-6 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-red-500">
          <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-50 mb-2">Terjadi Kesalahan</h2>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6 max-w-md">
        Halaman ini mengalami error. Coba muat ulang atau kembali ke dashboard.
      </p>
      <div className="flex gap-3">
        <button onClick={reset} className="btn-primary">Coba Lagi</button>
        <a href="/dashboard" className="btn-ghost">Ke Dashboard</a>
      </div>
    </div>
  );
}
