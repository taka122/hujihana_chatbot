import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const HOP_BY_HOP_HEADERS = [
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade"
];

function normalizeBaseUrl(value: string): string {
  return value.replace(/\/$/, "");
}

function getBackendBaseUrl(): string {
  const explicitTarget = process.env.API_PROXY_TARGET?.trim();
  if (explicitTarget) {
    return normalizeBaseUrl(explicitTarget);
  }

  const publicTarget = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (publicTarget) {
    return normalizeBaseUrl(publicTarget);
  }

  return "http://localhost:8000";
}

function filterResponseHeaders(headers: Headers): Headers {
  const filtered = new Headers(headers);
  HOP_BY_HOP_HEADERS.forEach((header) => filtered.delete(header));
  return filtered;
}

async function proxy(request: NextRequest, { params }: { params: { path: string[] } }) {
  const pathname = `/${(params.path ?? []).join("/")}`;
  const upstreamUrl = `${getBackendBaseUrl()}${pathname}${request.nextUrl.search}`;
  const requestHeaders = new Headers(request.headers);

  requestHeaders.delete("host");
  requestHeaders.delete("content-length");

  const init: RequestInit = {
    method: request.method,
    headers: requestHeaders,
    cache: "no-store",
    redirect: "manual"
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    const body = await request.arrayBuffer();
    if (body.byteLength > 0) {
      init.body = body;
    }
  }

  try {
    const upstream = await fetch(upstreamUrl, init);
    return new NextResponse(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: filterResponseHeaders(upstream.headers)
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown proxy error";
    return NextResponse.json(
      {
        error: `Backend proxy request failed: ${message}`
      },
      { status: 502 }
    );
  }
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE, proxy as OPTIONS, proxy as HEAD };
