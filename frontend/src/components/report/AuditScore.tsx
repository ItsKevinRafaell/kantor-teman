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
    65
    - (competitor_count > 3 ? 20 : competitor_count > 0 ? 10 : 0)
    - (monthly_search_volume > 500 ? 15 : monthly_search_volume > 0 ? 8 : 0)
    - (hasDigitalAnalysis && painPoints.length >= 3 ? 10 : 0)
    + (hasDigitalAnalysis ? 5 : 0)
  )));

  const scoreColor = score <= 30 ? "#ef4444" : score <= 60 ? "#f59e0b" : "#22c55e";
  const scoreLabel = hasDigitalAnalysis
    ? score <= 30 ? "Kondisi Kritis — Perlu Tindakan Segera" : score <= 60 ? "Perlu Perbaikan Signifikan" : "Cukup Baik, Bisa Ditingkatkan"
    : score <= 60 ? "Sinyal Awal: Perlu Validasi Digital" : "Data Awal Cukup, Perlu Dicek Lanjutan";
  const badges = hasDigitalAnalysis
    ? [
        { label: "SEO: Butuh Perbaikan", className: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" },
        { label: "Maps: Perlu Optimasi", className: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" },
        { label: "Konversi: Rendah", className: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" },
      ]
    : [
        { label: "SEO: Perlu Validasi", className: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" },
        { label: "Maps: Cek Manual", className: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300" },
        { label: "Konversi: Perlu Dicek", className: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300" },
      ];

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
            {hasDigitalAnalysis
              ? `Skor ini dihitung dari hasil AI analysis, sinyal visibilitas Google, tingkat kompetisi di ${city}, dan kesiapan digital ${nama_usaha || "bisnis ini"} saat ini.`
              : `Skor ini adalah estimasi awal dari data lead, kategori, estimasi pencarian, dan pembanding bisnis sejenis di ${city}. Audit teknis tetap perlu dilakukan sebelum mengambil keputusan besar.`}
          </p>
          <div className="flex flex-wrap gap-2 mt-2">
            {badges.map((badge) => (
              <span key={badge.label} className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${badge.className}`}>{badge.label}</span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
