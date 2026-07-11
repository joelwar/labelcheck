import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

function backendBaseUrl() {
  const backendUrl = process.env.BACKEND_API_URL;

  if (!backendUrl) {
    return null;
  }

  return backendUrl.replace(/\/$/, "");
}

export async function GET() {
  const backendUrl = backendBaseUrl();

  if (!backendUrl) {
    return NextResponse.json(
      {
        ok: false,
        detail: "BACKEND_API_URL is not configured on the frontend service."
      },
      { status: 500 }
    );
  }

  try {
    const response = await fetch(`${backendUrl}/api/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(8000)
    });
    const text = await response.text();
    return NextResponse.json(
      {
        ok: response.ok,
        backend_status: response.status,
        backend_url_host: new URL(backendUrl).host,
        backend_response: text
      },
      { status: response.ok ? 200 : 502 }
    );
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        detail: "Frontend service could not reach backend /api/health.",
        backend_url_host: safeHost(backendUrl),
        error: error instanceof Error ? error.message : "Unknown error"
      },
      { status: 502 }
    );
  }
}

export async function POST(request: NextRequest) {
  const backendUrl = backendBaseUrl();

  if (!backendUrl) {
    return NextResponse.json(
      { detail: "Backend URL is not configured. Set BACKEND_API_URL on the frontend service." },
      { status: 500 }
    );
  }

  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json(
      { detail: "Uploaded files could not be read by the frontend service. Please try again." },
      { status: 400 }
    );
  }

  try {
    const response = await fetch(`${backendUrl}/api/verify`, {
      method: "POST",
      body: formData,
      signal: AbortSignal.timeout(60000)
    });

    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") || "application/json"
      }
    });
  } catch (error) {
    return NextResponse.json(
      {
        detail: "Verification service could not be reached. Please try again.",
        backend_url_host: safeHost(backendUrl),
        error: error instanceof Error ? error.message : "Unknown error"
      },
      { status: 502 }
    );
  }
}

function safeHost(url: string) {
  try {
    return new URL(url).host;
  } catch {
    return "Invalid BACKEND_API_URL";
  }
}
