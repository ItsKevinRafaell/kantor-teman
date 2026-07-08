import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Final-static fallback — only reached when Brand Kit has no brandmark icon
// uploaded. Lives in `public/brand/derived/` and is built by
// scripts/build_logo_assets.py from the yellow brandmark master.
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

/**
 * Choose the favicon source. Order:
 *   1. Brand Kit admin-chosen default — but ONLY if it's brandmark-shaped
 *      (icon / brandmark), never a horizontal lockup.
 *   2. First brandmark-shaped asset uploaded (yellow preferred over white).
 *   3. Static `/brand/derived/icon-192.png` shipped with the build.
 *   4. Inline SVG.
 */
function pickFaviconAsset(
  kit: { assets?: Array<{ id: string; asset_type: string; file_url?: string | null }>; default_document_asset_id?: string | null },
): { url: string } | null {
  const assets = kit?.assets ?? [];
  const brandmarkSet = new Set(["brandmark_yellow", "brandmark_white", "brandmark"]);

  // 1. Admin-chosen default, ONLY if shape is icon.
  const defId = kit?.default_document_asset_id;
  if (defId) {
    const def = assets.find((a) => a.id === defId && a.file_url);
    if (def && brandmarkSet.has(def.asset_type)) return { url: def.file_url as string };
  }

  // 2. First brandmark-shaped asset (yellow > white > legacy).
  for (const pref of ["brandmark_yellow", "brandmark_white", "brandmark"]) {
    const m = assets.find((a) => a.asset_type === pref && a.file_url);
    if (m?.file_url) return { url: m.file_url };
  }

  return null;
}

export async function GET() {
  // 1. Brand Kit brandmark (admin upload)
  try {
    const res = await fetch(`${API_BASE}/api/brand-kit/public`, { next: { revalidate: 300 } });
    if (res.ok) {
      const kit = await res.json();
      const asset = pickFaviconAsset(kit);
      if (asset?.url) {
        const file = await fetchAssetFile(`${API_BASE}${asset.url}`);
        if (file) {
          return new NextResponse(file.buf, {
            headers: { "Content-Type": file.contentType, "Cache-Control": "public, max-age=300" },
          });
        }
      }
    }
  } catch { /* fall through */ }

  // 2. Static shipped icon (yellow brandmark @192) from /public/brand/derived/
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
