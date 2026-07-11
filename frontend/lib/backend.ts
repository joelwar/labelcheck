export function backendBaseUrl() {
  const backendUrl = process.env.BACKEND_API_URL;

  if (!backendUrl) {
    throw new Error("BACKEND_API_URL is not configured on the frontend service.");
  }

  return backendUrl.replace(/\/$/, "");
}

export function jsonResponse(message: string, status = 500) {
  return Response.json({ detail: message }, { status });
}
