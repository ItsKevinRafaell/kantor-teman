import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const dynamic = "force-dynamic";
export const revalidate = 300;

function fallbackSvg(): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#f5a700"/>
  <text x="32" y="42" text-anchor="middle" font-family="system-ui,sans-serif" font-size="26" font-weight="900" fill="#242423">TUK</text>
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

  return new NextResponse(fallbackSvg(), {
    headers: { "Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=300" },
  });
}
