import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const SECURITY_HEADERS = {
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
  "X-XSS-Protection": "1; mode=block",
};

export function middleware(request: NextRequest) {
  const token = request.cookies.get("kt_token")?.value;
  const { pathname } = request.nextUrl;
  const isLoginPage = pathname === "/login" || pathname === "/login/";
  const isPublicProposal = pathname.startsWith("/proposal/");
  const isPublicReport = pathname.startsWith("/report/");
  const isShortLink = pathname.startsWith("/r/") || pathname.startsWith("/p/");

  if (isPublicProposal || isPublicReport || isShortLink) {
    return NextResponse.next();
  }

  if (!token && !isLoginPage) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (token && isLoginPage) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  const response = NextResponse.next();
  Object.entries(SECURITY_HEADERS).forEach(([key, value]) => {
    response.headers.set(key, value);
  });
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api|manifest|sw\\.js|workbox-).*)"],
};
