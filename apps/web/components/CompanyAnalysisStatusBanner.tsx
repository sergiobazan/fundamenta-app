"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { pollAnalysis } from "@/lib/analysis-polling";
import type { AnalysisStepCode, Company, CompanyAnalysis } from "@/lib/types";

const stepNames: Record<AnalysisStepCode | "complete", string> = {
  statements: "estados financieros",
  metrics: "métricas",
  documents: "notas y búsqueda",
  summaries: "resúmenes y comparaciones",
  complete: "análisis completo",
};

export function CompanyAnalysisStatusBanner({ initial }: { initial: Company }) {
  const router = useRouter();
  const [company, setCompany] = useState(initial);
  const [activity, setActivity] = useState("");
  const active = Boolean(
    company.job_status && ["queued", "running", "retrying"].includes(company.job_status),
  );

  useEffect(() => {
    if (!active) return;
    return pollAnalysis(company.smv_rpj, (analysis: CompanyAnalysis) => {
      const details = analysis.job?.steps.find(step => step.step_code === "documents")?.details;
      setActivity(typeof details?.activity === "string" ? details.activity.split(": https://")[0] : "");
      setCompany((current) => ({
        ...current,
        ...analysis.company,
        job_id: analysis.job?.id ?? null,
        job_status: analysis.job?.status ?? null,
        job_current_step: analysis.job?.current_step ?? null,
        job_progress: analysis.job?.progress ?? null,
      }));
      if (!analysis.job || !["queued", "running", "retrying"].includes(analysis.job.status)) {
        router.refresh();
      }
    });
  }, [active, company.smv_rpj, router]);

  const title = active
    ? `Análisis en progreso · ${company.job_progress ?? 0}%`
    : company.analysis_status === "review_required"
      ? "Análisis pendiente de revisión"
      : "Análisis parcial";
  const detail = active
    ? `${activity || `Procesando ${company.job_current_step ? stepNames[company.job_current_step] : "la solicitud"}`}. Ya puedes consultar los estados y métricas disponibles.`
    : company.last_error || "Algunas etapas documentales continúan pendientes.";

  return <section className="coverage-note analysis-live-status"><span>{active ? "↻" : "!"}</span><div><b>{title}</b><p>{detail}</p></div></section>;
}
