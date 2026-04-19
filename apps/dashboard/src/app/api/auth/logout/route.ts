import { NextRequest, NextResponse } from "next/server";
import { getSessionCookieName } from "@/lib/session";
import { isSecureRequest } from "@/lib/session";
import { toPublicUrl } from "@/lib/public-url";

export async function POST(request: NextRequest) {
  const response = NextResponse.redirect(toPublicUrl(request, "/login"), 303);
  response.cookies.set({
    name: getSessionCookieName(),
    value: "",
    httpOnly: true,
    sameSite: "lax",
    secure: isSecureRequest(request),
    path: "/",
    maxAge: 0,
  });
  return response;
}
