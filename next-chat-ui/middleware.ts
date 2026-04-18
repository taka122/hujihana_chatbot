import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { hasConfiguredLoginPassword } from "@/lib/auth-config";
import { AUTH_COOKIE_NAME, AUTH_COOKIE_VALUE } from "@/lib/auth-constants";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const loginRequired = hasConfiguredLoginPassword();
  const isAuthenticated = request.cookies.get(AUTH_COOKIE_NAME)?.value === AUTH_COOKIE_VALUE;

  if (!loginRequired) {
    return NextResponse.next();
  }

  if (pathname === "/login") {
    const response = NextResponse.next();
    response.cookies.set(AUTH_COOKIE_NAME, "", {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      expires: new Date(0)
    });
    return response;
  }

  if (!isAuthenticated) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/login", "/w/:path*"]
};
