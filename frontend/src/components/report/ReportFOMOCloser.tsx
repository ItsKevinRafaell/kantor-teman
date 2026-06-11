"use client";
import { formatRupiah } from "../../utils/formatter";

interface ReportFOMOCloserProps {
  report: {
    category: string | null;
    competitor_count: number;
    base_price: number | null;
    total_price: number;
    discount_price: number | null;
    slug: string;
    nama_usaha: string | null;
    admin_wa?: string;
    admin_name?: string;
  };
  city: string;
  discountExpired: boolean;
  timeLeft: string;
  getProvinceForCity: (city: string) => string | null;
  apiBase: string;
}

export default function ReportFOMOCloser({ report, city, discountExpired, timeLeft, getProvinceForCity, apiBase }: ReportFOMOCloserProps) {
  const waLink = `https://wa.me/${report.admin_wa || ""}?text=${encodeURIComponent(`Halo ${report.admin_name || "Admin"}, saya tertarik konsultasi`)}`;
  const waLinkExpired = `https://wa.me/${report.admin_wa || ""}?text=${encodeURIComponent("Saya mau daftar waiting list")}`;

  return (
    <section className="bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-700 rounded-2xl p-6 shadow-sm space-y-5 print:hidden">
      <p className="text-sm text-zinc-900 dark:text-zinc-100 text-center leading-relaxed font-medium">
        Untuk menjaga kualitas pengerjaan dan hasil yang maksimal, kami membatasi kemitraan hanya untuk <span className="text-amber-600 font-black">1 bisnis</span> di sektor <span className="font-black text-zinc-900">{report.category || "bisnis ini"}</span> untuk wilayah <span className="font-black text-zinc-900">{city}</span> pada bulan ini.
      </p>
      {report.competitor_count > 0 && (
        <div className="rounded-xl bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-200 dark:border-amber-800 px-4 py-2.5 text-center">
          <p className="text-sm text-zinc-900 dark:text-zinc-100 font-medium">Database lead kami mencatat <span className="font-black text-amber-600">{report.competitor_count} bisnis sejenis</span> di {city} sebagai pembanding awal.</p>
        </div>
      )}
      {!discountExpired && (
        <div className="space-y-3 text-center">
          <div className="flex items-center justify-center gap-3">
            <span className="text-sm text-zinc-500 line-through font-medium">{formatRupiah(report.base_price || report.total_price)}</span>
            <span className="text-2xl font-black text-amber-600">{formatRupiah(report.discount_price || report.total_price)}</span>
          </div>
          <div className="bg-zinc-900 border-2 border-zinc-800 text-amber-500 font-mono text-2xl py-2 px-5 rounded-xl inline-block text-center shadow-md font-bold tracking-widest">{timeLeft}</div>
          <p className="text-[11px] text-zinc-700 dark:text-zinc-400 font-medium">Sisa waktu harga spesial</p>
        </div>
      )}
      <div className="rounded-xl bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-200 dark:border-amber-800 px-4 py-3">
        <p className="text-sm text-zinc-900 dark:text-zinc-100 leading-relaxed"><span className="font-bold text-zinc-900">Prioritas Layanan Wilayah {city || "Kota Anda"}:</span> Tim kami memastikan seluruh langkah optimasi disesuaikan dengan algoritma kompetisi pasar area <span className="font-bold text-zinc-900">{getProvinceForCity(city) || "Wilayah Kota Anda & Sekitarnya"}</span>.</p>
      </div>
      {!discountExpired ? (
        <a href={waLink} target="_blank" rel="noopener noreferrer" className="block w-full text-center py-4 px-6 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-black text-lg shadow-md border-b-4 border-amber-700 animate-pulse transition-all hover:scale-[1.02]">
          <span className="inline-flex items-center gap-2.5">
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
            Konsultasi Gratis via WhatsApp
          </span>
        </a>
      ) : (
        <a href={waLinkExpired} target="_blank" rel="noopener noreferrer" className="block w-full text-center py-4 px-6 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-white font-black text-lg border-b-4 border-zinc-900 shadow-md transition-all hover:scale-[1.02]">
          <span className="inline-flex items-center gap-2.5">Daftar Antrean Waiting List Bulan Depan</span>
        </a>
      )}
      <button onClick={() => {
        const shareText = `Saya baru baca laporan audit digital untuk ${report.nama_usaha || "bisnis ini"}. Cek insight dan proyeksinya di sini: kantorteman.com/report/${report.slug}`;
        if (navigator.share) navigator.share({ title: `Audit Digital - ${report.nama_usaha}`, text: shareText }).catch(() => {});
        else window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(shareText)}`, "_blank");
        fetch(`${apiBase}/api/proposals/public/report/${report.slug}/track-activity`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ activity_type: "SHARE_PARTNER_CLICKED" }) }).catch(() => {});
      }} className="block w-full text-center py-3 px-4 rounded-xl border-2 border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-200 hover:text-zinc-900 dark:hover:text-white font-bold text-sm transition-all">Bagikan Laporan Ini ke Rekan Bisnis</button>
    </section>
  );
}
