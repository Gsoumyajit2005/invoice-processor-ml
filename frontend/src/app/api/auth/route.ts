import { NextRequest, NextResponse } from "next/server";
import {
  attachSessionCookie,
  clearSessionCookie,
  isPasscodeRequired,
  isRequestAuthenticated,
  verifyPasscodeInput,
} from "@/lib/auth";

export const runtime = "nodejs";

export async function GET(request: NextRequest): Promise<NextResponse> {
  return NextResponse.json(
    {
      required: isPasscodeRequired(),
      authenticated: isRequestAuthenticated(request),
    },
    {
      headers: { "Cache-Control": "no-store" },
    },
  );
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  let body: { passcode?: unknown };
  try {
    body = (await request.json()) as { passcode?: unknown };
  } catch {
    return NextResponse.json(
      { detail: "Invalid JSON payload." },
      { status: 400 },
    );
  }

  const passcode = typeof body.passcode === "string" ? body.passcode : "";
  if (!verifyPasscodeInput(passcode)) {
    return NextResponse.json(
      { detail: "Invalid demo passcode." },
      { status: 401 },
    );
  }

  const response = NextResponse.json({
    ok: true,
    required: isPasscodeRequired(),
    authenticated: true,
  });
  if (isPasscodeRequired()) {
    attachSessionCookie(response, request);
  }
  return response;
}

export async function DELETE(request: NextRequest): Promise<NextResponse> {
  const response = NextResponse.json({
    ok: true,
    required: isPasscodeRequired(),
    authenticated: !isPasscodeRequired(),
  });
  clearSessionCookie(response, request);
  return response;
}
