import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const token = request.cookies.get("kt_token")?.value;
  const { pathname } = request.nextUrl;
  const isLoginPage = pathname === "/login";
  const isPublicProposal = pathname.startsWith("/proposal/");
  const isPublicReport = pathname.startsWith("/report/");

  if (isPublicProposal || isPublicReport) {
    return NextResponse.next();
  }

  if (!token && !isLoginPage) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (token && isLoginPage) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
