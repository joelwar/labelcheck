import { backendBaseUrl, jsonResponse } from "@/lib/backend";

export const runtime = "nodejs";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const response = await fetch(`${backendBaseUrl()}/api/submissions${url.search}`, {
      cache: "no-store"
    });
    return proxyResponse(response);
  } catch (error) {
    return jsonResponse(error instanceof Error ? error.message : "Submission queue could not be loaded.");
  }
}

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const response = await fetch(`${backendBaseUrl()}/api/submissions`, {
      method: "POST",
      body: formData
    });
    return proxyResponse(response);
  } catch (error) {
    return jsonResponse(error instanceof Error ? error.message : "Submission could not be created.");
  }
}

async function proxyResponse(response: Response) {
  const text = await response.text();
  return new Response(text, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") || "application/json"
    }
  });
}
