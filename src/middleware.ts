import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { locales, defaultLocale } from "@/lib/i18n";

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  // Ignore next internals and assets
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  const hasLocale = locales.some((loc) => pathname === `/${loc}` || pathname.startsWith(`/${loc}/`));
  if (!hasLocale) {
    const url = req.nextUrl.clone();
    url.pathname = `/${defaultLocale}${pathname}`;
    return NextResponse.redirect(url);
  }
  const locale = pathname.split("/")[1];
  const requestHeaders = new Headers(req.headers);
  requestHeaders.set("x-locale", locale);
  return NextResponse.next({ request: { headers: requestHeaders } });
}

export const config = {
  matcher: ["/:path*"],
};
