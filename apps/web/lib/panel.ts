import type { Company } from "./types";

export function panelOverview(companies: Company[]) {
  const active = companies.filter(c => ["queued", "running", "retrying"].includes(c.job_status ?? "")
    || ["queued", "processing"].includes(c.analysis_status));
  const activeIds = new Set(active.map(c => c.smv_rpj));
  const available = companies.filter(c => c.has_analysis && c.analysis_status === "available" && !activeIds.has(c.smv_rpj))
    .sort((a, b) => (Date.parse(b.last_completed_at ?? "") || 0) - (Date.parse(a.last_completed_at ?? "") || 0)
      || a.legal_name.localeCompare(b.legal_name, "es"));
  return { active, available,
    compatible: companies.filter(c => c.support_level !== "unsupported").length,
    attention: companies.filter(c => !activeIds.has(c.smv_rpj)
      && ["partial", "review_required", "failed"].includes(c.analysis_status)).length,
  };
}
