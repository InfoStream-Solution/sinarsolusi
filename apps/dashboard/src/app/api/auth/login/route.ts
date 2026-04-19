import { NextRequest, NextResponse } from "next/server";
import { createSessionCookie } from "@/lib/session";
import { getNextPath, readRequestBody } from "@/lib/http";
import { getSessionCookieName } from "@/lib/session";
import { getSessionMaxAgeSeconds } from "@/lib/session";
import { isSecureRequest } from "@/lib/session";
import { validateDashboardCredentials } from "@/lib/session";
import { normalizeNextPath } from "@/lib/paths";
import { toPublicUrl } from "@/lib/public-url";

export async function POST(request: NextRequest) {
  const body = await readRequestBody(request);
  const username = String(body.username ?? "");
  const password = String(body.password ?? "");
  const nextValue = normalizeNextPath(String(body.next ?? getNextPath(request)));

  const isValid = await validateDashboardCredentials(username, password);
  if (!isValid) {
    const url = toPublicUrl(request, "/login");
    url.searchParams.set("error", "invalid");
    url.searchParams.set("next", nextValue);
    return NextResponse.redirect(url, 303);
  }

  const sessionValue = await createSessionCookie(username);
  const response = NextResponse.redirect(toPublicUrl(request, nextValue), 303);
  response.cookies.set({
    name: getSessionCookieName(),
    value: sessionValue,
    httpOnly: true,
    sameSite: "lax",
    secure: isSecureRequest(request),
    path: "/",
    maxAge: getSessionMaxAgeSeconds(),
  });

  return response;
}
