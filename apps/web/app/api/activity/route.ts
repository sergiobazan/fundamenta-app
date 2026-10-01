import { adminProxy } from "@/lib/admin-proxy";
export async function POST(request: Request) {
  if (request.headers.get("origin") !== new URL(request.url).origin) return new Response(null, { status: 403 });
  if (!request.headers.get("content-type")?.startsWith("application/json")) return new Response(null, { status: 415 });
  const body = await request.text();
  if (body.length > 2048) return new Response(null, { status: 413 });
  return adminProxy("/activity", { method: "POST", body });
}
