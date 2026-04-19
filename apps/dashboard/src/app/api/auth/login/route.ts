import { NextRequest, NextResponse } from "next/server";
import { createSessionCookie } from "@/lib/session";
import { getNextPath, readRequestBody } from "@/lib/http";
import { getSessionCookieName } from "@/lib/session";
import { getSessionMaxAgeSeconds } from "@/lib/session";
import { validateDashboardCredentials } from "@/lib/session";
import { normalizeNextPath } from "@/lib/paths";

export async function POST(request: NextRequest) {
  const body = await readRequestBody(request);
  const username = String(body.username ?? "");
  const password = String(body.password ?? "");
  const nextValue = normalizeNextPath(String(body.next ?? getNextPath(request)));

  const isValid = await validateDashboardCredentials(username, password);
  if (!isValid) {
    const url = new URL("/login", request.url);
    url.searchParams.set("error", "invalid");
    url.searchParams.set("next", nextValue);
    return NextResponse.redirect(url, 303);
  }

  const sessionValue = await createSessionCookie(username);
  const response = NextResponse.redirect(new URL(nextValue, request.url), 303);
  response.cookies.set({
    name: getSessionCookieName(),
    value: sessionValue,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: getSessionMaxAgeSeconds(),
  });

  return response;
}
