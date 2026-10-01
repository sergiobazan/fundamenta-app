import { adminProxy } from "@/lib/admin-proxy";
export async function GET(_request: Request, { params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  return adminProxy(`/admin/analysis-jobs/${encodeURIComponent(jobId)}`);
}
