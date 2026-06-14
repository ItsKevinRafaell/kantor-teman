import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const STATIC_BRANDMARK = "/uploads/brand/logo-brandmark.png";

export const dynamic = "force-dynamic";
export const revalidate = 300;

function fallbackSvg(): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" fill="#f5a700"/>
  <path d="M10 39.5 32 27.5l22 12-22-7.2-22 7.2Z" fill="#fff"/>
  <rect x="13" y="27" width="5" height="13" fill="#fff"/>
  <path d="M39 22c5 1 9 5 10 10M39 27c3 1 5 3 6 6" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/>
</svg>`;
}

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/brand-kit/public`, { next: { revalidate: 300 } });
    if (res.ok) {
      const kit = await res.json();
      const brandmark = kit.assets?.find((a: { asset_type: string; file_url: string | null }) => a.asset_type === "brandmark" && a.file_url);
      if (brandmark?.file_url) {
        const fileRes = await fetch(`${API_BASE}${brandmark.file_url}`);
        if (fileRes.ok) {
          const buf = await fileRes.arrayBuffer();
          const ct = fileRes.headers.get("content-type") || "image/png";
          return new NextResponse(buf, {
            headers: { "Content-Type": ct, "Cache-Control": "public, max-age=300" },
          });
        }
      }
    }
  } catch {}

  try {
    const fileRes = await fetch(`${API_BASE}${STATIC_BRANDMARK}`);
    if (fileRes.ok) {
      const buf = await fileRes.arrayBuffer();
      const ct = fileRes.headers.get("content-type") || "image/png";
      return new NextResponse(buf, {
        headers: { "Content-Type": ct, "Cache-Control": "public, max-age=300" },
      });
    }
  } catch {}

  return new NextResponse(fallbackSvg(), {
    headers: { "Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=300" },
  });
}
