import { backendBaseUrl, jsonResponse } from "@/lib/backend";

export const runtime = "nodejs";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const response = await fetch(`${backendBaseUrl()}/api/submissions/${id}/decision`, {
      method: "POST",
      headers: {
        "content-type": "application/json"
      },
      body: await request.text()
    });
    const text = await response.text();
    return new Response(text, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") || "application/json"
      }
    });
  } catch (error) {
    return jsonResponse(error instanceof Error ? error.message : "Decision could not be saved.");
  }
}
