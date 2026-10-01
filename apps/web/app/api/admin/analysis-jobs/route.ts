import { adminProxy } from "@/lib/admin-proxy";
export async function GET(request: Request) {
  const source = new URL(request.url).searchParams;
  const query = new URLSearchParams();
  for (const key of ["q", "status", "page"]) if (source.has(key)) query.set(key, source.get(key)!);
  return adminProxy(`/admin/analysis-jobs?${query}`);
}
