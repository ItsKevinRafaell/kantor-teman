"use client";

interface ReportPainBoxProps {
  painPoints: string[];
  monthly_search_volume: number;
  city: string;
  category: string | null;
  hasDigitalAnalysis: boolean;
}

export default function ReportPainBox({ painPoints, monthly_search_volume, city, category, hasDigitalAnalysis }: ReportPainBoxProps) {
  const defaultPainPoints = [
    `Visibilitas lokal di ${city} perlu dicek agar calon pelanggan mudah menemukan bisnis Anda.`,
    "Website atau profil bisnis perlu punya alur kontak yang jelas agar pengunjung tidak berhenti di tengah jalan.",
    "Konten, review, dan CTA perlu dirapikan supaya calon pelanggan lebih cepat percaya dan menghubungi.",
  ];

  return (
    <section className="bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-200 dark:border-amber-800 rounded-2xl p-6 shadow-sm">
      <div className="mb-4 space-y-2">
        <h2 className="text-sm font-bold uppercase tracking-widest text-amber-700 dark:text-amber-400">
          {hasDigitalAnalysis ? "Masalah Kritis yang Ditemukan" : "Area yang Perlu Dicek"}
        </h2>
        {!hasDigitalAnalysis && (
          <p className="text-xs leading-relaxed text-amber-900 dark:text-amber-100">
            Belum ada AI analysis scrape detail untuk lead ini, jadi poin di bawah memakai data awal: kategori bisnis, kota, estimasi pencarian, dan pembanding dari database lead.
          </p>
        )}
      </div>
      <div className="space-y-4">
        {(painPoints.length > 0 ? painPoints : defaultPainPoints).map((point, i) => (
          <div key={i} className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">{i + 1}</div>
            <p className="text-sm text-zinc-900 dark:text-zinc-100 leading-relaxed font-medium">{point}</p>
          </div>
        ))}
      </div>
      {monthly_search_volume > 0 && (
        <div className="mt-6 pt-5 border-t-2 border-amber-200 dark:border-amber-800">
          <p className="text-[10px] uppercase tracking-widest text-zinc-700 dark:text-zinc-300 font-bold mb-3">Fakta Pasar Digital — {city}</p>
          <div className="flex items-end gap-3 mb-3">
            <span className="text-4xl md:text-5xl font-black text-amber-600 tracking-tight">{monthly_search_volume.toLocaleString("id-ID")}</span>
            <span className="text-sm text-zinc-700 dark:text-zinc-300 font-medium pb-1">pencarian/bulan</span>
          </div>
          <div className="w-full h-2 bg-amber-200 rounded-full overflow-hidden"><div className="bg-amber-500 h-full rounded-full" style={{ width: "75%" }}></div></div>
          <p className="text-sm text-zinc-900 dark:text-zinc-100 mt-3 leading-relaxed">Ada estimasi <span className="font-bold text-amber-600">{monthly_search_volume.toLocaleString("id-ID")}</span> pencarian per bulan di <span className="font-bold text-zinc-900 dark:text-zinc-50">{city}</span> untuk kebutuhan <span className="font-bold text-zinc-900 dark:text-zinc-50">{category || "bisnis ini"}</span>.</p>
        </div>
      )}
    </section>
  );
}
