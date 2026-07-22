"use client";

export interface PresenceSignals {
  hasWebsite?: boolean;
  hasGbp?: boolean; // original_url / Maps link
  hasInstagram?: boolean;
  hasFacebook?: boolean;
  hasTiktok?: boolean;
  googleRating?: number | null;
  reviewCount?: number | null;
  websiteUrl?: string | null;
  gbpUrl?: string | null;
  instagramUrl?: string | null;
  primaryChannel?: "website" | "gbp" | "instagram" | "facebook" | "tiktok" | "none";
}

interface Props {
  nama_usaha: string | null;
  category: string | null;
  city: string;
  slug: string;
  base_price?: number | null;
  discount_price?: number | null;
  hasDigitalAnalysis: boolean;
  presence?: PresenceSignals;
}

type Row = {
  label: string;
  before: string;
  beforeNote: string;
  after: string;
  tone: "critical" | "warn" | "ok" | "info";
};

function buildRows(
  city: string,
  category: string | null,
  presence: PresenceSignals,
  hasDigitalAnalysis: boolean,
): Row[] {
  const area = city || "area Anda";
  const cat = category || "layanan Anda";
  const p = presence || {};
  const rating = p.googleRating;
  const reviews = p.reviewCount;
  const rows: Row[] = [];

  // 1) Presence / channel
  if (p.hasWebsite) {
    rows.push({
      label: "Website",
      before: "Ada, perlu dicek",
      beforeNote: p.websiteUrl
        ? `Terdeteksi: ${p.websiteUrl.replace(/^https?:\/\//, "").slice(0, 42)}`
        : "Struktur, kecepatan, dan CTA perlu divalidasi",
      after: "Halaman penawaran + CTA WA jelas",
      tone: "warn",
    });
  } else if (p.hasGbp) {
    rows.push({
      label: "Google Business",
      before: "GBP ada, website belum",
      beforeNote: "Profil Maps jadi pintu utama — lengkapi foto, jam, layanan, dan tombol WA",
      after: "GBP lengkap + landing ringkas",
      tone: "warn",
    });
  } else if (p.hasInstagram || p.hasFacebook || p.hasTiktok) {
    const ch = p.hasInstagram ? "Instagram" : p.hasFacebook ? "Facebook" : "TikTok";
    rows.push({
      label: "Kanal utama",
      before: `${ch} aktif, Maps/web lemah`,
      beforeNote: "Sosmed bagus untuk awareness, tapi pencarian lokal butuh jejak di Google/Maps",
      after: "Sosmed + jejak lokal terhubung",
      tone: "warn",
    });
  } else {
    rows.push({
      label: "Jejak digital",
      before: "Belum terdeteksi",
      beforeNote: "Belum ada website / GBP / sosmed di data kami — calon pelanggan sulit memverifikasi bisnis",
      after: "Profil inti online siap dicek",
      tone: "critical",
    });
  }

  // 2) Maps / social proof
  if (rating != null && rating > 0) {
    const ok = rating >= 4.3;
    rows.push({
      label: "Google Maps",
      before: ok ? `${rating.toFixed(1)}★ — jaga momentum` : `${rating.toFixed(1)}★ — perlu ditingkatkan`,
      beforeNote: reviews
        ? `${reviews.toLocaleString("id-ID")} ulasan · bandingkan posisi di ${area}`
        : `Cek kelengkapan profil & respons review di ${area}`,
      after: ok ? "Pertahankan peringkat & review" : "Target 4.5★+ & profil lengkap",
      tone: ok ? "ok" : "warn",
    });
  } else if (p.hasGbp) {
    rows.push({
      label: "Google Maps",
      before: "Link GBP ada, rating kosong",
      beforeNote: "Isi kategori, area layanan, dan minta review awal dari klien puas",
      after: "Rating & foto terisi rapi",
      tone: "warn",
    });
  } else {
    rows.push({
      label: "Google Maps",
      before: hasDigitalAnalysis ? `Perlu dicek di ${area}` : "Belum ada GBP",
      beforeNote: p.hasInstagram
        ? "Tanpa Maps, orang yang search di Google tidak menemukan Anda meski IG ramai"
        : `Posisi lokal di ${area} belum bisa diverifikasi dari data`,
      after: p.hasInstagram ? "GBP + IG saling taut" : `Mudah ditemukan di ${area}`,
      tone: "critical",
    });
  }

  // 3) Discoverability
  rows.push({
    label: "Pencarian lokal",
    before: p.hasWebsite || p.hasGbp ? "Dasar ada, belum optimal" : "Belum punya fondasi",
    beforeNote: `Keyword «${cat}» + ${area} perlu halaman/profil yang rapi`,
    after: "Konten & profil selaras keyword",
    tone: p.hasWebsite || p.hasGbp ? "warn" : "critical",
  });

  // 4) Conversion path
  if (p.hasWebsite) {
    rows.push({
      label: "Konversi",
      before: "CTA perlu diperjelas",
      beforeNote: "Pastikan tombol WhatsApp / form muncul di atas lipatan & di halaman layanan",
      after: "1 klik ke WhatsApp",
      tone: "warn",
    });
  } else if (p.hasGbp) {
    rows.push({
      label: "Konversi",
      before: "Tombol chat/telepon Maps",
      beforeNote: "Aktifkan messaging, jam buka akurat, dan tautan WA di deskripsi",
      after: "Chat Maps → closing rapi",
      tone: "info",
    });
  } else if (p.hasInstagram || p.hasFacebook || p.hasTiktok) {
    rows.push({
      label: "Konversi",
      before: "Bergantung DM sosmed",
      beforeNote: "Tambah link-in-bio / landing ringkas supaya prospek tidak hilang di DM",
      after: "DM + link penawaran jelas",
      tone: "warn",
    });
  } else {
    rows.push({
      label: "Konversi",
      before: "Jalur kontak belum jelas",
      beforeNote: "Tanpa web/GBP/sosmed, prospek tidak tahu cara menghubungi Anda",
      after: "WhatsApp + profil terhubung",
      tone: "critical",
    });
  }

  return rows;
}

