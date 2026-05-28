import type { MetadataRoute } from "next";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const FALLBACK_ICONS: MetadataRoute.Manifest["icons"] = [
  { src: "/icons/icon-72x72.png",   sizes: "72x72",   type: "image/png" },
  { src: "/icons/icon-96x96.png",   sizes: "96x96",   type: "image/png" },
  { src: "/icons/icon-128x128.png", sizes: "128x128", type: "image/png" },
  { src: "/icons/icon-144x144.png", sizes: "144x144", type: "image/png" },
  { src: "/icons/icon-152x152.png", sizes: "152x152", type: "image/png" },
  { src: "/icons/icon-192x192.png", sizes: "192x192", type: "image/png", purpose: "any" },
  { src: "/icons/icon-384x384.png", sizes: "384x384", type: "image/png" },
  { src: "/icons/icon-512x512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
];

export default async function manifest(): Promise<MetadataRoute.Manifest> {
  let icons = FALLBACK_ICONS;

  try {
    const res = await fetch(`${API_BASE}/api/brand-kit/public`, { next: { revalidate: 3600 } });
    if (res.ok) {
      const data = await res.json();
      const brandmark = data?.assets?.find((a: { asset_type: string }) => a.asset_type === "brandmark");
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
    name: "Kantor Teman",
    short_name: "KantorTeman",
    description: "CRM internal untuk prospek bisnis lokal",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#fcfaf7",
    theme_color: "#f5a700",
    orientation: "portrait",
    icons,
  };
}
