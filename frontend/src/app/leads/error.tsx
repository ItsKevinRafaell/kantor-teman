"use client";

export default function LeadsError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="max-w-6xl mx-auto py-24 text-center">
      <div className="text-4xl mb-4">⚠️</div>
      <h2 className="text-lg font-bold text-neutral-900 dark:text-neutral-50 mb-2">Gagal memuat leads</h2>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">{error.message || "Terjadi kesalahan."}</p>
      <button onClick={reset} className="px-4 py-2.5 bg-brand-yellow hover:bg-amber-600 text-white text-sm font-semibold rounded-xl transition-colors">
        Coba Lagi
      </button>
    </div>
  );
}
