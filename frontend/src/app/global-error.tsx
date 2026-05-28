"use client";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html>
      <body className="bg-[var(--bg-canvas)] dark:bg-[var(--bg-canvas)] text-gray-900 dark:text-neutral-50">
        <div className="flex flex-col items-center justify-center min-h-screen p-8 text-center">
          <div className="w-16 h-16 mb-6 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-red-500">
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h2 className="text-xl font-bold mb-2">Terjadi Kesalahan Sistem</h2>
          <p className="text-sm text-gray-500 mb-6 max-w-md">
            Aplikasi mengalami error yang tidak terduga. Silakan muat ulang halaman.
          </p>
          <button onClick={reset} className="px-4 py-2.5 text-sm font-semibold bg-amber-500 hover:bg-amber-600 text-white rounded-xl">
            Muat Ulang
          </button>
        </div>
      </body>
    </html>
  );
}
