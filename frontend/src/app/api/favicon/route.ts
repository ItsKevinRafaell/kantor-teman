import { NextResponse } from "next/server";
import path from "node:path";
import fs from "node:fs/promises";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
// Built by scripts/build_logo_assets.py from the yellow brandmark master.
// Used as the *static* fallback when Brand Kit has no PNG brandmark uploaded.
const STATIC_FALLBACK_PNG = "brand/derived/icon-192.png";

export const dynamic = "force-dynamic";
export const revalidate = 0;

function fallbackSvg(): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" fill="#f5a700"/>
  <path d="M10 39.5 32 27.5l22 12-22-7.2-22 7.2Z" fill="#fff"/>
  <rect x="13" y="27" width="5" height="13" fill="#fff"/>
  <path d="M39 22c5 1 9 5 10 10M39 27c3 1 5 3 6 6" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/>
</svg>`;
}

async function fetchAssetFile(absoluteUrl: string): Promise<{ buf: ArrayBuffer; contentType: string } | null> {
  try {
    const fileRes = await fetch(absoluteUrl, { cache: "no-store" });
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
 * Pick a favicon-grade asset: brandmark-shaped only AND png/ico only.
 * Falls back through yellow → white → legacy. Admin-chosen default
 * accepted only when its shape is brandmark AND filetype is image/png
 * or image/x-icon — SVGs are rejected because browsers can render them
 * inconsistently at favicon sizes.
 */
function pickFaviconAsset(
  kit: {
    assets?: Array<{ id: string; asset_type: string; file_url?: string | null }>;
    default_document_asset_id?: string | null;
  },
): { url: string } | null {
  const assets = kit?.assets ?? [];
  const iconSet = new Set(["brandmark_yellow", "brandmark_white", "brandmark"]);
  const isRaster = (fileUrl?: string | null) =>
    !!fileUrl && /\.(png|jpe?g|webp|ico)$/i.test(fileUrl);

  const defId = kit?.default_document_asset_id;
  if (defId) {
    const def = assets.find((a) => a.id === defId && a.file_url && isRaster(a.file_url));
    if (def && iconSet.has(def.asset_type)) return { url: def.file_url as string };
  }

  for (const pref of ["brandmark_yellow", "brandmark_white", "brandmark"]) {
    const m = assets.find((a) => a.asset_type === pref && a.file_url && isRaster(a.file_url));
    if (m?.file_url) return { url: m.file_url };
  }
  return null;
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const cc = "public, max-age=300, s-maxage=300, must-revalidate";

  // 1. Brand Kit brandmark (admin upload). Skipped silently if fetch fails.
  try {
    const res = await fetch(`${API_BASE}/api/brand-kit/public`, { cache: "no-store" });
    if (res.ok) {
      const kit = await res.json();
      const asset = pickFaviconAsset(kit);
      if (asset?.url) {
        const file = await fetchAssetFile(`${API_BASE}${asset.url}`);
        if (file) {
          return new NextResponse(file.buf, {
            headers: { "Content-Type": file.contentType, "Cache-Control": cc },
          });
        }
      }
    }
  } catch {
    /* fall through */
  }

  // 2. Static shipped icon, read directly from the deployment bundle.
  try {
    const localPath = path.join(process.cwd(), "public", STATIC_FALLBACK_PNG);
    const buf = await fs.readFile(localPath);
    return new NextResponse(buf, {
      headers: { "Content-Type": "image/png", "Cache-Control": cc },
    });
  } catch {
    /* fall through */
  }

  // 3. Inline SVG (last resort — should rarely fire).
  return new NextResponse(fallbackSvg(), {
    headers: { "Content-Type": "image/svg+xml", "Cache-Control": cc },
  });
}
