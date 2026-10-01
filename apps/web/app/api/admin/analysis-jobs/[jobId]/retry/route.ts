import { adminProxy } from "@/lib/admin-proxy";
export async function POST(request: Request, { params }: { params: Promise<{ jobId: string }> }) {
  if (request.headers.get("origin") !== new URL(request.url).origin) {
    return Response.json({ detail: "Origen de solicitud no permitido" }, { status: 403 });
  }
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    return Response.json({ detail: "Se requiere JSON" }, { status: 415 });
  }
  const body = await request.text();
  if (body.length > 4096) return Response.json({ detail: "Solicitud demasiado grande" }, { status: 413 });
  const { jobId } = await params;
  return adminProxy(`/admin/analysis-jobs/${encodeURIComponent(jobId)}/retry`, { method: "POST", body });
}
