import { adminProxy } from "@/lib/admin-proxy";
type Context = { params: Promise<{ segments: string[] }> };
async function forward(request: Request, context: Context, method: string) {
  const { segments } = await context.params;
  const path = segments.join("/");
  if (!/^(summary|audit|users|users\/\d+(\/activity|\/access)?)$/.test(path)) return Response.json({ detail: "Ruta no encontrada" }, { status: 404 });
  if (method === "POST") {
    if (!/^users\/\d+\/access$/.test(path) || request.headers.get("origin") !== new URL(request.url).origin) return Response.json({ detail: "Solicitud no permitida" }, { status: 403 });
    if (!request.headers.get("content-type")?.startsWith("application/json")) return Response.json({ detail: "Se requiere JSON" }, { status: 415 });
    const body = await request.text();
    if (body.length > 4096) return Response.json({ detail: "Solicitud demasiado grande" }, { status: 413 });
    return adminProxy(`/admin/${path}`, { method, body });
  }
  const params = new URL(request.url).searchParams;
  const query = new URLSearchParams();
  for (const key of ["q", "role", "status", "page", "start", "end", "created_from", "created_to", "sort", "active_only", "action", "company", "outcome", "actor_type"]) if (params.has(key)) query.set(key, params.get(key)!);
  return adminProxy(`/admin/${path}?${query}`);
}
export async function GET(request: Request, context: Context) { return forward(request, context, "GET"); }
export async function POST(request: Request, context: Context) { return forward(request, context, "POST"); }
