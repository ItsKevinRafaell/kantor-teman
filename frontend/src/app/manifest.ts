import type { MetadataRoute } from "next";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Built by scripts/build_logo_assets.py from the 6 SVG masters in /home/kevin/Logo.
const STATIC_ICONS: MetadataRoute.Manifest["icons"] = [
  { src: "/brand/derived/icon-72.png",  sizes: "72x72",  type: "image/png" },
  { src: "/brand/derived/icon-96.png",  sizes: "96x96",  type: "image/png" },
  { src: "/brand/derived/icon-128.png", sizes: "128x128", type: "image/png" },
  { src: "/brand/derived/icon-144.png", sizes: "144x144", type: "image/png" },
  { src: "/brand/derived/icon-152.png", sizes: "152x152", type: "image/png" },
  { src: "/brand/derived/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
  { src: "/brand/derived/icon-384.png", sizes: "384x384", type: "image/png" },
  { src: "/brand/derived/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
];

export default async function manifest(): Promise<MetadataRoute.Manifest> {
  // Manifest icons prefer a brandmark icon from Brand Kit. The 6-slot schema
  // exposes brandmark_yellow / brandmark_white; legacy "brandmark" kept for back-compat.
  let icons = STATIC_ICONS;

  try {
    const res = await fetch(`${API_BASE}/api/brand-kit/public`, { next: { revalidate: 3600 } });
    if (res.ok) {
      const data = await res.json();
      const def = data?.default_document_asset_id
        ? (data.assets as Array<{ id: string; asset_type: string; file_url?: string | null }>)
            .find((a) => a.id === data.default_document_asset_id)
        : undefined;
      const brandmark =
        def?.file_url ? def
        : (data?.assets as Array<{ asset_type: string; file_url?: string | null }>)
            ?.find((a) =>
              ["brandmark_yellow", "brandmark_white", "brandmark"].includes(a.asset_type) && a.file_url,
            );
      if (brandmark?.file_url) {
        const url = `${API_BASE}${brandmark.file_url}`;
        icons = [
          { src: url, sizes: "192x192", type: "image/png", purpose: "any" },
          { src: url, sizes: "512x512", type: "image/png", purpose: "maskable" },
        ];
      }
    }
  } catch { /* fallback to static icons */ }

  return {
    name: "Teman UMKM Kita — Kantor Teman",
    short_name: "KantorTeman",
    description: "ERP internal untuk agensi digital",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#fcfaf7",
    theme_color: "#f5a700",
    orientation: "portrait",
    icons,
  };
}
