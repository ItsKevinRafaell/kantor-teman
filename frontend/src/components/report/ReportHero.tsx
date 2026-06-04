"use client";

import { formatRupiah } from "../../utils/formatter";

interface Props {
  nama_usaha: string | null;
  category: string | null;
  city: string;
  monthly_search_volume: number;
  base_price: number | null;
  discount_price: number | null;
  discount_expires_at: string | null;
  is_discount_expired: boolean;
  active_price: number;
}

export function ReportHero({ nama_usaha, category, city, monthly_search_volume, base_price, discount_price, is_discount_expired, active_price }: Props) {
  return (
    <section className="bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-200 dark:border-amber-800 rounded-2xl p-6 shadow-sm hover:border-amber-500 transition-all duration-300 ease-in-out">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="space-y-1">
          <p className="text-[10px] uppercase tracking-widest text-zinc-700 dark:text-zinc-300 font-bold">
            Laporan Audit Digital — {new Date().toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })}
          </p>
          <h1 className="text-2xl md:text-3xl font-black text-zinc-900 dark:text-white leading-tight">{nama_usaha || "Bisnis Anda"}</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 font-medium">{category || "Kategori"} — {city}</p>
        </div>
        {!is_discount_expired && base_price && discount_price && (
          <div className="text-right shrink-0">
            <p className="text-[10px] text-zinc-500 line-through">{formatRupiah(base_price)}</p>
            <p className="text-2xl font-black text-amber-600">{formatRupiah(discount_price)}</p>
            <p className="text-[10px] text-amber-600 font-bold">HEMAT {Math.round((1 - discount_price / base_price) * 100)}%</p>
          </div>
        )}
      </div>

      {monthly_search_volume > 0 && (
        <div className="mt-6 pt-5 border-t-2 border-amber-200">
          <p className="text-[10px] uppercase tracking-widest text-zinc-700 font-bold mb-3">Fakta Pasar Digital — {city}</p>
          <div className="flex items-end gap-3 mb-3">
            <span className="text-4xl md:text-5xl font-black text-amber-600 tracking-tight">
              {monthly_search_volume.toLocaleString("id-ID")}
            </span>
            <span className="text-sm text-zinc-700 font-medium pb-1">pencarian/bulan</span>
          </div>
          <div className="w-full h-2 bg-amber-200 rounded-full overflow-hidden">
            <div className="bg-amber-500 h-full rounded-full" style={{ width: "75%" }}></div>
          </div>
          <p className="text-sm text-zinc-900 mt-3 leading-relaxed">
            Ada sekitar <span className="font-bold text-amber-600">{monthly_search_volume.toLocaleString("id-ID")}</span> orang di <span className="font-bold text-zinc-900">{city}</span> yang aktif mencari solusi <span className="font-bold text-zinc-900">{category}</span> setiap bulannya di Google. Tanpa optimasi yang tepat, potensi pasar ini sepenuhnya mengalir ke kompetitor Anda.
          </p>
        </div>
      )}
    </section>
  );
}