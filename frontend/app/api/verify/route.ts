import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const backendUrl = process.env.BACKEND_API_URL;

  if (!backendUrl) {
    return NextResponse.json(
      { detail: "Backend URL is not configured. Set BACKEND_API_URL on the frontend service." },
      { status: 500 }
    );
  }

  try {
    const formData = await request.formData();
    const response = await fetch(`${backendUrl.replace(/\/$/, "")}/api/verify`, {
      method: "POST",
      body: formData
    });

    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") || "application/json"
      }
    });
  } catch {
    return NextResponse.json(
      { detail: "Verification service could not be reached. Please try again." },
      { status: 502 }
    );
  }
}
