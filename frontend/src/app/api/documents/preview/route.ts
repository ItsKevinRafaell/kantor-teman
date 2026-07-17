import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy the document preview request directly to the backend API,
 * bypassing the Vercel trailingSlash redirect that strips POST bodies.
 *
 * trailingSlash:true causes /api/documents/preview → /api/documents/preview/
 * via308. The redirect chain then hits FastAPI which307-redirects back,
 * stripping the POST body entirely. The backend receives an empty request
 * and falls to WeasyPrint (broken CMap) instead of ReportLab.
 *
 * This route handles the POST directly and forwards to the backend.
 */
export async function POST(request: NextRequest) {
  const body = await request.arrayBuffer();
  const BACKEND_URL =
    process.env.NEXT_PUBLIC_API_URL || "https://api.kantorteman.my.id";

  const res = await fetch(`${BACKEND_URL}/api/documents/preview`, {
    method: "POST",
    body,
    headers: {
      "Content-Type": request.headers.get("content-type") || "application/json",
      Authorization: request.headers.get("authorization") || "",
    },
  });

  if (!res.ok) {
    const text = await res.text();
    return new NextResponse(text, { status: res.status, statusText: res.statusText });
  }

  const pdfBytes = await res.arrayBuffer();
  const filename =
    res.headers.get("content-disposition")?.match(/filename="([^"]+)"/)?.[1] ||
    "preview.pdf";

  return new NextResponse(pdfBytes, {
    status: 200,
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `inline; filename="${filename}"`,
      "X-Pdf-Renderer": res.headers.get("X-Pdf-Renderer") || "unknown",
    },
  });
}
