export const dynamic = "force-dynamic";
export async function GET() {
  const baseUrl = process.env.BACKEND_URL || "http://127.0.0.1:8000";
  try {
    const alive = await fetch(`${baseUrl}/api/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (!alive.ok) throw new Error("API unavailable");
  } catch {
    return Response.json(
      { api: "unavailable", database: "unknown" },
      { status: 503 },
    );
  }
  try {
    const response = await fetch(`${baseUrl}/api/health/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    const data = await response.json();
    return Response.json({
      api: "online",
      database:
        response.ok && data.database === "connected"
          ? "connected"
          : "unavailable",
    });
  } catch {
    return Response.json({ api: "online", database: "unavailable" });
  }
}
