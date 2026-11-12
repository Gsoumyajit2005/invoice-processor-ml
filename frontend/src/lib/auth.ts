import { createHash, createHmac, timingSafeEqual } from "node:crypto";
import type { NextRequest, NextResponse } from "next/server";

export const SESSION_COOKIE_NAME = "invproc_session";
const SESSION_TTL_SECONDS = 60 * 60 * 24 * 7; // 7 days

function getPasscode(): string {
  return (process.env.DEMO_PASSCODE ?? "").trim();
}

function getSigningKey(): string {
  const explicit = (process.env.DEMO_AUTH_SECRET ?? "").trim();
  if (explicit) return explicit;
  const fallback =
    (process.env.BACKEND_SHARED_SECRET ?? "").trim() || getPasscode();
  return createHash("sha256")
    .update(`invproc-demo-session-key:${fallback}`)
    .digest("hex");
}

function sha256Digest(value: string): Buffer {
  return createHash("sha256").update(value, "utf8").digest();
}

export function isPasscodeRequired(): boolean {
  return getPasscode().length > 0;
}

export function verifyPasscodeInput(candidate: string): boolean {
  const expected = getPasscode();
  if (!expected) return true;
  if (!candidate) return false;
  return timingSafeEqual(sha256Digest(candidate), sha256Digest(expected));
}

export function createSessionToken(nowMs: number = Date.now()): string {
  const exp = Math.floor(nowMs / 1000) + SESSION_TTL_SECONDS;
  const payload = Buffer.from(JSON.stringify({ exp }), "utf8").toString(
    "base64url",
  );
  const sig = createHmac("sha256", getSigningKey())
    .update(payload)
    .digest("base64url");
  return `${payload}.${sig}`;
}

export function verifySessionToken(
  token: string | undefined,
  nowMs: number = Date.now(),
): boolean {
  if (!token) return false;
  const parts = token.split(".");
  if (parts.length !== 2) return false;
  const [payload, sig] = parts;
  if (!payload || !sig) return false;

  const expectedSig = createHmac("sha256", getSigningKey())
    .update(payload)
    .digest("base64url");

  const actualBuf = Buffer.from(sig, "utf8");
  const expectedBuf = Buffer.from(expectedSig, "utf8");
  if (actualBuf.length !== expectedBuf.length) return false;
  if (!timingSafeEqual(actualBuf, expectedBuf)) return false;

  try {
    const decoded = JSON.parse(
      Buffer.from(payload, "base64url").toString("utf8"),
    ) as { exp?: unknown };
    return (
      typeof decoded.exp === "number" &&
      decoded.exp > Math.floor(nowMs / 1000)
    );
  } catch {
    return false;
  }
}

export function isRequestAuthenticated(request: NextRequest): boolean {
  if (!isPasscodeRequired()) return true;
  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  return verifySessionToken(token);
}

export function isHttpsRequest(request: NextRequest): boolean {
  const forwardedProto = request.headers.get("x-forwarded-proto");
  if (forwardedProto) {
    return forwardedProto.split(",")[0].trim().toLowerCase() === "https";
  }
  return request.nextUrl.protocol === "https:";
}

export function attachSessionCookie(
  response: NextResponse,
  request: NextRequest,
): void {
  response.cookies.set(SESSION_COOKIE_NAME, createSessionToken(), {
    httpOnly: true,
    sameSite: "lax",
    secure: isHttpsRequest(request),
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  });
}

export function clearSessionCookie(
  response: NextResponse,
  request: NextRequest,
): void {
  response.cookies.set(SESSION_COOKIE_NAME, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: isHttpsRequest(request),
    path: "/",
    maxAge: 0,
  });
}
