"use client";

interface Props {
  competitor_count: number;
  monthly_search_volume: number;
  painPoints: string[];
  hasDigitalAnalysis: boolean;
  city: string;
  nama_usaha: string | null;
}

export function AuditScore({ competitor_count, monthly_search_volume, painPoints, hasDigitalAnalysis, city, nama_usaha }: Props) {
  const score = Math.max(10, Math.min(100, Math.round(
    (competitor_count > 3 ? 10 : 25) +
    (monthly_search_volume > 500 ? 5 : 15) +
    (painPoints.length >= 3 ? 5 : 20) +
    (hasDigitalAnalysis ? 10 : 0)
  )));

  const scoreColor = score <= 30 ? "#ef4444" : score <= 60 ? "#f59e0b" : "#22c55e";
  const scoreLabel = score <= 30 ? "Kondisi Kritis — Perlu Tindakan Segera" : score <= 60 ? "Perlu Perbaikan Signifikan" : "Cukup Baik, Bisa Ditingkatkan";

  return (
    <section className="bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-700 rounded-2xl p-6 shadow-sm">
      <p className="text-[10px] uppercase tracking-widest text-zinc-600 dark:text-zinc-400 font-bold mb-4">Skor Kesehatan Digital</p>
      <div className="flex items-center gap-6">
        {/* Speedometer */}
        <div className="relative w-28 h-28 shrink-0">
          <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
            <circle cx="60" cy="60" r="50" fill="none" stroke="#e4e4e7" strokeWidth="12" className="dark:stroke-zinc-700" />
            <circle cx="60" cy="60" r="50" fill="none" stroke={scoreColor} strokeWidth="12" strokeLinecap="round"
              strokeDasharray={`${Math.round((score / 100) * 314)} 314`}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-black text-zinc-900 dark:text-white">{score}</span>
            <span className="text-[9px] text-zinc-500 font-bold">/100</span>
          </div>
        </div>
        <div className="flex-1 space-y-2">
          <p className="text-base font-bold text-zinc-900 dark:text-white">{scoreLabel}</p>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
            Skor ini dihitung berdasarkan visibilitas Google, tingkat kompetisi di {city}, dan kesiapan digital {nama_usaha} saat ini.
          </p>
          <div className="flex flex-wrap gap-2 mt-2">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-semibold dark:bg-red-900/30 dark:text-red-400">SEO: Lemah</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-semibold dark:bg-red-900/30 dark:text-red-400">Maps: Tidak Terlihat</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold dark:bg-amber-900/30 dark:text-amber-400">Konversi: Rendah</span>
          </div>
        </div>
      </div>
    </section>
  );
}