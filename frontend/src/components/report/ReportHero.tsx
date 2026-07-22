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
  rating?: number | null;
  reviews?: number | null;
  website?: string | null;
}

export function ReportHero({
  nama_usaha, category, city, monthly_search_volume,
  base_price, discount_price, is_discount_expired,
  rating, reviews, website,
}: Props) {
  return (
    <section className="relative overflow-hidden rounded-3xl border border-amber-200/80 bg-gradient-to-br from-amber-50 via-white to-orange-50 p-6 shadow-sm dark:border-amber-900/40 dark:from-amber-950/40 dark:via-zinc-900 dark:to-zinc-950 md:p-8">
      <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-amber-200/40 blur-3xl dark:bg-amber-700/20" />
      <div className="relative space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2 min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-700 dark:text-amber-300">
              Laporan Audit Digital · {new Date().toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })}
            </p>
            <h1 className="text-3xl font-black tracking-tight text-zinc-900 dark:text-white md:text-4xl">
              {nama_usaha || "Bisnis Anda"}
            </h1>
            <p className="text-sm font-medium text-zinc-600 dark:text-zinc-300">
              {category || "Layanan"} · {city || "Area Anda"}
            </p>
          </div>
          {!is_discount_expired && base_price && discount_price && base_price > 0 ? (
            <div className="rounded-2xl border border-amber-300 bg-white/80 px-4 py-3 text-right shadow-sm dark:border-amber-800 dark:bg-zinc-900/80">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-zinc-500">Estimasi paket</p>
              <p className="text-xs text-zinc-400 line-through">{formatRupiah(base_price)}</p>
              <p className="text-2xl font-black text-amber-600">{formatRupiah(discount_price)}</p>
              <p className="text-[10px] font-bold text-amber-700">
                Hemat {Math.max(0, Math.round((1 - discount_price / base_price) * 100))}% · 24 jam
              </p>
            </div>
          ) : null}
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="rounded-xl border border-zinc-200/80 bg-white/70 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900/60">
            <p className="text-[10px] font-bold uppercase tracking-wide text-zinc-500">Rating Maps</p>
            <p className="text-lg font-black text-zinc-900 dark:text-white">
              {rating && rating > 0 ? `${Number(rating).toFixed(1)}★` : "—"}
            </p>
          </div>
          <div className="rounded-xl border border-zinc-200/80 bg-white/70 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900/60">
            <p className="text-[10px] font-bold uppercase tracking-wide text-zinc-500">Ulasan</p>
            <p className="text-lg font-black text-zinc-900 dark:text-white">
              {reviews && reviews > 0 ? Number(reviews).toLocaleString("id-ID") : "—"}
            </p>
          </div>
          <div className="rounded-xl border border-zinc-200/80 bg-white/70 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900/60">
            <p className="text-[10px] font-bold uppercase tracking-wide text-zinc-500">Website</p>
            <p className="truncate text-sm font-bold text-zinc-900 dark:text-white">
              {website ? "Ada" : "Belum terdeteksi"}
            </p>
          </div>
          <div className="rounded-xl border border-zinc-200/80 bg-white/70 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900/60">
            <p className="text-[10px] font-bold uppercase tracking-wide text-zinc-500">Est. pencarian/bln</p>
            <p className="text-lg font-black text-amber-600">
              {monthly_search_volume > 0 ? monthly_search_volume.toLocaleString("id-ID") : "—"}
            </p>
          </div>
        </div>

        {monthly_search_volume > 0 ? (
          <p className="text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
            <span className="font-bold text-amber-600">{monthly_search_volume.toLocaleString("id-ID")}</span>{" "}
            <span className="font-semibold">estimasi internal</span> pencarian/bulan di{" "}
            <span className="font-semibold">{city}</span> terkait{" "}
            <span className="font-semibold">{category || "kategori ini"}</span>
            {" "}— bukan data live Google Ads/Keyword Planner. Dipakai sebagai sinyal pasar, bukan angka resmi.
          </p>
        ) : (
          <p className="text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
            Estimasi volume pencarian belum tersedia untuk kombinasi kategori/kota ini. Fokus audit: kelengkapan profil digital & jalur kontak.
          </p>
        )}
        <p className="text-[11px] leading-relaxed text-zinc-500 dark:text-zinc-400">
          Rating, ulasan, website, dan link sosmed di laporan ini mengikuti data profil lead (scrape/manual). Angka estimasi dilabeli terpisah.
        </p>
      </div>
    </section>
  );
}
