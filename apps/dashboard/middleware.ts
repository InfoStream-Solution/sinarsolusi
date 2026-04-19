import { NextRequest, NextResponse } from "next/server";
import { getSessionCookieName } from "@/lib/session";
import { getSessionFromCookieValue } from "@/lib/session";

const PUBLIC_PATHS = new Set(["/login"]);

function isPublicAsset(pathname: string) {
  return (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.includes(".")
  );
}

function isAuthPath(pathname: string) {
  return pathname.startsWith("/api/auth/");
}

async function hasValidSession(request: NextRequest) {
  return getSessionFromCookieValue(
    request.cookies.get(getSessionCookieName())?.value,
  );
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isPublicAsset(pathname)) {
    return NextResponse.next();
  }

  const session = await hasValidSession(request);

  if (PUBLIC_PATHS.has(pathname)) {
    if (session) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    return NextResponse.next();
  }

  if (isAuthPath(pathname)) {
    return NextResponse.next();
  }

  if (!session) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/:path*"],
};
