import { NextRequest } from "next/server";
export const dynamic = "force-dynamic";
type Context = { params: Promise<{ path: string[] }> };
async function proxy(request: NextRequest, context: Context) {
  const host = request.headers.get("host") || "";
  if (!/^(localhost|127\.0\.0\.1)(:\d+)?$/.test(host))
    return Response.json(
      { detail: "This workspace is local-only" },
      { status: 403 },
    );
  const { path } = await context.params;
  const target = path.join("/");
  const method = request.method;
  const allowed =
    (method === "GET" &&
      (target === "workspace" || /^incidents\/[a-zA-Z0-9-]+$/.test(target))) ||
    (method === "POST" &&
      ["analyst", "runtime/events", "services", "deployments/ingest"].includes(
        target,
      )) ||
    (method === "PATCH" && /^incidents\/[a-zA-Z0-9-]+$/.test(target));
  if (!allowed)
    return Response.json({ detail: "Route not available" }, { status: 404 });
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (process.env.APP_API_KEY) headers["X-API-Key"] = process.env.APP_API_KEY;
  if (method !== "GET" && target !== "analyst") {
    if (!process.env.INGEST_TOKEN)
      return Response.json(
        {
          detail:
            "Configure INGEST_TOKEN on the frontend and backend to enable local writes.",
        },
        { status: 503 },
      );
    headers.Authorization = `Bearer ${process.env.INGEST_TOKEN}`;
  }
  let body: string | undefined;
  if (method !== "GET") {
    let sameOrigin = false;
    try {
      const origin = new URL(request.headers.get("origin") || "");
      sameOrigin =
        origin.host === host && ["http:", "https:"].includes(origin.protocol);
    } catch {
      /* Missing or invalid Origin is rejected. */
    }
    if (!sameOrigin)
      return Response.json(
        { detail: "Same-origin requests only" },
        { status: 403 },
      );
    if (!request.headers.get("content-type")?.startsWith("application/json"))
      return Response.json({ detail: "JSON required" }, { status: 415 });
    body = await request.text();
    if (body.length > 1_048_576)
      return Response.json({ detail: "Request too large" }, { status: 413 });
  }
  try {
    const response = await fetch(
      `${process.env.BACKEND_URL || "http://127.0.0.1:8000"}/api/v1/${target}`,
      {
        method,
        headers,
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(15000),
      },
    );
    return new Response(await response.text(), {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return Response.json(
      {
        detail:
          "BuildBrother API is unavailable. Start the backend and verify BACKEND_URL.",
      },
      { status: 503 },
    );
  }
}
export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
