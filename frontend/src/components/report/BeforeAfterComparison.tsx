"use client";

interface Props {
  nama_usaha: string | null;
  category: string | null;
  city: string;
  slug: string;
  base_price: number | null;
  discount_price: number | null;
  hasDigitalAnalysis: boolean;
}

export function BeforeAfterComparison({ nama_usaha, category, city, slug, base_price, discount_price, hasDigitalAnalysis }: Props) {
  const beforeItems = hasDigitalAnalysis
    ? [
        ["Skor Kecepatan Web", "Perlu optimasi", "Pengalaman pengunjung perlu dibuat lebih cepat"],
        ["Google Maps", `Perlu dicek di ${city}`, "Posisi lokal harus dibandingkan dengan kompetitor"],
        ["SEO Lokal", "Belum optimal", "Kata kunci dan halaman layanan perlu dirapikan"],
        ["Konversi", "Perlu diperkuat", "Alur WhatsApp/CTA harus lebih jelas"],
      ]
    : [
        ["Website", "Perlu audit teknis", "Kecepatan, struktur halaman, dan CTA perlu divalidasi"],
        ["Google Maps", "Perlu validasi posisi", `Cek apakah profil mudah ditemukan untuk pencarian di ${city}`],
        ["SEO Lokal", "Perlu baseline", "Keyword, konten, dan halaman layanan perlu dipetakan"],
        ["Konversi", "Perlu dicek", "Pastikan pengunjung punya jalur kontak yang mudah"],
      ];

  return (
    <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Before */}
      <div className="bg-zinc-100 dark:bg-zinc-800 border-2 border-zinc-200 dark:border-zinc-700 rounded-2xl p-5 space-y-4 transition-all duration-300 ease-in-out">
        <div className="flex items-center justify-between">
          <p className="text-[10px] uppercase tracking-widest text-zinc-600 dark:text-zinc-400 font-bold">Kondisi Saat Ini</p>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-zinc-200 dark:bg-zinc-700 border-2 border-zinc-300 dark:border-zinc-600 text-[10px] font-bold text-zinc-600 dark:text-zinc-300">
            {hasDigitalAnalysis ? "Temuan Audit" : "Perlu Validasi"}
          </span>
        </div>
        <h3 className="text-sm font-bold text-zinc-800 dark:text-zinc-100">{nama_usaha || "Bisnis Anda"}</h3>
        <div className="space-y-3">
          {beforeItems.map(([label, value, note]) => (
            <div key={label} className="flex items-start gap-2">
              <div className="w-5 h-5 rounded-full bg-zinc-200 dark:bg-zinc-700 border-2 border-zinc-300 dark:border-zinc-600 flex items-center justify-center shrink-0 mt-0.5"><span className="text-zinc-600 dark:text-zinc-300 text-[9px] font-bold">!</span></div>
              <div>
                <p className="text-sm text-zinc-600 dark:text-zinc-300">{label}: <span className="text-zinc-500 dark:text-zinc-400 font-medium">{value}</span></p>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400">{note}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* After */}
      <div className="bg-white dark:bg-zinc-900 border-2 border-amber-200 dark:border-amber-800 rounded-2xl p-5 space-y-4 transition-all duration-300 ease-in-out hover:border-amber-500 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-[10px] uppercase tracking-widest text-zinc-600 dark:text-zinc-400 font-bold">Proyeksi Perbaikan</p>
          <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-700 border-2 border-amber-300 text-xs px-2.5 py-1 rounded-full font-bold">Peringkat #1</span>
        </div>
        <h3 className="text-sm font-bold text-zinc-900 dark:text-white">Bersama Kantor Teman</h3>

        {/* Mockup Google Search */}
        <div className="rounded-xl border-2 border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 p-3.5 space-y-1.5">
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded-full bg-amber-500 flex items-center justify-center">
              <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
            <span className="text-[10px] text-zinc-600 dark:text-zinc-300">kantorteman.com › {slug}</span>
          </div>
          <p className="text-sm font-bold text-blue-700">{nama_usaha} — Solusi Terpercaya di {city}</p>
          <div className="flex items-center gap-1">
            <span className="text-amber-500 text-xs flex items-center gap-0.5">
              {Array(5).fill(null).map((_, i) => (
                <svg key={i} width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
              ))}
            </span>
            <span className="text-[10px] text-zinc-600">5.0 · Terverifikasi</span>
          </div>
          <p className="text-[11px] text-zinc-600 dark:text-zinc-300">Layanan profesional {category || "bisnis"} terbaik di {city}.</p>
        </div>

        <div className="space-y-2.5">
          {[
            { label: "Kecepatan Web", value: "98/100" },
            { label: "Google Maps", value: `Peringkat 1 di ${city}` },
            { label: "SEO Lokal", value: "Fully Optimized" },
            { label: "Konversi", value: "8-12%" },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-amber-600 text-sm font-bold"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="inline"><polyline points="20 6 9 17 4 12"/></svg></span>
              <p className="text-sm text-zinc-900 dark:text-zinc-100">{item.label}: <span className="text-amber-600 font-bold">{item.value}</span></p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
