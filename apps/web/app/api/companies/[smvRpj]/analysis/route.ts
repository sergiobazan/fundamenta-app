import { backendFetch } from "@/lib/backend";

function forward(response: Response, body: string) {
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
  });
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ smvRpj: string }> },
) {
  const { smvRpj } = await params;
  const response = await backendFetch(
    `/companies/${encodeURIComponent(smvRpj)}/analysis`,
  );
  return forward(response, await response.text());
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ smvRpj: string }> },
) {
  const { smvRpj } = await params;
  const body = await request.text();
  const response = await backendFetch(
    `/companies/${encodeURIComponent(smvRpj)}/analysis`,
    { method: "POST", body: body || "{}" },
  );
  return forward(response, await response.text());
}
