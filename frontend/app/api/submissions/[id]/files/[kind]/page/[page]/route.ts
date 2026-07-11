import { backendBaseUrl, jsonResponse } from "@/lib/backend";

export const runtime = "nodejs";

export async function GET(
  _: Request,
  { params }: { params: Promise<{ id: string; kind: string; page: string }> }
) {
  try {
    const { id, kind, page } = await params;
    const response = await fetch(`${backendBaseUrl()}/api/submissions/${id}/files/${kind}/page/${page}`, {
      cache: "no-store"
    });
    const body = await response.arrayBuffer();
    return new Response(body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") || "application/octet-stream",
        "content-disposition": response.headers.get("content-disposition") || "inline"
      }
    });
  } catch (error) {
    return jsonResponse(error instanceof Error ? error.message : "Page preview could not be loaded.");
  }
}
