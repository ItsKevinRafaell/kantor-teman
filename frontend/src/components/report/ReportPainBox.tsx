"use client";

interface ReportPainBoxProps {
  painPoints: string[];
  monthly_search_volume: number;
  city: string;
  category: string | null;
}

export default function ReportPainBox({ painPoints, monthly_search_volume, city, category }: ReportPainBoxProps) {
  const defaultPainPoints = [
    `Unoptimized Local SEO: Bisnis Anda tenggelam di Google Maps, kalah saing dari kompetitor di ${city}.`,
    "Kecepatan Web Lambat: Bikin sekitar 40% calon pelanggan Anda kabur sebelum halaman terbuka.",
    "Tidak Ada Sistem Konversi: Pengunjung datang tapi tidak ada mekanisme untuk mengubah mereka jadi pelanggan.",
  ];

  return (
    <section className="bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-200 dark:border-amber-800 rounded-2xl p-6 shadow-sm">
      <h2 className="text-sm font-bold uppercase tracking-widest text-amber-700 dark:text-amber-400 mb-4">Masalah Kritis yang Ditemukan</h2>
      <div className="space-y-4">
        {(painPoints.length > 0 ? painPoints : defaultPainPoints).map((point, i) => (
          <div key={i} className="flex items-start gap-3">
            <div className="w-6 h-6 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold">{i + 1}</div>
            <p className="text-sm text-zinc-900 leading-relaxed font-medium">{point}</p>
          </div>
        ))}
      </div>
      {monthly_search_volume > 0 && (
        <div className="mt-6 pt-5 border-t-2 border-amber-200">
          <p className="text-[10px] uppercase tracking-widest text-zinc-700 font-bold mb-3">Fakta pasar Digital — {city}</p>
          <div className="flex items-end gap-3 mb-3">
            <span className="text-4xl md:text-5xl font-black text-amber-600 tracking-tight">{monthly_search_volume.toLocaleString("id-ID")}</span>
            <span className="text-sm text-zinc-700 font-medium pb-1">pencarian/bulan</span>
          </div>
          <div className="w-full h-2 bg-amber-200 rounded-full overflow-hidden"><div className="bg-amber-500 h-full rounded-full" style={{ width: "75%" }}></div></div>
          <p className="text-sm text-zinc-900 mt-3 leading-relaxed">Ada sekitar <span className="font-bold text-amber-600">{monthly_search_volume.toLocaleString("id-ID")}</span> orang di <span className="font-bold text-zinc-900">{city}</span> yang aktif mencari solusi <span className="font-bold text-zinc-900">{category}</span> setiap bulannya di Google.</p>
        </div>
      )}
    </section>
  );
}