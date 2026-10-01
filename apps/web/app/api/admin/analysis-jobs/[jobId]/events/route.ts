import { adminProxy } from "@/lib/admin-proxy";
export async function GET(request: Request, { params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  const query = new URLSearchParams();
  const before = new URL(request.url).searchParams.get("before");
  if (before) query.set("before", before);
  return adminProxy(`/admin/analysis-jobs/${encodeURIComponent(jobId)}/events?${query}`);
}
