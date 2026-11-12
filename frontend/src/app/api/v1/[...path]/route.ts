import { NextRequest, NextResponse } from "next/server";
import { isRequestAuthenticated } from "@/lib/auth";

export const runtime = "nodejs";
export const maxDuration = 60;

const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "content-type",
  "x-llm-provider",
  "x-llm-model",
  "x-llm-api-key",
] as const;

const FORWARDED_RESPONSE_HEADERS = [
  "content-type",
  "content-disposition",
  "cache-control",
] as const;

function getBackendBaseUrl(): string {
  const raw = (process.env.BACKEND_API_URL ?? "http://localhost:8000").trim();
  return raw.replace(/\/+$/, "");
}

function buildTargetUrl(segments: string[], search: string): string | null {
  if (!segments.length) return null;
  for (const segment of segments) {
    if (
      !segment ||
      segment === "." ||
      segment === ".." ||
      segment.includes("/") ||
      segment.includes("\\")
    ) {
      return null;
    }
  }
  const encodedPath = segments.map((seg) => encodeURIComponent(seg)).join("/");
  return `${getBackendBaseUrl()}/api/v1/${encodedPath}${search}`;
}

async function handleProxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  if (!isRequestAuthenticated(request)) {
    return NextResponse.json(
      { detail: "Demo authentication required." },
      { status: 401 },
    );
  }

  const { path } = await context.params;
  const targetUrl = buildTargetUrl(path, request.nextUrl.search);
  if (!targetUrl) {
    return NextResponse.json(
      { detail: "Invalid API proxy path." },
      { status: 400 },
    );
  }

  const upstreamHeaders = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const val = request.headers.get(name);
    if (val) {
      upstreamHeaders.set(name, val);
    }
  }

  const sharedSecret = (process.env.BACKEND_SHARED_SECRET ?? "").trim();
  if (sharedSecret) {
    upstreamHeaders.set("x-backend-secret", sharedSecret);
  }

  const method = request.method.toUpperCase();
  const hasBody = method !== "GET" && method !== "HEAD";
  const body = hasBody ? await request.arrayBuffer() : undefined;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(new Error("timeout")), 180_000);
  const onAbort = () => controller.abort(request.signal.reason);
  if (request.signal.aborted) {
    controller.abort(request.signal.reason);
  } else {
    request.signal.addEventListener("abort", onAbort, { once: true });
  }

  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(targetUrl, {
      method,
      headers: upstreamHeaders,
      body,
      redirect: "manual",
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return NextResponse.json(
        { detail: "Request cancelled or timed out waiting for backend." },
        { status: 504 },
      );
    }
    return NextResponse.json(
      {
        detail:
          "Backend API is unreachable. Verify FastAPI is running on BACKEND_API_URL.",
      },
      { status: 502 },
    );
  } finally {
    clearTimeout(timeoutId);
    request.signal.removeEventListener("abort", onAbort);
  }

  const responseHeaders = new Headers();
  for (const headerName of FORWARDED_RESPONSE_HEADERS) {
    const val = upstreamResponse.headers.get(headerName);
    if (val) {
      responseHeaders.set(headerName, val);
    }
  }
  if (!responseHeaders.has("cache-control")) {
    responseHeaders.set("cache-control", "no-store");
  }

  return new NextResponse(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: responseHeaders,
  });
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  return handleProxy(request, context);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  return handleProxy(request, context);
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  return handleProxy(request, context);
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  return handleProxy(request, context);
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  return handleProxy(request, context);
}
