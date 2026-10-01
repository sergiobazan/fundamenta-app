import { backendFetch } from "./backend";

export async function adminProxy(path: string, init?: RequestInit) {
  try {
    const response = await backendFetch(path, init);
    return new Response(await response.text(), {
      status: response.status,
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
    });
  } catch {
    return Response.json({ detail: "No se pudo conectar con el servicio. Intenta actualizar." }, { status: 502 });
  }
}