function toneDot(tone: Row["tone"]) {
  if (tone === "critical") return "bg-red-100 border-red-300 text-red-600 dark:bg-red-950/40 dark:border-red-800 dark:text-red-400";
  if (tone === "warn") return "bg-amber-100 border-amber-300 text-amber-700 dark:bg-amber-950/40 dark:border-amber-800 dark:text-amber-300";
  if (tone === "ok") return "bg-emerald-100 border-emerald-300 text-emerald-700 dark:bg-emerald-950/40 dark:border-emerald-800 dark:text-emerald-300";
  return "bg-zinc-100 border-zinc-300 text-zinc-600 dark:bg-zinc-800 dark:border-zinc-600 dark:text-zinc-300";
}

export function BeforeAfterComparison({
  nama_usaha,
  category,
  city,
  slug,
  hasDigitalAnalysis,
  presence = {},
}: Props) {
  const rows = buildRows(city, category, presence, hasDigitalAnalysis);
  const primary =
    presence.primaryChannel === "instagram"
      ? "Instagram"
      : presence.primaryChannel === "gbp"
        ? "Google Maps"
        : presence.primaryChannel === "website"
          ? "Website"
          : presence.primaryChannel === "facebook"
            ? "Facebook"
            : presence.primaryChannel === "tiktok"
              ? "TikTok"
              : "Profil digital";

  const afterPreviewTitle =
    presence.primaryChannel === "instagram"
      ? `${nama_usaha || "Bisnis Anda"} · Instagram + jejak lokal`
      : presence.primaryChannel === "gbp"
        ? `${nama_usaha || "Bisnis Anda"} · Google Maps unggulan`
        : `${nama_usaha || "Bisnis Anda"} — Solusi terpercaya di ${city || "area Anda"}`;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2 px-1">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-zinc-500">Perbandingan</p>
          <h2 className="text-lg font-black text-zinc-900 dark:text-white">Kondisi sekarang → target perbaikan</h2>
        </div>
        <span className="rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-[10px] font-semibold text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
          Kanal utama: {primary}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {/* Before */}
        <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-5 dark:border-zinc-700 dark:bg-zinc-900/60">
          <div className="mb-4 flex items-center justify-between gap-2">
            <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Kondisi saat ini</p>
            <span className="rounded-full bg-zinc-200 px-2 py-0.5 text-[10px] font-bold text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
              {hasDigitalAnalysis ? "Temuan audit" : "Data awal"}
            </span>
          </div>
          <h3 className="mb-4 text-base font-bold text-zinc-900 dark:text-zinc-50">{nama_usaha || "Bisnis Anda"}</h3>
          <div className="space-y-3">
            {rows.map((row) => (
              <div key={row.label} className="flex gap-3">
                <div className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[10px] font-black ${toneDot(row.tone)}`}>
                  !
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                    {row.label}
                    <span className="font-medium text-zinc-500"> · {row.before}</span>
                  </p>
                  <p className="mt-0.5 text-[12px] leading-relaxed text-zinc-500 dark:text-zinc-400">{row.beforeNote}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* After */}
        <div className="rounded-2xl border border-amber-200 bg-gradient-to-b from-amber-50/80 to-white p-5 shadow-sm dark:border-amber-900/50 dark:from-amber-950/30 dark:to-zinc-900">
          <div className="mb-4 flex items-center justify-between gap-2">
            <p className="text-[10px] font-bold uppercase tracking-widest text-amber-700 dark:text-amber-300">Proyeksi perbaikan</p>
            <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-800 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-200">
              Target 30–90 hari
            </span>
          </div>
          <h3 className="mb-4 text-base font-bold text-zinc-900 dark:text-white">Bersama Kantor Teman</h3>

          <div className="mb-4 rounded-xl border border-zinc-200 bg-white p-3.5 dark:border-zinc-700 dark:bg-zinc-950/50">
            <div className="mb-1.5 flex items-center gap-1.5 text-[10px] text-zinc-500">
              <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-[9px] font-black text-white">✓</span>
              <span className="truncate">
                {presence.primaryChannel === "instagram"
                  ? "instagram.com · profil bisnis"
                  : presence.primaryChannel === "gbp"
                    ? "Google Maps · Business Profile"
                    : `hasil pencarian · ${slug}`}
              </span>
            </div>
            <p className="text-sm font-bold leading-snug text-blue-700 dark:text-blue-400">{afterPreviewTitle}</p>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <span className="text-xs text-amber-500">★★★★★</span>
              <span className="text-[10px] text-zinc-500">
                {presence.googleRating && presence.googleRating > 0
                  ? `${presence.googleRating.toFixed(1)} · ditingkatkan`
                  : "Target review positif"}
              </span>
            </div>
            <p className="mt-1.5 text-[11px] leading-relaxed text-zinc-600 dark:text-zinc-400">
              {category || "Layanan"} yang mudah dicek & dihubungi di {city || "area Anda"}.
            </p>
          </div>

          <div className="space-y-2.5">
            {rows.map((row) => (
              <div key={`after-${row.label}`} className="flex items-start gap-2">
                <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500 text-[10px] font-black text-white">
                  ✓
                </span>
                <p className="text-sm leading-snug text-zinc-800 dark:text-zinc-100">
                  <span className="font-semibold">{row.label}:</span>{" "}
                  <span className="font-bold text-amber-700 dark:text-amber-300">{row.after}</span>
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
