import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// New derived asset lives in the frontend's /public (master PNGs were copied
// from SVG via scripts/build_logo_assets.py).
const STATIC_FALLBACK_PNG = "/brand/derived/icon-192.png";

export const dynamic = "force-dynamic";
export const revalidate = 300;

function fallbackSvg(): string {
  // Last-resort inline SVG using the brand yellow + brandmark shape.
  return `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" fill="#f5a700"/>
  <path d="M10 39.5 32 27.5l22 12-22-7.2-22 7.2Z" fill="#fff"/>
  <rect x="13" y="27" width="5" height="13" fill="#fff"/>
  <path d="M39 22c5 1 9 5 10 10M39 27c3 1 5 3 6 6" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/>
</svg>`;
}

async function fetchAssetFile(absoluteUrl: string): Promise<{ buf: ArrayBuffer; contentType: string } | null> {
  try {
    const fileRes = await fetch(absoluteUrl);
    if (!fileRes.ok) return null;
    return {
      buf: await fileRes.arrayBuffer(),
      contentType: fileRes.headers.get("content-type") || "image/png",
    };
  } catch {
    return null;
  }
}

function preferredBrandmarkAssetId(kit: { assets?: Array<{ id: string; asset_type: string; file_url?: string | null }>; default_document_asset_id?: string | null }) {
  const assets = kit?.assets ?? [];
  // Honour admin-chosen default only if it points to a brandmark/icon
  // (acceptable: any of the 6 logo slots; fall back to brandmark-yellow).
  const defId = kit?.default_document_asset_id;
  const def = defId ? assets.find(a => a.id === defId && a.file_url) : null;
  if (def?.file_url) return def;
  for (const pref of ["brandmark_yellow", "brandmark_white", "brandmark", "logo_primary_yellow", "logo_primary"]) {
    const m = assets.find(a => a.asset_type === pref && a.file_url);
    if (m) return m;
  }
  return null;
}

export async function GET() {
  // 1. Try brand kit public endpoint
  try {
    const res = await fetch(`${API_BASE}/api/brand-kit/public`, { next: { revalidate: 300 } });
    if (res.ok) {
      const kit = await res.json();
      const asset = preferredBrandmarkAssetId(kit);
      if (asset?.file_url) {
        const file = await fetchAssetFile(`${API_BASE}${asset.file_url}`);
        if (file) {
          return new NextResponse(file.buf, {
            headers: { "Content-Type": file.contentType, "Cache-Control": "public, max-age=300" },
          });
        }
      }
    }
  } catch { /* fall through */ }

  // 2. Try the new derived asset shipped with the build
  const localBase = (process.env.NEXT_PUBLIC_FRONTEND_URL ?? "http://localhost:3000").replace(/\/$/, "");
  const local = await fetchAssetFile(`${localBase}${STATIC_FALLBACK_PNG}`);
  if (local) {
    return new NextResponse(local.buf, {
      headers: { "Content-Type": local.contentType, "Cache-Control": "public, max-age=300" },
    });
  }

  // 3. Inline SVG last-resort
  return new NextResponse(fallbackSvg(), {
    headers: { "Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=300" },
  });
}
