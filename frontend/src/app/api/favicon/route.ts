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

export async function GET(request: Request) {
  // Make sure CDN/browser bypass cache during deploys.
  const url = new URL(request.url);
  const cacheBust = url.searchParams.get("v") ?? "";
  const cacheControl = `public, max-age=300, s-maxage=300, must-revalidate${cacheBust ? `, no-cache` : ""}`;

  // 1. Brand Kit brandmark (admin upload) — server-side fetch, no full-page cache.
  try {
    const res = await fetch(`${API_BASE}/api/brand-kit/public`, {
      cache: "no-store",
      next: { revalidate: 300 },
    });
    if (res.ok) {
      const kit = await res.json();
      const asset = pickFaviconAsset(kit);
      if (asset?.url) {
        const file = await fetchAssetFile(`${API_BASE}${asset.url}`);
        if (file) {
          return new NextResponse(file.buf, {
            headers: { "Content-Type": file.contentType, "Cache-Control": cacheControl },
          });
        }
      }
    }
  } catch { /* fall through */ }

  // 2. Static shipped icon — lives in the same Vercel deployment, so use a
  //    path-relative URL (Next serves files from /public at the root).
  //    Direct fs read avoids the SSR self-fetch loop entirely.
  try {
    const fs = await import("node:fs/promises");
    const path = await import("node:path");
    const localPath = path.join(process.cwd(), "public", STATIC_FALLBACK_PNG.replace(/^\//, ""));
    const buf = await fs.readFile(localPath);
    return new NextResponse(buf, {
      headers: { "Content-Type": "image/png", "Cache-Control": cacheControl },
    });
  } catch { /* fall through */ }

  // 3. Inline SVG last-resort (yellow brandmark shape).
  return new NextResponse(fallbackSvg(), {
    headers: { "Content-Type": "image/svg+xml", "Cache-Control": cacheControl },
  });
}
