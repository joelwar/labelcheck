import { backendBaseUrl, jsonResponse } from "@/lib/backend";

export const runtime = "nodejs";

export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const response = await fetch(`${backendBaseUrl()}/api/submissions/${id}`, {
      cache: "no-store"
    });
    const text = await response.text();
    return new Response(text, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") || "application/json"
      }
    });
  } catch (error) {
    return jsonResponse(error instanceof Error ? error.message : "Submission could not be loaded.");
  }
}
