"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import type { Company } from "@/lib/types";

type ActionCompany = Pick<
  Company,
  "smv_rpj" | "support_level" | "analysis_status" | "has_analysis" | "job_status"
>;

export function CompanyAnalysisAction({ company }: { company: ActionCompany }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState("");
  const active = company.job_status && ["queued", "running", "retrying"].includes(company.job_status);
  const companyPath = `/empresas/${encodeURIComponent(company.smv_rpj)}`;

  if (company.has_analysis) {
    return <Link className="analysis-action ready" href={companyPath}>Ver análisis</Link>;
  }
  if (company.support_level === "unsupported") {
    return <span className="analysis-action disabled">Próximamente</span>;
  }
  if (active) {
    return <Link className="analysis-action progress" href={companyPath}>Ver progreso</Link>;
  }
  if (company.analysis_status === "review_required") {
    return <span className="analysis-action disabled">En revisión</span>;
  }

  function requestAnalysis() {
    setError("");
    startTransition(async () => {
      const response = await fetch(`/api/companies/${encodeURIComponent(company.smv_rpj)}/analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null) as { detail?: string } | null;
        setError(payload?.detail || "No pudimos registrar el análisis.");
        return;
      }
      router.push(companyPath);
      router.refresh();
    });
  }

  return <div className="analysis-action-wrap">
    <button className="analysis-action request" type="button" disabled={pending} onClick={requestAnalysis}>
      {pending ? "Solicitando…" : company.analysis_status === "failed" ? "Reintentar" : "Generar análisis"}
    </button>
    {error && <small role="alert">{error}</small>}
  </div>;
}
