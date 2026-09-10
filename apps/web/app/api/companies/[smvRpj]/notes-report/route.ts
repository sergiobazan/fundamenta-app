import { backendFetch } from "@/lib/backend";

type Context = { params: Promise<{ smvRpj: string }> };

async function proxy(request: Request, context: Context) {
  const { smvRpj } = await context.params;
  const url = new URL(request.url);
  try {
    const response = await backendFetch(
      `/companies/${encodeURIComponent(smvRpj)}/notes-report${url.search}`,
      { method: request.method,
        ...(request.method === "POST" ? { body: await request.text() } : {}),
        signal: AbortSignal.timeout(20000) },
    );
    return new Response(await response.text(), {
      status: response.status,
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json({ detail: "No se pudo contactar al backend. Intenta nuevamente." },
      { status: 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
