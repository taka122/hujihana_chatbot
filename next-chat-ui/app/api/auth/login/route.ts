import { NextResponse } from "next/server";

import {
  AUTH_COOKIE_NAME,
  AUTH_COOKIE_VALUE,
  hasConfiguredLoginPassword,
  verifyLoginPassword
} from "@/lib/auth";

export async function POST(request: Request) {
  const payload = await request.json().catch(() => ({}));
  const password = typeof payload?.password === "string" ? payload.password : "";

  if (!verifyLoginPassword(password)) {
    return NextResponse.json(
      {
        message: hasConfiguredLoginPassword()
          ? "パスワードが一致しません。"
          : "パスワードを入力してください。"
      },
      { status: 401 }
    );
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(AUTH_COOKIE_NAME, AUTH_COOKIE_VALUE, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/"
  });
  return response;
}
